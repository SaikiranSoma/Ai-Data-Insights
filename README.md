AI Data Insights

AI Data Insights is a domain-independent web application that lets users upload one or more CSV or Excel files, ask analytical questions in plain English, and receive calculated answers, SQL transparency, KPI summaries, and interactive visualizations.

The language model interprets the question and generates a structured SQL plan. DuckDB, not the language model, performs the calculations against the uploaded data.

Replace the placeholder links below after deployment.

Live application: Open AI Data Insights

Demo video: Watch the demo

Source repository: GitHub repository

Features

Upload multiple CSV, XLSX, or XLS files in one session

Load each CSV and Excel sheet as a separate analytical table

Inspect table schemas, data types, missing values, unique values, and sample rows

Ask questions using plain English

Generate DuckDB-compatible SQL using the open-weight GPT-OSS 20B model

Run aggregations, filters, comparisons, rankings, trends, and cross-file joins

Display generated SQL for transparency

Show deterministic summaries and KPI cards from actual query results

Automatically select bar, line, pie, scatter, or histogram visualizations

Download analysis results as CSV

Reject destructive and multi-statement SQL

Disable external database and file access

Apply query timeouts and result limits

Attempt one controlled SQL repair when generated SQL fails

Record session-level execution history and user feedback

Avoid permanent storage of uploaded data

Architecture

flowchart TD
    A[CSV and Excel uploads] --> B[Pandas ingestion]
    B --> C[Schema catalog and profiling]
    C --> D[GPT-OSS SQL planning]
    D --> E[Read-only SQL guardrails]
    E --> F[DuckDB execution]
    F --> G[Deterministic summaries and charts]
    G --> H[Streamlit user interface]

Request flow

The user uploads CSV or Excel files.

Pandas loads the files into DataFrames.

Each DataFrame is registered as an in-memory DuckDB table.

The application builds a compact schema description.

GPT-OSS 20B converts the question into a structured SQL plan.

The application validates the plan and rejects unsafe SQL.

DuckDB executes the query and calculates the result.

Deterministic application logic generates the summary, KPIs, chart, and downloadable result.

Why this architecture?

The model is used for language understanding, not arithmetic. Totals, averages, filters, rankings, joins, and trends are calculated by DuckDB. This reduces numerical hallucination and makes every result traceable to visible SQL.

The application sends compact schema metadata to the model instead of entire uploaded datasets. Sensitive-looking sample columns are redacted before prompt construction.

Technology stack

Component

Technology

Purpose

Web interface

Streamlit

Uploads, controls, results, and deployment

Data processing

Pandas

CSV and Excel loading and profiling

Analytical engine

DuckDB

SQL execution and cross-file analysis

AI model

GPT-OSS 20B

Natural-language to SQL planning

Model hosting

Groq

Hosted inference for the open-weight model

Visualizations

Plotly

Interactive charts

Testing

Pytest

Guardrail and data-layer tests

Runtime

Python 3.11

Application environment

Why GPT-OSS 20B?

GPT-OSS 20B is an open-weight reasoning model distributed under the Apache 2.0 license. It supports structured JSON output and is suitable for SQL generation. The smaller 20B variant offers a practical balance of reasoning quality, latency, and hosted inference cost for a prototype.

The model does not directly access DuckDB, local files, or external systems. It only returns a proposed SQL plan, which is validated by application code before execution.

Repository structure

