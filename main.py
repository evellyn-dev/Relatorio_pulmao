import streamlit as st
from leitor_excel import ler_planilha, detectar_colunas_endereco, porcentagem_valida
from filtros import (interpretar_coluna, ConfigRua, ConfigPP, gerar_relatorio,
                     validar_rua, validar_pp, validar_tudo, normalizar_lista)
from regras_logisticas import (TIPOS_RELATORIO, RUAS_CONHECIDAS, LADOS, APARTAMENTOS,
                               PREDIOS_PADRAO, NIVEIS_PADRAO)
from relatorios import (resumo_config, identificar_relatorio, detectar_colunas, metricas,
                        saldo_por_produto, saldo_por_campo, fmt_num)
from exportador import para_excel_bytes, nome_arquivo

st.set_page_config(page_title="RELATÓRIO PULMÃO", page_icon="📦", layout="centered")
st.markdown("""<style>
.stApp{background:#FFFFFF;color:#171717}
h1,h2,h3{color:#171717;font-weight:700}
.stButton>button,.stDownloadButton>button{border-radius:8px;border:1px solid #E5E5E5;background:#FFFFFF;color:#171717}
[data-testid="stMetric"]{border:1px solid #E5E5E5;border-radius:10px;padding:12px 16px}
[data-testid="stMetricValue"]{color:#F97316;font-weight:700}
.stTabs [aria-selected="true"]{color:#F97316}
.stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"]{background:#F97316;border-color:#F97316;color:#FFFFFF}
.tag{display:inline-block;background:#FFF1E8;color:#F97316;border-radius:6px;padding:2px 10px;font-size:.85rem;font-weight:600}
.caixa{border:1px solid #E5E5E5;border-radius:10px;padding:12px 16px;background:#F5F5F5;color:#737373}
</style>""", unsafe_allow_html=True)

S = st.session_state
for k, v in {"step": 1, "df": None, "nome": None, "col": None, "parsed": None, "tipo": None,
             "ruas": [], "configs": {}, "idx": 0, "res": None, "res_sig": None}.items():
    S.setdefault(k, v)

# Mantém os valores digitados nos campos de cada rua mesmo quando a aba não está na tela
# (o Streamlit apaga o estado de widgets que deixam de ser exibidos).
PREFIXOS = ("lado_", "modo_", "pred_", "niv_", "apto_", "pp_ini", "pp_fim")
for _k in list(S.keys()):
    if isinstance(_k, str) and _k.startswith(PREFIXOS):
        S[_k] = S[_k]

ETAPAS = ["Planilha", "Tipo", "Ruas", "Configuração", "Resumo", "Resultado"]


def ir(n):
    S.step = n
    st.rerun()


def goto(n):
    S.step = n


def editar(rua):
    S.idx = S.ruas.index(rua)
    S.step = 4


def nome_rua(r):
    return "PP" if r == "PP" else f"Rua {r}"


def pendentes():
    return [r for r in S.ruas if r not in S.configs]


def assinatura():
    return repr((S.tipo, S.col, [S.configs.get(r) for r in S.ruas]))


def liberado():
    """Maior etapa que já pode ser aberta."""
    if S.df is None: return 1
    if S.tipo is None: return 2
    if not S.ruas: return 3
    if pendentes(): return 4
    if S.res is None: return 5
    return 6


def gerar():
    cfgs = [S.configs[r] for r in S.ruas]
    erros = validar_tudo(S.parsed, cfgs)
    if erros:
        S.erros_gerar = erros
        return
    S.erros_gerar = []
    S.res = gerar_relatorio(S.df, S.parsed, cfgs, S.tipo) + (identificar_relatorio(S.tipo),)
    S.res_sig = assinatura()
    S.step = 6


# ---------------- Cabeçalho e navegação por abas ----------------
st.title("RELATÓRIO PULMÃO")
st.caption("Sistema de filtragem e extração de relatórios de estoque.")
feitas = {1: S.df is not None, 2: S.tipo is not None, 3: bool(S.ruas),
          4: bool(S.ruas) and not pendentes(), 5: S.res is not None, 6: S.res is not None}
rotulos = [f"{'✓ ' if feitas[i] else ''}{i}. {n}" for i, n in enumerate(ETAPAS, 1)]
atual = rotulos[S.step - 1]
escolha = st.segmented_control("Etapas", rotulos, default=atual, label_visibility="collapsed",
                               key=f"nav_{S.step}_{abs(hash('|'.join(rotulos)))}")
if escolha and escolha != atual:
    ir(rotulos.index(escolha) + 1)
st.divider()

