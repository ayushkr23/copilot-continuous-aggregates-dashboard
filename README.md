# Continuous Aggregates Dashboard

An end-to-end Global Hack Week project that demonstrates how TimescaleDB continuous
aggregates make time-series dashboards faster and cheaper to query.

The dashboard compares the same fleet-telemetry question in two ways:

1. an on-demand aggregation over the raw hypertable; and
2. a pre-computed hourly continuous aggregate maintained by TimescaleDB.

It also shows live device metrics, hourly trends, and the measured query-speed
difference. The app can run against Tiger Cloud or a local TimescaleDB container.
Without a database connection it starts in an explicit demo mode so the UI can be
reviewed, but demo mode does not claim to benchmark a continuous aggregate.

## Challenge deliverables

This repository implements the original “Accelerate Dashboards with Continuous
Aggregates” brief:

- a TimescaleDB hypertable containing high-frequency telemetry;
- an hourly continuous aggregate using `time_bucket`;
- an automatic refresh policy;
- reproducible sample data;
- a working interactive dashboard;
- a benchmark that measures raw-table aggregation versus the CAGG; and
- documentation showing setup, usage, and the expected screenshots.

## Project structure

| Path | Purpose |
| --- | --- |
| `app.py` | Streamlit dashboard and database/demo data access |
| `setup_cagg.sql` | Hypertable, continuous aggregate, indexes, and refresh policy |
| `seed_data.py` | Deterministic telemetry generator and database seeder |
| `benchmark.py` | `EXPLAIN ANALYZE` comparison of raw and CAGG queries |
| `requirements.txt` | Python dependencies |
| `docker-compose.yml` | Local TimescaleDB for reproducible development |

## Prerequisites

- Python 3.10 or newer
- Docker Desktop (for the local database option), or a Tiger Cloud TimescaleDB
  service
- PostgreSQL connection URI in `TIMESCALE_SERVICE_URL`

Tiger Cloud connection strings normally look like:

```text
postgresql://tsdbadmin:<password>@<host>:<port>/tsdb?sslmode=require
```

## Quick start with local TimescaleDB

1. Create the environment and install dependencies:

   ```powershell
   py -3 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

2. Start TimescaleDB:

   ```powershell
   docker compose up -d
   ```

3. Set the connection string for the current PowerShell session:

   ```powershell
   $env:TIMESCALE_SERVICE_URL = "postgresql://postgres:postgres@localhost:5432/telemetry"
   ```

4. Create the schema and continuous aggregate, then load 100,000 deterministic
   telemetry rows:

   ```powershell
   python seed_data.py --reset
   ```

5. Run the benchmark:

   ```powershell
   python benchmark.py
   ```

6. Launch the dashboard:

   ```powershell
   streamlit run app.py
   ```

The dashboard opens at `http://localhost:8501`. Use the sidebar to choose the
device and time range. The **Refresh aggregate** button invokes
`refresh_continuous_aggregate` so the demo is easy to repeat after adding data.

## Tiger Cloud setup

Skip `docker compose up -d`, set `TIMESCALE_SERVICE_URL` to the Tiger Cloud
connection URI, and run the same `seed_data.py --reset`, `benchmark.py`, and
`streamlit run app.py` commands. The SQL uses only TimescaleDB features available
on a standard Tiger Cloud service.

## Screenshots

The checked-in UI screenshot was captured from a running Streamlit process in
demo mode. It proves the dashboard renders, but it is not a database benchmark:

![Dashboard in demo mode](docs-dashboard-demo.png)

For a submission backed by Tiger Cloud or local TimescaleDB, capture the live
dashboard and benchmark output after running the commands above and replace this
image with those run-specific screenshots.

## Testing

The repository includes fast offline tests for deterministic seed generation and
benchmark parsing:

```powershell
python -m pytest
```

The database acceptance check is:

```powershell
python seed_data.py --reset
python benchmark.py
```

The benchmark prints both execution plans and a summary. Only a run that reports
`database_mode=true` proves the CAGG path; demo mode is deliberately labelled and
is not presented as a database performance result.

## License

MIT
