# RELATÓRIO PULMÃO

Sistema de filtragem e extração de relatórios de estoque (pulmões) a partir de planilhas Excel
exportadas do ERP/WMS. Nenhum dado é guardado: a planilha é processada em memória durante o uso.

## Rodar no computador (Windows)

1. Instale o Python 3.10 ou superior (https://www.python.org/downloads/), marcando **Add python.exe to PATH**.
2. Baixe o projeto (botão **Code → Download ZIP** no GitHub) e extraia a pasta.
3. Dê duplo clique em **`abrir.bat`**. Na primeira vez ele instala as dependências e abre o sistema no navegador.

Pelo terminal, dentro da pasta do projeto:

```
pip install -r requirements.txt
python -m streamlit run main.py
```

## Arquivos

| Arquivo | Função |
|---|---|
| `main.py` | Interface (abas/etapas) |
| `leitor_excel.py` | Leitura da planilha e detecção da coluna de endereço |
| `regras_logisticas.py` | Regras de endereçamento, prédios e níveis padrão |
| `filtros.py` | Motor de filtragem e validações |
| `relatorios.py` | Métricas e saldo por produto |
| `exportador.py` | Exportação para Excel |
| `test_filtros.py` | Testes com dados sintéticos (`python test_filtros.py`) |

## Observação

Não envie planilhas reais da empresa para o repositório (o `.gitignore` já bloqueia `.xlsx`/`.xls`).
