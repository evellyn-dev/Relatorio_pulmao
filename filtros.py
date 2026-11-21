from dataclasses import dataclass
import pandas as pd
from regras_logisticas import (interpretar_endereco, ANDAR_POR_RUA, ANDAR_PP,
                               numero_pp, TIPOS_RELATORIO)

CAMPOS = ["tipo", "andar", "rua", "predio", "nivel", "apto", "pp_num"]


@dataclass
class ConfigRua:
    rua: str
    lado: str = "Ambos"          # Par | Ímpar | Ambos
    predios: list = None         # None = todos do lado
    niveis: list = None          # obrigatório (lista não vazia)
    apartamentos: list = None    # None = todos


@dataclass
class ConfigPP:
    inicial: str = ""
    final: str = ""


def interpretar_coluna(serie):
    """Tabela auxiliar (mesmo índice do df). Não altera os dados originais."""
    linhas = [interpretar_endereco(v) for v in serie]
    p = pd.DataFrame([l or {} for l in linhas], index=serie.index, columns=CAMPOS)
    p["valido"] = [l is not None for l in linhas]
    return p


def normalizar_lista(valores):
    """Converte o que o usuário digitou em códigos de 2 dígitos ('5' -> '05').
    Retorna (válidos sem repetição, inválidos). Aceita números que não estão na lista."""
    ok, inval = [], []
    for v in valores:
        t = str(v).strip()
        if t.isdigit() and 1 <= len(t) <= 2:
            t = t.zfill(2)
            if t not in ok:
                ok.append(t)
        else:
            inval.append(t)
    return ok, inval


def _eh_par(predio):
    return pd.to_numeric(predio, errors="coerce") % 2 == 0


def mascara_rua(p, cfg):
    m = (p["tipo"] == "NUM") & (p["rua"] == cfg.rua)
    andar = ANDAR_POR_RUA.get(cfg.rua)
    if andar:
        m &= p["andar"] == andar
    par = _eh_par(p["predio"])
    if cfg.lado == "Par":
        m &= par
    elif cfg.lado == "Ímpar":
        m &= ~par & p["predio"].notna()
    if cfg.predios is not None:
        m &= p["predio"].isin(cfg.predios)
    m &= p["nivel"].isin(cfg.niveis or [])
    if cfg.apartamentos is not None:
        m &= p["apto"].isin(cfg.apartamentos)
    return m.fillna(False)


def mascara_pp(p, cfg):
    ini, fim = numero_pp(cfg.inicial), numero_pp(cfg.final)
    m = (p["tipo"] == "PP") & (p["andar"] == ANDAR_PP)
    m &= pd.to_numeric(p["pp_num"], errors="coerce").between(ini, fim)
    return m.fillna(False)


def validar_rua(p, cfg):
    """Lista de erros (bloqueiam) para a configuração de uma rua."""
    erros = []
    sub = p[(p["tipo"] == "NUM") & (p["rua"] == cfg.rua)]
    if sub.empty:
        erros.append(f"Rua {cfg.rua}: sem registros na planilha.")
        return erros
    if not cfg.niveis:
        erros.append(f"Rua {cfg.rua}: selecione ao menos um nível.")
    if cfg.predios is not None:
        if not cfg.predios:
            erros.append(f"Rua {cfg.rua}: selecione ao menos um prédio.")
    return erros


def validar_pp(p, cfg):
    erros = []
    ini, fim = numero_pp(cfg.inicial), numero_pp(cfg.final)
    if ini is None or fim is None:
        return ["PP: informe inicial e final no formato PP12."]
    if ini > fim:
        erros.append("PP: o valor inicial é maior que o final.")
    if not (p["tipo"] == "PP").any():
        erros.append("PP: sem registros na planilha.")
    return erros


def validar_tudo(p, configs):
    erros = []
    for c in configs:
        erros += validar_pp(p, c) if isinstance(c, ConfigPP) else validar_rua(p, c)
    return erros


def gerar_relatorio(df, p, configs, tipo=None):
    """Processa cada configuração separadamente e combina sem duplicar linhas."""
    restr = TIPOS_RELATORIO.get(tipo, {}) if tipo else {}
    partes, contagem = [], {}
    for c in configs:
        m = mascara_pp(p, c) if isinstance(c, ConfigPP) else mascara_rua(p, c)
        if restr.get("niveis") and not isinstance(c, ConfigPP):
            m &= p["nivel"].isin(restr["niveis"])
        nome = "PP" if isinstance(c, ConfigPP) else f"Rua {c.rua}"
        contagem[nome] = int(m.sum())
        partes.append(df[m])
    if not partes:
        return df.iloc[0:0], contagem
    res = pd.concat(partes)
    res = res[~res.index.duplicated(keep="first")].sort_index()
    return res, contagem