_lib = liberado()
if S.step > _lib:
    st.info(f"Conclua primeiro a etapa «{ETAPAS[_lib - 1]}» para abrir esta aba.")
    st.button(f"Ir para «{ETAPAS[_lib - 1]}»", type="primary", on_click=goto, args=(_lib,))
    st.stop()

# ---------- 1. Planilha ----------
if S.step == 1:
    arq = st.file_uploader("Carregar planilha Excel", type=["xlsx", "xls"])
    if arq is None and S.df is not None:
        st.success(f"Arquivo carregado: **{S.nome}** · {len(S.df)} linhas · "
                   f"coluna de endereço: **{S.col}**")
        st.caption("Para usar outra planilha, carregue o novo arquivo acima. "
                   "Suas configurações atuais continuam salvas nas outras abas.")
        with st.expander("Pré-visualização"):
            st.dataframe(S.df.head(20), width="stretch")
        st.button("Continuar", type="primary", on_click=goto, args=(2,))
    elif arq is not None:
        df, h, erro = ler_planilha(arq)
        if erro:
            st.error(erro)
        else:
            st.success(f"Arquivo: **{arq.name}** · {len(df)} linhas · {df.shape[1]} colunas"
                       + (f" · cabeçalho na linha {h+1}" if h else ""))
            cands = dict(detectar_colunas_endereco(df))
            if not cands:
                st.error("Nenhuma coluna com endereços válidos (12 dígitos ou PP##) foi encontrada. "
                         "Escolha a coluna manualmente abaixo e confira os valores de exemplo.")
            ordem = list(cands) + [c for c in df.columns if c not in cands]
            col = st.selectbox("Coluna de endereço", ordem,
                               format_func=lambda c: f"{c} ({porcentagem_valida(df[c]):.0%} válidos)")
            amostra = [repr(v) for v in df[col].dropna().head(5)]
            st.caption("Exemplos desta coluna: " + (", ".join(amostra) or "(vazia)"))
            p = interpretar_coluna(df[col])
            if not p["valido"].any():
                st.error("Esta coluna não tem nenhum endereço no formato esperado "
                         "(12 dígitos, ex.: 010003020001, ou PP12). Escolha outra coluna.")
            else:
                inval = int((~p["valido"] & df[col].notna()).sum())
                if inval:
                    st.warning(f"{inval} linha(s) com endereço malformado ou incompleto. "
                               "Elas não serão corrigidas e ficarão fora dos filtros.")
                with st.expander("Pré-visualização"):
                    st.dataframe(df.head(20), width="stretch")
                if st.button("Confirmar planilha e continuar", type="primary"):
                    mesma = (S.df is not None and S.nome == arq.name and S.col == col
                             and len(S.df) == len(df))
                    S.df, S.nome, S.col, S.parsed = df, arq.name, col, p
                    if not mesma:                      # planilha nova: recomeça as ruas
                        S.ruas, S.configs, S.res, S.idx = [], {}, None, 0
                    ir(2)

# ---------- 2. Tipo ----------
elif S.step == 2:
    nomes = list(TIPOS_RELATORIO)
    tipo = st.radio("Tipo de relatório", nomes, index=nomes.index(S.tipo) if S.tipo in nomes else 0)
    if st.button("Confirmar tipo e continuar", type="primary"):
        S.tipo = tipo
        ir(3)

# ---------- 3. Ruas ----------
elif S.step == 3:
    p = S.parsed
    achadas = set(p.loc[p["tipo"] == "NUM", "rua"].dropna()) | (
        {"PP"} if (p["tipo"] == "PP").any() else set())
    opcoes = sorted(achadas | set(RUAS_CONHECIDAS), key=lambda r: (r == "PP", r))
    sem = [r for r in opcoes if r not in achadas]
    if sem:
        st.info("Sem registros na planilha: " + ", ".join(sem))
    st.caption("Você pode voltar aqui a qualquer momento para adicionar ou remover ruas "
               "(por exemplo, a PP). As ruas já configuradas não perdem as configurações.")
    sel = st.multiselect("Ruas", opcoes, default=[r for r in S.ruas if r in opcoes])
    if st.button("Confirmar ruas", type="primary"):
        if not sel:
            st.error("Selecione ao menos uma rua.")
        else:
            S.ruas = sorted(sel, key=lambda r: (r == "PP", r))
            S.configs = {k: v for k, v in S.configs.items() if k in S.ruas}
            pend = pendentes()
            if pend:
                S.idx = S.ruas.index(pend[0])
                ir(4)
            ir(5)

