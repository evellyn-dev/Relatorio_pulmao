from datetime import datetime
from filtros import ConfigPP


def identificar_relatorio(tipo):
    return f"{tipo} — {datetime.now():%d/%m/%Y %H:%M}"


def resumo_config(c):
    if isinstance(c, ConfigPP):
        return f"PP: de {c.inicial} até {c.final}"
    pred = "todos do lado" if c.predios is None else ", ".join(c.predios)
    apto = "todos" if c.apartamentos is None else ", ".join(c.apartamentos)
    return (f"Rua {c.rua}: lado {c.lado}; prédios {pred}; "
            f"níveis {', '.join(c.niveis or [])}; apartamentos {apto}")


# ---------------- Métricas ----------------
import unicodedata
import pandas as pd


def _norm(t):
    return unicodedata.normalize("NFKD", str(t)).encode("ascii", "ignore").decode().lower()


def detectar_colunas(df):
    """Sugere colunas de produto, descrição e quantidade pelo nome. Valores podem ser None."""
    cols = {c: _norm(c) for c in df.columns}
    def achar(*grupos):
        for g in grupos:
            for c, n in cols.items():
                if all(k in n for k in g):
                    return c
        return None
    return {
        "produto": achar(("cod", "prod"), ("cod", "item"), ("sku",), ("codigo",), ("produto",), ("item",)),
        "descricao": achar(("descri",), ("nome",)),
        "quantidade": achar(("quant",), ("qtd",), ("qtde",), ("saldo",)),
    }


def para_numero(serie):
    """Texto -> número, aceitando '1.234,56' e '1234.56'. Inválido vira NaN."""
    def conv(v):
        t = str(v).strip()
        if "," in t:
            t = t.replace(".", "").replace(",", ".")
        return t
    return pd.to_numeric(serie.dropna().map(conv), errors="coerce").reindex(serie.index)


def fmt_num(v):
    """Formato brasileiro: 1.234 ou 1.234,5"""
    if pd.isna(v):
        return "-"
    s = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def _agrupar(d, chave, rotulo):
    g = d.groupby(chave, dropna=False)
    out = g.agg(**{"Endereços": ("_end", "nunique"), "Registros": ("_end", "size"),
                   "Saldo total": ("_q", "sum")}).reset_index()
    out = out.rename(columns={chave: rotulo})
    total = out["Saldo total"].sum()
    out["% do saldo"] = (out["Saldo total"] / total * 100).round(1) if total else 0.0
    return out.sort_values("Saldo total", ascending=False).reset_index(drop=True)


def _base(df, col_end, col_qtd, extra=None):
    d = pd.DataFrame({"_end": df[col_end], "_q": para_numero(df[col_qtd])}, index=df.index)
    for k, v in (extra or {}).items():
        d[k] = v
    return d


def saldo_por_produto(df, col_prod, col_qtd, col_end, col_desc=None):
    d = _base(df, col_end, col_qtd, {"_p": df[col_prod].fillna("(sem código)")})
    out = _agrupar(d, "_p", "Produto")
    if col_desc:
        desc = df[col_desc].groupby(df[col_prod].fillna("(sem código)")).first()
        out.insert(1, "Descrição", out["Produto"].map(desc))
    return out


def saldo_por_campo(df, parsed, campo, col_qtd, col_end, rotulo):
    d = _base(df, col_end, col_qtd, {"_c": parsed.loc[df.index, campo].fillna("-")})
    out = _agrupar(d, "_c", rotulo)
    return out.sort_values(rotulo).reset_index(drop=True)


def metricas(df, col_end, col_qtd, col_prod):
    q = para_numero(df[col_qtd])
    return {"registros": len(df), "enderecos": df[col_end].nunique(),
            "produtos": df[col_prod].nunique(dropna=False), "saldo": q.sum(),
            "qtd_invalidas": int(q.isna().sum() - df[col_qtd].isna().sum())}
