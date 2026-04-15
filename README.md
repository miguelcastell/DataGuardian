# Data Guardian

Plataforma de qualidade de dados para arquivos CSV, construída com Streamlit.

O projeto permite diagnosticar problemas de qualidade, aplicar tratamento assistido e exportar os dados limpos para uso em BI, análise e modelagem.

## Principais funcionalidades

- Upload de um ou mais arquivos CSV.
- Diagnóstico automático de qualidade:
  - dados faltantes
  - linhas duplicadas
  - colunas constantes
  - outliers
  - inconsistências de tipo
  - placeholders de nulo (NA, N/A, null, etc.)
- Score de qualidade (0 a 100) com classificação por nível.
- Priorização de problemas com recomendações de ação.
- Tratamento configurável com preview antes/depois.
- Exportação em CSV, JSON e Excel (quando disponível).
- Painel visual com histogramas, barras, dispersão e correlação.

## Stack

- Python
- Streamlit
- Pandas
- NumPy
- Plotly
- OpenPyXL
- Pytest

## Estrutura do projeto

```text
app/
  dashboard.py                # Ponto de entrada do app
  dashboard_app/
    app_main.py               # Orquestração do fluxo e estado
    data_io.py                # Leitura/caching de CSV
    scoring.py                # Cálculo de score e prioridades
    sections.py               # Seções da interface
    styles.py                 # Design system e componentes visuais

src/
  data/
    quality.py                # Diagnóstico de qualidade
    cleaning.py               # Regras de tratamento de dados

tests/
  test_quality.py
  test_cleaning.py
  test_scoring.py
```

## Instalação

```bash
pip install -r requirements.txt
```

## Execução local

```bash
python -m streamlit run app/dashboard.py
```

## Fluxo no app

1. Faça upload de um ou mais CSVs.
2. Escolha o dataset ativo.
3. Revise score, alertas e problemas priorizados.
4. Configure as regras de tratamento.
5. Compare antes/depois.
6. Exporte os dados tratados e o relatório.
7. Explore os insights visuais.

## Testes

```bash
python -m pytest -q
```

## Casos de uso

- Data profiling rápido antes de análises.
- Padronização de dados para dashboards.
- Pré-processamento para pipelines de ciência de dados.
- Auditoria de qualidade em bases de fornecedores.

## Roadmap sugerido

- Regras de validação por schema.
- Templates de tratamento por tipo de dataset.
- Comparação entre versões do mesmo arquivo.
- Métricas históricas de qualidade por execução.