# ---------- 4. Configuração individual ----------
elif S.step == 4:
    p = S.parsed
    S.idx = min(S.idx, len(S.ruas) - 1)
    rl = [f"{'✓' if r in S.configs else '•'} {nome_rua(r)}" for r in S.ruas]
    sel = st.segmented_control("Rua", rl, default=rl[S.idx], label_visibility="collapsed",
                               key=f"navrua_{S.idx}_{abs(hash('|'.join(rl)))}")
    if sel and sel != rl[S.idx]:
        S.idx = rl.index(sel)
        st.rerun()
    rua = S.ruas[S.idx]
    st.subheader(nome_rua(rua))
    st.caption("✓ = configurada · • = pendente. Clique em outra rua acima quando quiser; "
               "nada do que você já preencheu é perdido.")
    cfg, extra = None, []
    if rua == "PP":
        disp = sorted(p.loc[p["tipo"] == "PP", "pp_num"].dropna().astype(int).unique())
        if disp:
            st.markdown(f"<div class='caixa'>PP existentes na planilha: PP{disp[0]} a PP{disp[-1]} "
                        f"({len(disp)} códigos)</div>", unsafe_allow_html=True)
        S.setdefault("pp_ini", "")
        S.setdefault("pp_fim", "")
        c1, c2 = st.columns(2)
        ini = c1.text_input("PP inicial", key="pp_ini", placeholder="PP12").strip().upper()
        fim = c2.text_input("PP final", key="pp_fim", placeholder="PP20").strip().upper()
        st.caption("A PP não possui prédio/nível/apartamento no código; "
                   "regras adicionais ainda não foram confirmadas.")
        cfg = ConfigPP(ini, fim)
    else:
        sub = p[(p["tipo"] == "NUM") & (p["rua"] == rua)]
        S.setdefault(f"lado_{rua}", "Ambos")
        lado = st.radio("Lado da rua", LADOS, horizontal=True, key=f"lado_{rua}")
        S.setdefault(f"modo_{rua}", "Todos os prédios do lado")
        modo = st.radio("Prédios", ["Todos os prédios do lado", "Selecionar prédios específicos"],
                        key=f"modo_{rua}")
        predios = None
        if modo.startswith("Selecionar"):
            kp = f"pred_{rua}_{lado}"
            S.setdefault(kp, [])
            opts = PREDIOS_PADRAO[lado] + [v for v in S[kp] if v not in PREDIOS_PADRAO[lado]]
            brutos = st.multiselect("Prédios (selecione ou digite outros números)", opts,
                                    key=kp, accept_new_options=True)
            predios, inv = normalizar_lista(brutos)
            if inv:
                extra.append(f"Prédios inválidos: {', '.join(inv)}. Use números de 1 ou 2 dígitos.")
            aus = [x for x in predios if x not in set(sub["predio"].dropna())]
            if aus:
                st.info(f"Sem registros na planilha para os prédios: {', '.join(aus)}.")
            fora = [x for x in predios if lado != "Ambos" and (int(x) % 2 == 0) != (lado == "Par")]
            if fora:
                st.warning(f"Prédios fora do lado {lado} (serão ignorados): {', '.join(fora)}.")
        else:
            st.caption("Serão considerados todos os prédios do lado que existirem na planilha.")
        kn = f"niv_{rua}"
        S.setdefault(kn, [])
        opts_n = NIVEIS_PADRAO + [v for v in S[kn] if v not in NIVEIS_PADRAO]
        brutos = st.multiselect("Níveis (selecione ou digite outros números)", opts_n,
                                key=kn, accept_new_options=True)
        niveis, inv_n = normalizar_lista(brutos)
        if inv_n:
            extra.append(f"Níveis inválidos: {', '.join(inv_n)}. Use números de 1 ou 2 dígitos.")
        aus_n = [x for x in niveis if x not in set(sub["nivel"].dropna())]
        if aus_n:
            st.info(f"Sem registros na planilha para os níveis: {', '.join(aus_n)}.")
        S.setdefault(f"apto_{rua}", "Todos")
        apto = st.radio("Apartamentos", APARTAMENTOS, horizontal=True, key=f"apto_{rua}")
        cfg = ConfigRua(rua, lado, predios, niveis, None if apto == "Todos" else [apto])
    erros = extra + (validar_pp(p, cfg) if rua == "PP" else validar_rua(p, cfg))
    for e in erros:
        st.error(e)
    if st.button("Confirmar e avançar", type="primary", disabled=bool(erros)):
        S.configs[rua] = cfg
        pend = pendentes()
        if pend:
            S.idx = S.ruas.index(pend[0])
            st.rerun()
        ir(5)

# ---------- 5. Resumo ----------
elif S.step == 5:
    st.write(f"**Tipo:** {S.tipo}  ·  **Arquivo:** {S.nome}")
    for r in S.ruas:
        a, b = st.columns([6, 1])
        a.markdown(f"- {resumo_config(S.configs[r])}")
        b.button("Editar", key=f"ed_{r}", on_click=editar, args=(r,))
    st.button("＋ Adicionar ou remover ruas", on_click=goto, args=(3,))
    st.divider()
    for e in S.get("erros_gerar", []):
        st.error(e)
    st.button("Gerar relatório", type="primary", on_click=gerar)

