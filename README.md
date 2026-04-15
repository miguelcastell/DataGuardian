# Data Guardian

Aplicacao para diagnostico e tratamento de qualidade de dados em arquivos CSV.

## O que o projeto faz

- Upload de um ou mais CSVs
- Diagnostico de qualidade (faltantes, duplicidades, outliers, inconsistencias de tipo)
- Tratamento configuravel dos dados
- Exportacao do CSV tratado
- Painel de visualizacao com graficos

## Estrutura atual

```
app/
  dashboard.py
src/
  data/
    cleaning.py
    quality.py
```

## Instalacao

```bash
pip install -r requirements.txt
```

## Execucao

```bash
python -m streamlit run app/dashboard.py
```

## Fluxo no app

1. Envie um ou mais CSVs
2. Escolha o dataset ativo
3. Revise os problemas detectados
4. Configure o tratamento
5. Baixe o CSV tratado
6. Abra os insights BI
