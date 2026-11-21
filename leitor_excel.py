import pandas as pd
from regras_logisticas import interpretar_endereco


def _montar(bruto, h):
    """Usa a linha h como cabeçalho; as linhas seguintes são os dados."""
    nomes, vistos = [], {}
    for i, v in enumerate(bruto.iloc[h]):
        n = str(v).strip() if pd.notna(v) and str(v).strip() else f"Coluna {i+1}"
        vistos[n] = vistos.get(n, 0) + 1
        nomes.append(n if vistos[n] == 1 else f"{n}_{vistos[n]}")
    df = bruto.iloc[h + 1:].dropna(how="all")
    df.columns = nomes
    return df


def porcentagem_valida(serie):
    s = serie.dropna()
    if s.empty:
        return 0.0
    return sum(interpretar_endereco(v) is not None for v in s) / len(s)


def detectar_colunas_endereco(df, minimo=0.3):
    """Colunas cujos valores seguem os padrões de endereço: [(coluna, % válidos)]."""
    res = [(c, porcentagem_valida(df[c])) for c in df.columns]
    return sorted([r for r in res if r[1] >= minimo], key=lambda x: -x[1])


def ler_planilha(arquivo, max_cabecalho=15):
    """Lê tudo como texto (preserva zeros) e procura a linha de cabeçalho.
    Retorna (df, linha_cabecalho, erro)."""
    try:
        bruto = pd.read_excel(arquivo, header=None, dtype=str)
    except Exception as e:
        return None, None, f"Não foi possível ler o arquivo: {e}"
    if bruto.empty or bruto.shape[1] == 0:
        return None, None, "A planilha não contém dados."
    # Primeira linha que contém algum endereço válido = primeira linha de dados.
    r = None
    for i in range(len(bruto)):
        if any(interpretar_endereco(v) is not None for v in bruto.iloc[i].dropna()):
            r = i
            break
    if r is None:
        return _montar(bruto, 0), 0, None   # nada reconhecido: a tela mostra o diagnóstico
    h = r - 1
    while h >= 0 and bruto.iloc[h].notna().sum() == 0:
        h -= 1                              # pula linhas em branco acima dos dados
    if h < 0:                               # sem cabeçalho: cria nomes genéricos
        bruto = pd.concat([pd.DataFrame([[None] * bruto.shape[1]]), bruto], ignore_index=True)
        h = 0
    return _montar(bruto, h), h, None
