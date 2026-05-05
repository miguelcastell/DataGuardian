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

## Como funciona

### Fluxo interno de dados

```
CSV (upload)
    │
    ▼
data_io.py          → lê e faz cache do DataFrame por hash do arquivo
    │
    ▼
quality.py          → analyze_dataset(df) → dicionário de análise
    │
    ▼
scoring.py          → compute_quality_score(analysis) → score, nível, breakdown
    │
    ▼
sections.py         → renderiza os 5 painéis na UI (side effects apenas)
    │
    ▼
cleaning.py         → clean_dataset(df, **options) → DataFrame tratado + relatório
    │
    ▼
Export              → CSV / Excel / JSON
```

### Métodos de detecção

#### Dados faltantes
`df.isna()` — contagem direta e percentual por coluna e no total.

#### Placeholders de nulo
Varredura por token em colunas texto. Tokens reconhecidos: `""`, `" "`, `na`, `n/a`, `null`, `none`, `nan`, `-`. A comparação é case-insensitive.

#### Outliers — IQR + Z-score combinados
Dois métodos rodados em paralelo para colunas numéricas:
- **IQR**: outlier se `valor < Q1 − 1.5×IQR` ou `valor > Q3 + 1.5×IQR`
- **Z-score**: outlier se `|z| > 3` (onde `z = (valor − média) / desvio padrão`)

O score usa a média IQR das colunas; ambas as contagens são exibidas na UI.

#### Inferência de tipo
Para cada coluna `object`, tenta converter todos os valores:
- Se ≥ 80% convertíveis para numérico → sugere `numeric`
- Se ≥ 80% convertíveis para datetime → sugere `datetime`

Colunas já tipadas corretamente não são reportadas.

#### Padrões semânticos brasileiros
Regex `fullmatch` aplicado por coluna. Um padrão é confirmado se ≥ 60% dos valores não-nulos casam:

| Padrão | Exemplo |
|---|---|
| `email` | `ana@empresa.com.br` |
| `cpf` | `123.456.789-09` ou `12345678909` |
| `cep` | `01310-100` ou `01310100` |
| `telefone` | `11 99999-0001` ou `+55 (11) 99999-0001` |
| `url` | `https://exemplo.com` |

No máximo um padrão é atribuído por coluna (o primeiro que passar o limiar).

#### Cardinalidade suspeita
- **Alta**: coluna texto com >90% de valores únicos e mais de 10 registros → possível ID/chave primária
- **Baixa**: coluna numérica com ≤5 valores únicos e mais de 10 registros → possível categórica mal tipada

#### Quase-duplicatas textuais
Usa `rapidfuzz.fuzz.ratio` entre pares de valores únicos (até 200 por coluna). Pares com similaridade entre 80% e 99% são reportados. Se `rapidfuzz` não estiver instalado, a detecção é silenciosamente pulada.

---

### Sistema de score

O score parte de 100 e desconta penalidades por dimensão:

```
penalidade_por_dimensão = min(percentual_do_problema × peso, cap)
score = 100 − soma(penalidades)   [clampado entre 0 e 100]
```

| Dimensão | Peso padrão | Cap |
|---|---|---|
| Linhas duplicadas | 2.0 | 20 pts |
| Valores ausentes | 1.5 | 30 pts |
| Inconsistências de tipo | 1.0 | 15 pts |
| Tokens de nulo / Colunas constantes | 0.8 | 10 pts cada |
| Outliers | 0.5 | 10 pts |

Os caps impedem que um único problema zerize o score — por exemplo, 80% de ausência sem cap geraria uma penalidade de 120 pts.

**Presets de domínio** ajustam os pesos sem alterar o código:

| Preset | Duplicatas | Ausentes | Tipo |
|---|---|---|---|
| Geral | 2.0 | 1.5 | 1.0 |
| Financeiro | 3.0 | 2.5 | 1.5 |
| Marketing / CRM | 1.5 | 1.0 | 0.8 |
| RH / Pessoas | 2.5 | 2.0 | 1.0 |
| Logística / Operações | 2.0 | 1.8 | 1.2 |

**Níveis de qualidade:**

| Score | Nível |
|---|---|
| ≥ 90 | Excelente |
| 75–89 | Bom |
| 55–74 | Atenção |
| < 55 | Crítico |

---

### Tratamento de dados (`clean_dataset`)

As transformações são aplicadas nesta ordem:

1. Normalização de nomes de colunas → `lowercase_snake_case`, colisões resolvidas com sufixo `_1`, `_2`…
2. Trim de strings → `str.strip()` em todas as colunas texto
3. Substituição de tokens de nulo → converte placeholders para `NaN`
4. Remoção de duplicatas exatas
5. Remoção de colunas acima do limiar de faltantes configurado
6. Imputação numérica → mediana, média ou zero
7. Imputação categórica → moda ou `"unknown"`
8. Tratamento de outliers:
   - `cap` (winsorização) → clipa nos limites IQR ou ±3σ
   - `remove` → remove linhas que contenham outliers em qualquer coluna numérica

A função retorna `(DataFrame_tratado, relatório_dict)`. O relatório contém contagens de cada operação aplicada (linhas removidas, colunas renomeadas, tokens convertidos, etc.).

---

## Testes

```bash
python -m pytest -q
```

45 testes, todos passando:

| Arquivo | Testes | O que cobre |
|---|---|---|
| `tests/test_quality.py` | 16 | `analyze_dataset` — guards, lógica de detecção, cardinalidade, fuzzy |
| `tests/test_cleaning.py` | 18 | `clean_dataset` — normalização, dedup, imputação, tratamento de outliers |
| `tests/test_scoring.py` | 11 | `compute_quality_score` — range, breakdown, presets de domínio |

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
