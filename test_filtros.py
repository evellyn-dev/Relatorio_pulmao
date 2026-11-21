"""Teste com dados sintéticos: python test_filtros.py"""
import pandas as pd
from filtros import *

def end(rua, pred, niv, apto, andar="0100"): return f"{andar}{rua}{pred:02d}{niv:02d}{apto:02d}"
rows = [end("03", p, n, a) for p in (1, 2, 3, 4) for n in (0, 1, 2) for a in (1, 2)]
rows.remove(end("03", 2, 2, 2))                     # prédio 02 sem apto 02 no nível 02
rows += [end("08", p, 0, a) for p in (1, 2, 3) for a in (1, 2)]
rows += ["PP12", "PP13", "PP14", "PP15", "PP20", "PP21", "123", "01000302"]
df = pd.DataFrame({"Endereco": rows, "Qtd": range(len(rows))})
p = interpretar_coluna(df["Endereco"])
assert (~p.valido).sum() == 2

r, c = gerar_relatorio(df, p, [ConfigRua("03", "Par", None, ["00", "02"], None),
                               ConfigRua("08", "Ímpar", None, ["00"], ["01"])])
assert c == {"Rua 03": 2*2*2 - 1, "Rua 08": 2}, c   # sem registros fictícios
assert set(r.Endereco.str[4:6]) == {"03", "08"}
r, _ = gerar_relatorio(df, p, [ConfigRua("03", "Ambos", ["01"], ["00"], ["02"])])
assert list(r.Endereco) == [end("03", 1, 0, 2)]
r, c = gerar_relatorio(df, p, [ConfigPP("PP12", "PP15")])
assert list(r.Endereco) == ["PP12", "PP13", "PP14", "PP15"]
r, _ = gerar_relatorio(df, p, [ConfigRua("03", "Par", None, ["00"], None),
                               ConfigRua("03", "Ambos", None, ["00"], None)])
assert len(r) == 8 and r.index.is_unique            # sem duplicação
assert validar_pp(p, ConfigPP("PP20", "PP12")) and validar_rua(p, ConfigRua("03", niveis=[]))
assert not validar_rua(p, ConfigRua("03", "Ambos", ["26"], ["00"]))   # inexistente não é erro
r, _ = gerar_relatorio(df, p, [ConfigRua("03", "Ambos", ["26", "01"], ["00", "09"], None)])
assert set(r.Endereco.str[6:8]) == {"01"} and set(r.Endereco.str[8:10]) == {"00"}   # só o que existe
assert normalizar_lista(["5", "05", "x", "123", " 7 "]) == (["05", "07"], ["x", "123"])
from regras_logisticas import PREDIOS_PADRAO, NIVEIS_PADRAO
assert PREDIOS_PADRAO["Ímpar"][0] == "01" and PREDIOS_PADRAO["Ímpar"][-1] == "25" and len(PREDIOS_PADRAO["Ímpar"]) == 13
assert PREDIOS_PADRAO["Par"][0] == "02" and PREDIOS_PADRAO["Par"][-1] == "26" and NIVEIS_PADRAO == ["00", "01", "02", "03", "04"]
from exportador import para_excel_bytes
from openpyxl import load_workbook; import io
ws = load_workbook(io.BytesIO(para_excel_bytes(r))).active
assert ws["A2"].value.startswith("0100") and ws["A1"].value == "Endereco"
from relatorios import *
x = pd.DataFrame({"End": ["a", "a", "b", "c"], "Cod": ["P1", "P2", "P1", None],
                  "Desc": ["x", "y", "x", "z"], "Qtd": ["10", "1.234,5", "5", "abc"]})
sp = saldo_por_produto(x, "Cod", "Qtd", "End", "Desc")
assert sp.loc[sp.Produto == "P1", "Saldo total"].iloc[0] == 15 and sp["Saldo total"].max() == 1234.5
assert metricas(x, "End", "Qtd", "Cod")["qtd_invalidas"] == 1
assert detectar_colunas(pd.DataFrame(columns=["Endereço", "Código Produto", "Descrição", "Quantidade"])) == \
    {"produto": "Código Produto", "descricao": "Descrição", "quantidade": "Quantidade"}
assert fmt_num(1234567) == "1.234.567" and fmt_num(1234.5) == "1.234,50"
print("OK: todos os testes passaram")
