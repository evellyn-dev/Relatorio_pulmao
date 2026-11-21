from datetime import date
from io import BytesIO
from math import ceil
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from relatorios import para_numero

LARANJA, LARANJA_CLARO, ZEBRA = "F97316", "FFF1E8", "FAFAFA"
CINZA, CINZA_TEXTO = "E5E5E5", "737373"
F = lambda **k: Font(name="Arial", size=k.pop("size", 10), **k)
FINA = Side(style="thin", color=CINZA)
BORDA = Border(left=FINA, right=FINA, top=FINA, bottom=FINA)
BORDA_TOTAL = Border(left=FINA, right=FINA, bottom=FINA, top=Side(style="medium", color=LARANJA))


def nome_arquivo():
    return f"Relatorio_Pulmao_{date.today():%Y-%m-%d}.xlsx"


def _inteiros(serie):
    s = pd.to_numeric(serie, errors="coerce").dropna()
    return bool(((s % 1) == 0).all())


def _fmt_num(serie):
    return "#,##0" if _inteiros(serie) else "#,##0.00"


def _preparar_folha(ws):
    ws.sheet_view.showGridLines = False
    ws.sheet_properties.tabColor = LARANJA
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_options.horizontalCentered = True


def _tabela(ws, cols, linhas, formatos):
    """Escreve cabeçalho + linhas com estilo único. formatos: {índice_coluna(1..): formato numérico}."""
    ws.append(cols)
    for j in range(1, len(cols) + 1):
        c = ws.cell(1, j)
        c.font = F(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=LARANJA)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = BORDA
    ws.row_dimensions[1].height = 26
    for i, linha in enumerate(linhas, 2):
        ws.append(linha)
        for j in range(1, len(cols) + 1):
            c = ws.cell(i, j)
            c.font = F()
            c.border = BORDA
            if i % 2 == 1:
                c.fill = PatternFill("solid", fgColor=ZEBRA)
            if j in formatos:
                c.number_format = formatos[j]
                c.alignment = Alignment(horizontal="right", vertical="center", indent=1)
            else:
                c.number_format = "@"
                c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.freeze_panes = "A2"
    ws.print_title_rows = "1:1"
    return len(linhas) + 1


def _total(ws, linha, ncols, rotulo, formulas, formatos):
    """Linha de total logo abaixo dos dados. formulas: {coluna: '=SUM(...)'}."""
    for j in range(1, ncols + 1):
        c = ws.cell(linha, j)
        c.font = F(bold=True)
        c.fill = PatternFill("solid", fgColor=LARANJA_CLARO)
        c.border = BORDA_TOTAL
        c.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.cell(linha, 1, rotulo)
    for j, f in formulas.items():
        c = ws.cell(linha, j, f)
        c.number_format = formatos.get(j, "#,##0")
        c.alignment = Alignment(horizontal="right", vertical="center", indent=1)
    ws.row_dimensions[linha].height = 22


def _larguras(ws, minimo=11, maximo=42):
    for col in ws.columns:
        tam = max((len(f"{c.value:,.0f}") if isinstance(c.value, (int, float))
                   else len(str(c.value)) if c.value and not str(c.value).startswith("=")
                   else 12) for c in col)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max(minimo, min(maximo, int(tam * 1.15) + 4))


