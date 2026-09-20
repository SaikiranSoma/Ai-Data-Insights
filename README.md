# AI Data Insights

AI Data Insights is a web application that lets users upload multiple
CSV or Excel files and ask analytical questions in plain English.

The application converts questions into validated DuckDB SQL, executes
the SQL against uploaded data, and presents answers through tables,
KPIs and interactive charts.

## Live Demo

[Open the deployed application](PASTE_STREAMLIT_URL_HERE)

## Features

- Multiple CSV and Excel file upload
- Multi-sheet Excel support
- Automatic schema and missing-value profiling
- Cross-file SQL analysis
- Natural-language to SQL using GPT-OSS 20B
- Read-only SQL validation
- One automatic SQL repair attempt
- Query timeout and result limits
- Automatic KPI and chart selection
- CSV result download
- Execution history and feedback
- No permanent storage of uploaded data

## Architecture

```mermaid
flowchart TD
    A[CSV and Excel uploads] --> B[Pandas ingestion]
    B --> C[Schema catalog]
    C --> D[GPT-OSS SQL planning]
    D --> E[SQL guardrails]
    E --> F[DuckDB execution]
    F --> G[Deterministic insights]
    G --> H[Streamlit interface]