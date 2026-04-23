# DataGuardian

**Plataforma de qualidade de dados para arquivos CSV**, construída com Streamlit e voltada para equipes brasileiras de dados.

Faça upload de um CSV → receba um diagnóstico completo → trate os problemas com um clique → exporte os dados limpos prontos para BI ou modelagem.

---

## Funcionalidades

### Diagnóstico automático

| Dimensão | O que detecta |
|---|---|
| Dados faltantes | Contagem e % por coluna, mapa de ausência visual |
| Linhas duplicadas | Duplicatas exatas em todo o dataset |
| Placeholders de nulo | Tokens como `NA`, `N/A`, `null`, `-`, `none` disfarçados de valores |
| Inconsistências de tipo | Colunas texto que deveriam ser numéricas ou datas |
| Outliers | Método IQR (1.5×IQR) e Z-score combinados |
| Colunas constantes | Colunas sem variação que não agregam valor preditivo |
| Cardinalidade suspeita | IDs disfarçados de texto e categóricas numéricas mal tipadas |
| Quase-duplicatas textuais | Valores com alta similaridade (ex: `"João Silva"` vs `"Joao Silva"`) via `rapidfuzz` |
| Padrões semânticos (BR) | Detecta CPF, CEP, telefone, e-mail e URL automaticamente |

### Score de qualidade configurável

- Score 0–100 com classificação: **Excelente** / **Bom** / **Atenção** / **Crítico**
- Pesos ajustáveis por **preset de domínio**: Geral, Financeiro, Marketing/CRM, RH/Pessoas, Logística
- Fila de problemas priorizados por severidade com ação recomendada

### Tratamento configurável

- Remoção de duplicatas, normalização de nomes de colunas, trim de strings
- Imputação numérica: mediana, média ou zero
- Imputação categórica: moda ou `"unknown"`
- Remoção de colunas acima de um limiar de faltantes
- **Tratamento de outliers**: capping (winsorização) ou remoção de linhas — por IQR ou Z-score
- Preview antes/depois com células alteradas marcadas

### Exportação

- CSV tratado
- Excel com abas de qualidade (requer `openpyxl`)
- Relatório JSON com score, sumário e log de transformações

### Insights visuais

- Histograma de distribuição, frequência por categoria
- Gráfico de dispersão, matriz de correlação, boxplot de outliers

---

## Instalação

```bash
pip install -r requirements.txt
```

## Execução local

```bash
python -m streamlit run app/dashboard.py
```

Acesse `http://localhost:8501`. Um dataset de demonstração está disponível em [`data/exemplo.csv`](data/exemplo.csv).

---

## Fluxo de uso

```
Upload CSV  →  Diagnóstico  →  Score + Alertas  →  Tratamento  →  Export / BI
```

1. Faça upload de um ou mais CSVs na barra lateral
2. Selecione o **preset de domínio** para calibrar o score (ex: Financeiro penaliza duplicatas mais)
3. Revise o score, a fila de problemas priorizados e os alertas
4. Configure as regras de tratamento — preview ao vivo antes/depois
5. Exporte os dados tratados (CSV, Excel) e o relatório JSON
6. Explore histogramas, correlações e boxplots na aba Insights BI

---

## Estrutura do projeto

```
app/
  dashboard.py                # Ponto de entrada (streamlit run)
  dashboard_app/
    app_main.py               # Orquestração principal e session state
    data_io.py                # Leitura e cache de CSV
    scoring.py                # Score de qualidade e presets de domínio
    sections.py               # Renderização de cada painel
    styles.py                 # Design system (CSS, metric_card, badge)

src/
  data/
    quality.py                # analyze_dataset() — diagnóstico completo
    cleaning.py               # clean_dataset() — tratamento configurável

data/
  exemplo.csv                 # Dataset de demonstração

tests/
  test_quality.py
  test_cleaning.py
  test_scoring.py
```

---

## Testes

```bash
python -m pytest -q
```

---

## Stack

Python · Streamlit · Pandas · NumPy · Plotly · RapidFuzz · OpenPyXL · Pytest

---

## Casos de uso

- Data profiling rápido antes de análises exploratórias
- Padronização de dados para dashboards de BI
- Pré-processamento para pipelines de ciência de dados
- Auditoria de qualidade em bases recebidas de fornecedores