def _aba_resumo(wb, resumo, ref_total):
    r = wb.create_sheet("Resumo", 0)
    _preparar_folha(r)
    r.column_dimensions["A"].width = 30
    r.column_dimensions["B"].width = 24
    r["A1"] = "RELATÓRIO PULMÃO"
    r["A1"].font = F(bold=True, size=18, color=LARANJA)
    r.row_dimensions[1].height = 30
    r["A2"] = resumo.get("ident", "")
    r["A2"].font = F(color=CINZA_TEXTO)
    for j, t in enumerate(("Indicador", "Valor"), 1):
        c = r.cell(4, j, t)
        c.font = F(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=LARANJA)
        c.alignment = Alignment(horizontal="center" if j == 2 else "left", vertical="center")
        c.border = BORDA
    itens = [("Registros", resumo["registros"]), ("Endereços", resumo["enderecos"]),
             ("Produtos distintos", resumo["produtos"]), ("Saldo total", None)]
    for i, (k, v) in enumerate(itens, 5):
        destaque = k == "Saldo total"
        a, b = r.cell(i, 1, k), r.cell(i, 2)
        if destaque and ref_total:
            b.value = f"={ref_total}"
        elif v is not None:
            b.value = v
        a.font = F(bold=destaque, size=12 if destaque else 10)
        b.font = F(bold=True, size=12 if destaque else 10, color=LARANJA if destaque else "171717")
        for c in (a, b):
            c.border = BORDA
            c.alignment = Alignment(vertical="center", horizontal="left" if c is a else "right")
            if destaque:
                c.fill = PatternFill("solid", fgColor=LARANJA_CLARO)
        b.number_format = resumo.get("fmt_saldo", "#,##0") if destaque else "#,##0"
        r.row_dimensions[i].height = 22
    linha = 5 + len(itens) + 1
    r.cell(linha, 1, "Parâmetros do relatório").font = F(bold=True, size=11)
    r.cell(linha, 1).border = Border(bottom=Side(style="medium", color=LARANJA))
    r.cell(linha, 2).border = Border(bottom=Side(style="medium", color=LARANJA))
    for k, t in enumerate(resumo.get("parametros", []), linha + 1):
        r.merge_cells(start_row=k, start_column=1, end_row=k, end_column=2)
        c = r.cell(k, 1, t)
        c.font = F()
        c.alignment = Alignment(wrap_text=True, vertical="top")
        r.row_dimensions[k].height = 15 * max(1, ceil(len(t) / 58)) + 4


def para_excel_bytes(df, col_qtd=None, extras=None, resumo=None):
    """Excel organizado: Resumo, Relatorio (registros + SALDO TOTAL) e abas de saldo com TOTAL.
    Endereços ficam como texto; a quantidade é gravada como número para poder somar."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Relatorio"
    _preparar_folha(ws)
    cols = list(df.columns)
    qi = cols.index(col_qtd) + 1 if col_qtd in cols else None
    qnum = para_numero(df[col_qtd]) if qi else None
    linhas = []
    for idx, row in df.iterrows():
        linha = []
        for j, c in enumerate(cols, 1):
            v = row[c]
            if pd.isna(v):
                linha.append(None)
            elif qi == j and pd.notna(qnum.loc[idx]):
                n = qnum.loc[idx]
                linha.append(int(n) if float(n).is_integer() else float(n))
            else:
                linha.append(str(v))
        linhas.append(linha)
    fmt_q = {qi: _fmt_num(qnum)} if qi else {}
    fim = _tabela(ws, cols, linhas, fmt_q)
    ref_total = None
    if qi:
        L = get_column_letter(qi)
        _total(ws, fim + 1, len(cols), "SALDO TOTAL", {qi: f"=SUM({L}2:{L}{fim})"}, fmt_q)
        ref_total = f"Relatorio!{L}{fim + 1}"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{fim}"
    _larguras(ws)

    for nome, tab in (extras or {}).items():
        tab = tab.copy()
        if "Saldo total" in tab and "% do saldo" in tab:     # sem arredondar: total fecha em 100%
            tot = tab["Saldo total"].sum()
            tab["% do saldo"] = tab["Saldo total"] / tot if tot else 0.0
        w = wb.create_sheet(nome[:31])
        _preparar_folha(w)
        fm = {}
        for j, c in enumerate(tab.columns, 1):
            if c in ("Endereços", "Registros"):
                fm[j] = "#,##0"
            elif c == "Saldo total":
                fm[j] = _fmt_num(tab[c])
            elif c == "% do saldo":
                fm[j] = "0.0%"
        dados = [[None if (isinstance(v, float) and v != v) else
                  (v if isinstance(v, (int, float)) else str(v)) for v in l]
                 for l in tab.itertuples(index=False)]
        f2 = _tabela(w, list(tab.columns), dados, fm)
        form = {j: f"=SUM({get_column_letter(j)}2:{get_column_letter(j)}{f2})"
                for j, c in enumerate(tab.columns, 1) if c in ("Registros", "Saldo total", "% do saldo")}
        _total(w, f2 + 1, len(tab.columns), "TOTAL", form, fm)
        w.auto_filter.ref = f"A1:{get_column_letter(len(tab.columns))}{f2}"
        _larguras(w)

    if resumo:
        resumo = dict(resumo, fmt_saldo=fmt_q.get(qi, "#,##0") if qi else "#,##0")
        _aba_resumo(wb, resumo, ref_total)
        wb.active = 0

    out = BytesIO()
    wb.save(out)
    return out.getvalue()