# ---------- 6. Resultado ----------
elif S.step == 6:
    res, contagem, ident = S.res
    st.subheader("Relatório gerado")
    st.caption(ident)
    if S.res_sig != assinatura():
        st.warning("As configurações mudaram depois que este relatório foi gerado. "
                   "Os dados abaixo estão desatualizados.")
        st.button("Atualizar relatório", type="primary", on_click=gerar)
    if res.empty:
        st.warning("Nenhum registro encontrado com as configurações escolhidas.")
    else:
        sug = detectar_colunas(S.df)
        todas = list(S.df.columns)
        with st.expander("Colunas usadas nas métricas", expanded=not (sug["produto"] and sug["quantidade"])):
            c1, c2, c3 = st.columns(3)
            idx = lambda c: todas.index(c) if c in todas else 0
            col_prod = c1.selectbox("Produto (código)", todas, index=idx(sug["produto"]))
            opc = ["(nenhuma)"] + todas
            col_desc = c2.selectbox("Descrição", opc, index=opc.index(sug["descricao"]) if sug["descricao"] else 0)
            col_qtd = c3.selectbox("Quantidade / saldo", todas, index=idx(sug["quantidade"]))
        col_desc = None if col_desc == "(nenhuma)" else col_desc
        m = metricas(res, S.col, col_qtd, col_prod)
        if m["qtd_invalidas"]:
            st.warning(f"{m['qtd_invalidas']} linha(s) com quantidade não numérica foram desconsideradas no saldo.")
        k = st.columns(4)
        k[0].metric("Registros", fmt_num(m["registros"]))
        k[1].metric("Endereços", fmt_num(m["enderecos"]))
        k[2].metric("Produtos distintos", fmt_num(m["produtos"]))
        k[3].metric("Saldo total", fmt_num(m["saldo"]))

        t_prod = saldo_por_produto(res, col_prod, col_qtd, S.col, col_desc)
        t_rua = saldo_por_campo(res, S.parsed, "rua", col_qtd, S.col, "Rua")
        t_niv = saldo_por_campo(res[S.parsed.loc[res.index, "tipo"] == "NUM"], S.parsed, "nivel",
                                col_qtd, S.col, "Nível")
        cfg_num = dict(hide_index=True, width="stretch", column_config={
            "Saldo total": st.column_config.NumberColumn(format="%.0f" if float(m["saldo"]).is_integer() else "%.2f"),
            "% do saldo": st.column_config.NumberColumn(format="%.1f%%")})

        a, b, c, d = st.tabs(["Saldo por produto", "Por rua e nível", "Registros", "Parâmetros"])
        with a:
            busca = st.text_input("Buscar produto (código ou descrição)", key="busca_prod")
            tp = t_prod
            if busca:
                alvo = tp.astype(str).agg(" ".join, axis=1).str.lower()
                tp = tp[alvo.str.contains(busca.lower(), regex=False)]
            st.dataframe(tp, **cfg_num)
            st.caption(f"{len(tp)} produto(s) · maiores saldos:")
            graf = t_prod.head(10).set_index("Descrição" if col_desc else "Produto")["Saldo total"]
            st.bar_chart(graf, color="#F97316")
        with b:
            st.markdown("**Por rua**")
            st.dataframe(t_rua, **cfg_num)
            st.markdown("**Por nível**")
            st.dataframe(t_niv, **cfg_num)
        with c:
            st.dataframe(res, width="stretch")
        with d:
            for kk, vv in contagem.items():
                st.markdown(f"- {kk}: {vv} registro(s) encontrados")
            for cf in [S.configs[r] for r in S.ruas if r in S.configs]:
                st.markdown(f"- {resumo_config(cf)}")

        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        resumo = {"ident": f"{ident} · {S.nome}", "registros": m["registros"],
                  "enderecos": int(m["enderecos"]), "produtos": int(m["produtos"]),
                  "parametros": [resumo_config(cf) for cf in [S.configs[r] for r in S.ruas if r in S.configs]]}
        st.download_button("Exportar Excel (registros + saldo total)",
                           para_excel_bytes(res, col_qtd, {"Saldo por produto": t_prod,
                                            "Por rua": t_rua, "Por nivel": t_niv}, resumo),
                           nome_arquivo(), mime, type="primary")
    st.divider()
    if st.button("Novo relatório"):
        for k in list(S.keys()): del S[k]
        st.rerun()
