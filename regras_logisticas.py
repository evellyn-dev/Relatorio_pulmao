"""Regras logísticas centralizadas. Tudo aqui é configurável.
Itens marcados como NÃO CONFIRMADO não são aplicados até serem definidos."""
import re

LADOS = ["Par", "Ímpar", "Ambos"]
APARTAMENTOS = ["01", "02", "Todos"]
RUAS_CONHECIDAS = ["03", "08", "PP"]

# Opções oferecidas por padrão na seleção (o usuário pode digitar outros números).
# O relatório só traz o que existir na planilha.
PREDIOS_PADRAO = {
    "Ímpar": [f"{n:02d}" for n in range(1, 26, 2)],   # 01 a 25
    "Par": [f"{n:02d}" for n in range(2, 27, 2)],     # 02 a 26
    "Ambos": [f"{n:02d}" for n in range(1, 27)],      # 01 a 26
}
NIVEIS_PADRAO = [f"{n:02d}" for n in range(0, 5)]      # 00 a 04

# Andar de cada rua conhecida (spec: ruas 03 a 08 e PP pertencem ao andar 0100).
# Rua fora deste mapa: qualquer andar é aceito.
ANDAR_POR_RUA = {f"{r:02d}": "0100" for r in range(3, 9)}
ANDAR_PP = "0100"

# Regras por modalidade. NÃO CONFIRMADO: ruas/níveis próprios de cada tipo.
# None = sem restrição extra. Quando definido, preencher aqui (ex.: {"niveis": ["00"]}).
TIPOS_RELATORIO = {
    "Pulmões": {"ruas": None, "niveis": None},
    "Pulmão aéreo": {"ruas": None, "niveis": None},
    "Pulmão térreo": {"ruas": None, "niveis": None},
}

_RE_NUM = re.compile(r"^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})$")  # andar|rua|prédio|nível|apto
_RE_PP = re.compile(r"^PP(\d+)$")


def interpretar_endereco(valor):
    """Retorna dict com os campos ou None se malformado. Nunca corrige o valor."""
    if valor is None or valor is getattr(__import__("pandas"), "NA", None) or (isinstance(valor, float) and valor != valor):
        return None
    v = str(valor).strip().upper()
    m = _RE_NUM.match(v)
    if m:
        a, r, p, n, ap = m.groups()
        return {"tipo": "NUM", "andar": a, "rua": r, "predio": p,
                "nivel": n, "apto": ap, "pp_num": None}
    m = _RE_PP.match(v)
    if m:
        return {"tipo": "PP", "andar": ANDAR_PP, "rua": "PP", "predio": None,
                "nivel": None, "apto": None, "pp_num": int(m.group(1))}
    return None


def numero_pp(codigo):
    """'PP12' -> 12; inválido -> None."""
    m = _RE_PP.match(str(codigo).strip().upper())
    return int(m.group(1)) if m else None
