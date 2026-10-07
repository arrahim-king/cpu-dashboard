"""CPU Utilization Dashboard — Streamlit app.

Upload a CSV with date, time and CPU utilization % columns and get a dark,
dashboard-style time-series chart (green line, translucent area fill).

Run:  streamlit run app.py
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ----------------------------------------------------------------------------
# Page setup & theme
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="CPU Utilization Dashboard",
    page_icon="📈",
    layout="wide",
)

BG = "#1c1c1e"          # chart / app background (matches the screenshot)
GRID = "rgba(255,255,255,0.10)"
TEXT = "#d9d9de"
GREEN = "#74e374"       # bright line colour

st.markdown(
    f"""
    <style>
      .stApp {{ background-color: {BG}; }}
      [data-testid="stSidebar"] {{ background-color: #232326; }}
      [data-testid="stMetric"] {{
          background: #242427; border: 1px solid rgba(255,255,255,0.07);
          border-radius: 12px; padding: 14px 18px;
      }}
      [data-testid="stMetricLabel"] p {{ color: #9a9aa3; font-size: 0.8rem; }}
      [data-testid="stMetricValue"] {{ color: {GREEN}; }}
      .block-container {{ padding-top: 2rem; max-width: 1400px; }}
      h1, h2, h3, p, label, span {{ color: {TEXT}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------
# Data loading / validation
# ----------------------------------------------------------------------------
DATE_ALIASES = {"date", "day", "dt"}
TIME_ALIASES = {"time", "timestamp_time", "clock"}
CPU_ALIASES = {
    "cpu_utilization", "cpu_utilisation", "cpu", "cpu_util", "cpu_usage",
    "cpu_percent", "cpu_%", "cpu utilization", "cpu utilization %",
    "cpu_utilization_%", "utilization", "utilization_%", "value",
}


def _find_column(columns: list[str], aliases: set[str]) -> str | None:
    for col in columns:
        if col.strip().lower() in aliases:
            return col
    return None


@st.cache_data(show_spinner=False)
def parse_csv(raw: bytes) -> tuple[pd.DataFrame | None, list[str], list[str]]:
    """Return (dataframe, errors, warnings). dataframe has columns ts, cpu."""
    errors: list[str] = []
    warnings: list[str] = []

    try:
        df = pd.read_csv(io.BytesIO(raw), skipinitialspace=True)
    except Exception as exc:  # noqa: BLE001
        return None, [f"Could not read the file as CSV: {exc}"], warnings

    if df.empty:
        return None, ["The CSV file has no data rows."], warnings

    cols = list(df.columns)
    date_col = _find_column(cols, DATE_ALIASES)
    time_col = _find_column(cols, TIME_ALIASES)
    cpu_col = _find_column(cols, CPU_ALIASES)

    missing = [
        name
        for name, col in (("date", date_col), ("time", time_col), ("cpu_utilization", cpu_col))
        if col is None
    ]
    if missing:
        return (
            None,
            [
                f"Missing required column(s): {', '.join(missing)}. "
                f"Found columns: {', '.join(map(str, cols))}. "
                "Expected headers: date, time, cpu_utilization."
            ],
            warnings,
        )

    total = len(df)
    ts = pd.to_datetime(
        df[date_col].astype(str).str.strip() + " " + df[time_col].astype(str).str.strip(),
        errors="coerce",
    )
    cpu = pd.to_numeric(
        df[cpu_col].astype(str).str.replace("%", "", regex=False).str.strip(),
        errors="coerce",
    )

    out = pd.DataFrame({"ts": ts, "cpu": cpu})
    bad_ts = int(out["ts"].isna().sum())
    bad_cpu = int(out["cpu"].isna().sum())
    out = out.dropna()

    if bad_ts:
        warnings.append(f"{bad_ts} row(s) skipped: date/time could not be parsed.")
    if bad_cpu:
        warnings.append(f"{bad_cpu} row(s) skipped: CPU value is not numeric.")
    if out.empty:
        return None, ["No valid rows remain after parsing date, time and CPU values."], warnings

    out_of_range = int(((out["cpu"] < 0) | (out["cpu"] > 100)).sum())
    if out_of_range:
        warnings.append(f"{out_of_range} row(s) have CPU values outside 0–100%.")

    dupes = int(out["ts"].duplicated().sum())
    if dupes:
        warnings.append(f"{dupes} duplicate timestamp(s) found; values were averaged.")
        out = out.groupby("ts", as_index=False)["cpu"].mean()

    out = out.sort_values("ts").reset_index(drop=True)
    if len(out) < total - bad_ts - bad_cpu:
        pass
    return out, errors, warnings


def demo_data() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    ts = pd.date_range("2026-10-06 09:30:00", "2026-10-06 15:45:00", freq="30s")
    n = len(ts)
    base = 42 + 14 * np.sin(np.linspace(0, 6.5, n)) + np.cumsum(rng.normal(0, 0.6, n)) * 0.25
    cpu = np.clip(base + rng.normal(0, 1.6, n), 1, 99)
    return pd.DataFrame({"ts": ts, "cpu": cpu})


def downsample(df: pd.DataFrame, max_points: int) -> pd.DataFrame:
    """Bucket-average to keep the chart snappy on very large files."""
    if len(df) <= max_points:
        return df
    bucket = int(np.ceil(len(df) / max_points))
    grp = np.arange(len(df)) // bucket
    return df.groupby(grp).agg(ts=("ts", "mean"), cpu=("cpu", "mean")).reset_index(drop=True)


# ----------------------------------------------------------------------------
# Sidebar: upload
# ----------------------------------------------------------------------------
st.title("CPU Utilization")
st.caption("Upload a CSV with `date`, `time` and `cpu_utilization` columns.")

with st.sidebar:
    st.header("Data")
    upload = st.file_uploader("CSV file", type=["csv"])
    use_demo = st.checkbox("Use demo data", value=False, help="Generate sample data to try the dashboard.")

if upload is not None:
    data, errs, warns = parse_csv(upload.getvalue())
    for e in errs:
        st.error(e)
    if data is None:
        st.stop()
    for w in warns:
        st.warning(w)
elif use_demo:
    data = demo_data()
else:
    st.info("Upload a CSV in the sidebar to get started, or tick **Use demo data**.")
    st.code(
        "date,time,cpu_utilization\n"
        "2026-10-06,10:00:01,42.5\n"
        "2026-10-06,10:00:05,47.2\n"
        "2026-10-06,10:00:10,51.8",
        language="csv",
    )
    st.stop()

# ----------------------------------------------------------------------------
# Sidebar: controls
# ----------------------------------------------------------------------------
t_min = data["ts"].min().to_pydatetime()
t_max = data["ts"].max().to_pydatetime()

with st.sidebar:
    st.header("Filters")
    if t_min < t_max:
        start, end = st.slider(
            "Time range",
            min_value=t_min,
            max_value=t_max,
            value=(t_min, t_max),
            format="YYYY-MM-DD HH:mm:ss",
        )
    else:
        start, end = t_min, t_max
        st.caption("Only one timestamp in the data.")

    st.header("Display")
    smoothing = st.slider(
        "Smoothing (moving average, points)", 1, 60, 1,
        help="1 = raw data. Higher values smooth the line.",
    )
    height = st.slider("Chart height (px)", 300, 900, 480, step=20)
    zoom_y = st.checkbox("Zoom Y-axis to data", value=True,
                         help="Off = fixed 0–100% scale.")
    show_markers = st.checkbox("Show data points", value=False)

view = data[(data["ts"] >= start) & (data["ts"] <= end)].copy()
if view.empty:
    st.warning("No data in the selected range.")
    st.stop()

if smoothing > 1:
    view["cpu"] = view["cpu"].rolling(smoothing, min_periods=1, center=True).mean()

view = downsample(view, 6000)

# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Latest", f"{view['cpu'].iloc[-1]:.1f}%")
m2.metric("Average", f"{view['cpu'].mean():.1f}%")
m3.metric("Peak", f"{view['cpu'].max():.1f}%")
m4.metric("Minimum", f"{view['cpu'].min():.1f}%")

# ----------------------------------------------------------------------------
# Chart
# ----------------------------------------------------------------------------
fig = go.Figure()

trace_kwargs = dict(
    x=view["ts"],
    y=view["cpu"],
    mode="lines+markers" if show_markers else "lines",
    line=dict(color=GREEN, width=2, shape="linear"),
    marker=dict(size=4, color=GREEN),
    fill="tozeroy",
    hovertemplate="<b>%{y:.1f}%</b><extra></extra>",
    name="CPU",
)
try:
    # Vertical gradient fill (Plotly >= 5.24): faint at the bottom, richer at the line.
    fig.add_trace(
        go.Scatter(
            **trace_kwargs,
            fillgradient=dict(
                type="vertical",
                colorscale=[
                    [0.0, "rgba(116,227,116,0.02)"],
                    [1.0, "rgba(116,227,116,0.42)"],
                ],
            ),
        )
    )
except Exception:  # noqa: BLE001 - older Plotly: flat translucent fill
    fig.data = ()
    fig.add_trace(go.Scatter(**trace_kwargs, fillcolor="rgba(116,227,116,0.18)"))

ymin, ymax = float(view["cpu"].min()), float(view["cpu"].max())
if zoom_y and ymax > ymin:
    pad = (ymax - ymin) * 0.12
    y_range = [max(0, ymin - pad), min(100, ymax + pad) if ymax + pad <= 100 else ymax + pad]
elif zoom_y:
    y_range = [max(0, ymin - 5), ymin + 5]
else:
    y_range = [0, 100]

fig.update_layout(
    height=height,
    margin=dict(l=8, r=8, t=16, b=8),
    paper_bgcolor=BG,
    plot_bgcolor=BG,
    font=dict(color=TEXT, size=13),
    showlegend=False,
    hovermode="x unified",
    hoverlabel=dict(bgcolor="#2c2c30", bordercolor="rgba(255,255,255,0.15)",
                    font=dict(color="#ffffff", size=13)),
    xaxis=dict(
        showgrid=True, gridcolor=GRID, gridwidth=1,
        showline=True, linecolor="rgba(255,255,255,0.25)",
        tickfont=dict(color="#c8c8ce", size=13),
        zeroline=False,
        hoverformat="%b %d, %Y  %H:%M:%S",
        spikemode="across", spikecolor="rgba(255,255,255,0.35)",
        spikethickness=1, spikedash="dot",
    ),
    yaxis=dict(
        side="right",
        range=y_range,
        showgrid=True, gridcolor=GRID, gridwidth=1,
        zeroline=False,
        ticksuffix="%",
        tickfont=dict(color="#e6e6ea", size=14),
        fixedrange=False,
    ),
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={"displaylogo": False, "responsive": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
)

with st.expander("Data preview"):
    st.dataframe(view.rename(columns={"ts": "timestamp", "cpu": "cpu_utilization_%"}),
                 use_container_width=True, hide_index=True)
    st.caption(f"{len(view):,} points shown · {start:%Y-%m-%d %H:%M:%S} → {end:%Y-%m-%d %H:%M:%S}")
