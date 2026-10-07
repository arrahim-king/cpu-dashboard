# CPU Utilization Dashboard

A local Streamlit app: upload a CSV (`date`, `time`, `cpu_utilization`) and get a dark, dashboard-style time-series chart.

## Setup (macOS, Apple Silicon)

```bash
mkdir cpu-dashboard && cd cpu-dashboard
# put app.py, requirements.txt, sample_cpu.csv and .streamlit/config.toml here

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

streamlit run app.py
```

The app opens at http://localhost:8501. Upload `sample_cpu.csv`, or tick **Use demo data**.

## CSV format

```csv
date,time,cpu_utilization
2026-10-06,10:00:01,42.5
2026-10-06,10:00:05,47.2
```

- Column names are case-insensitive; common aliases (`cpu`, `cpu_usage`, ...) are accepted.
- Values like `42.5%` are fine. Unparseable rows are skipped with a warning.

## Features

- Date + time combined into one datetime axis
- Time-range slider, moving-average smoothing, chart height, Y-axis zoom, optional markers
- Hover tooltip with exact timestamp and value, summary metrics, data preview
- Large files are automatically bucket-averaged to ~6,000 points