Ai-Data-Insights/
|
|-- app.py
|-- requirements.txt
|-- requirements-dev.txt
|-- README.md
|-- .gitignore
|
|-- .streamlit/
|   |-- config.toml
|   `-- secrets.toml          # Local only, never commit
|
|-- src/
|   |-- __init__.py
|   |-- ingestion.py
|   |-- data_workspace.py
|   |-- ai_sql.py
|   |-- analysis_service.py
|   `-- insights.py
|
|-- tests/
|   |-- test_ingestion.py
|   `-- test_query_guardrails.py
|
`-- docs/
    |-- approach.md
    `-- evaluation.md

Prerequisites

Python 3.11

Git

A Groq API key

A GitHub account for deployment

Local installation on Windows

1. Clone the repository

git clone https://github.com/YOUR_GITHUB_USERNAME/Ai-Data-Insights.git
cd Ai-Data-Insights

2. Create the virtual environment

py -3.11 -m venv .venv

3. Activate it

Command Prompt:

.venv\Scripts\activate.bat

PowerShell:

.\.venv\Scripts\Activate.ps1

Verify that the project interpreter is active:

python --version
where python

The first Python path should point to .venv\Scripts\python.exe.

4. Install dependencies

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

5. Configure the API key

Create .streamlit/secrets.toml:

GROQ_API_KEY = "your-groq-api-key"

Never place the key directly in Python code. Never commit secrets.toml.

6. Run the application

python -m streamlit run app.py

Open http://localhost:8501 if the browser does not open automatically.

Local installation on macOS or Linux

git clone https://github.com/YOUR_GITHUB_USERNAME/Ai-Data-Insights.git
cd Ai-Data-Insights
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
mkdir -p .streamlit

Create .streamlit/secrets.toml, add the Groq key, and run:

python -m streamlit run app.py

Required dependencies

requirements.txt should contain the tested versions of these direct dependencies:

streamlit
pandas
duckdb
openpyxl
xlrd
groq
plotly

Use the versions installed in the working local environment before deployment.

How to use the application

Upload one or more CSV, XLSX, or XLS files.

Click Process files.

Review the generated data catalog.

Inspect table previews, column profiles, and statistics.

Ask an analytical question in plain English.

Review the AI interpretation and generated SQL.

Inspect the answer, KPI cards, visualization, and result table.

Download the result if required.

Example questions

Single-table analysis

How many records are in the orders table?

What is the average order amount?

Show total sales by region from highest to lowest.

Which five products generated the highest sales?

Show monthly sales totals as a trend.

Show orders above 10,000.

Cross-file analysis

Join customers and orders and show total order amount by customer.

Which customer states generated the highest total item sales?

Show the top ten product categories by total sales.

Compare average payment value across customer regions.

Cross-file analysis requires a meaningful shared key such as customer_id, order_id, product_id, date, location, or product code. The application should request clarification when a relationship or metric is ambiguous.

Supported analysis

Counts and distinct counts

Totals and averages

Minimum and maximum values

Filters and conditional analysis

Grouped aggregations

Sorting and top-N ranking

Time-based trends

Cross-table joins

Category comparisons

Numeric distributions

Visualization rules

Charts are selected by deterministic application logic:

Result structure

Output

One-row result

KPI cards

Date and numeric value

Line chart

Category and numeric value

Bar chart

Proportion or contribution question

Pie chart when suitable

Two numeric measures and relationship question

Scatter chart

Numeric distribution question

Histogram

No reliable visual mapping

Result table only

All chart values come from DuckDB query results. The model does not generate chart data.

Security and reliability

The application adds the following controls around AI-generated SQL:

Only SELECT and WITH queries are accepted

Multiple SQL statements are rejected

Destructive operations are blocked

External database and local file access are disabled

Queries are checked by DuckDB before execution

Execution is interrupted after the configured timeout

Results are limited to 1,000 rows

Unknown tables returned by the model are rejected

Failed SQL receives only one controlled repair attempt

Ambiguous questions request clarification

Generated SQL remains visible for auditing

Uploaded data is not permanently stored by the application

Data privacy

Uploaded files are processed in the active Streamlit session.

Complete uploaded datasets are not included in model prompts.

The model receives table names, column metadata, statistics, and limited sample values.

Columns that appear sensitive are redacted from prompt samples.

Users should still avoid uploading confidential or regulated data to a public demonstration deployment.

Testing

Install development dependencies:

python -m pip install -r requirements-dev.txt

Run the test suite:

python -m pytest -v

The tests cover areas such as:

Valid read-only queries

Aggregation correctness

Destructive SQL rejection

Multiple-statement rejection

Unknown table handling

External file-access rejection

Result limiting

File-ingestion behavior

Manual AI evaluation results should be recorded in docs/evaluation.md.

Recommended test data

For a full demonstration, use a small selection from the Olist Brazilian E-Commerce dataset:

Orders

Order items

Customers

Products

Payments

Product category translation

This validates multi-file upload, joins, grouping, trends, rankings, and visualizations. Keep individual files below the configured 25 MB upload limit.

Deploy to Streamlit Community Cloud

1. Prepare the repository

Confirm that tests pass and secrets are ignored:

python -m pytest -v
git check-ignore .streamlit/secrets.toml
git status

The following command must return no tracked secrets file:

git ls-files .streamlit/secrets.toml

If a key was ever committed, revoke it in Groq Console and create a new key.

2. Commit and push

git add .
git commit -m "Prepare AI Data Insights for deployment"
git push origin main

If the repository uses another branch, replace main with the result of:

git branch --show-current

3. Create the cloud application

Open Streamlit Community Cloud.

Sign in with the GitHub account that owns or can access the repository.

Click Create app.

Select the repository and deployment branch.

Set the entrypoint to app.py.

Open Advanced settings.

Select Python 3.11 to match local development.

Add the production secret:

GROQ_API_KEY = "your-production-groq-api-key"

Click Deploy.

4. Verify the deployment

After deployment:

Open the public URL in an incognito window.

Upload a small CSV and verify basic analysis.

Upload related CSV files and verify a cross-file join.

Confirm that SQL, summaries, charts, and downloads work.

Confirm that destructive SQL requests are rejected.

Confirm that no secret is visible in the interface or logs.

5. Update the links

Replace these placeholders in this README:

YOUR_STREAMLIT_APP_URL

YOUR_DEMO_VIDEO_URL

YOUR_GITHUB_USERNAME

Then commit and push again:

git add README.md
git commit -m "Add deployment and demo links"
git push origin main

Streamlit Community Cloud will redeploy from the updated branch.

Deployment troubleshooting

ModuleNotFoundError

Add the missing direct dependency to requirements.txt, commit, and push again.

API key not found

Open the deployed app settings and confirm that the secret is exactly:

GROQ_API_KEY = "your-key"

Do not upload the local secrets.toml file.

App works locally but fails in the cloud

Confirm that Python 3.11 is selected.

Confirm that filenames and import capitalization match exactly.

Confirm that src/__init__.py exists.

Confirm that every direct dependency is in requirements.txt.

Review the Streamlit deployment logs for the first traceback.

Excel upload fails

Confirm that openpyxl is installed for XLSX files.

Confirm that xlrd is installed for legacy XLS files.

Test with a smaller workbook.

Groq rate-limit error

Wait for the provider limit to reset, reduce repeated calls, or configure a different inference plan. The application should present a readable error instead of crashing.

Query returns incorrect results

Review the generated SQL.

Confirm the table and column names.

Check whether the question used an ambiguous metric such as “best” or “revenue.”

Run the SQL through the developer SQL section.

Compare the result with a manual calculation.

Current limitations

The prototype is designed for small and medium tabular files, not data-lake scale workloads.

Join relationships are inferred from available schema information.

Uploaded files and analysis history are session-based.

The hosted AI model requires an internet connection and provider availability.

Public deployments share the configured provider quota.

Password-protected and heavily formatted Excel files may not load correctly.

The application does not provide authentication or persistent user workspaces.

Future improvements

User-confirmed table relationships

Semantic definitions for business metrics

Persistent authenticated workspaces

Object storage for larger files

Parquet support

Background processing for long-running analysis

Model-provider fallback

Saved dashboards and conversations

Centralized monitoring and structured logs

Larger automated text-to-SQL evaluation suite

Role-based access control and audit storage

Deliverables

Hosted Streamlit application

GitHub repository containing complete source code

README with setup and architecture documentation

docs/approach.md containing the one-page design write-up

docs/evaluation.md containing manual evaluation results

Short demonstration recording

License

No license is granted unless a license file is added to the repository. If the repository will be public and reusable, choose an appropriate open-source license before submission.

Author

Saikiran Soma

