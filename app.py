"""Streamlit dashboard for the continuous-aggregate challenge."""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import psycopg
import streamlit as st

from seed_data import generate_rows


st.set_page_config(page_title="Edge Fleet Telemetry", page_icon="⚡", layout="wide")


def db_url() -> str | None:
    return os.getenv("TIMESCALE_SERVICE_URL")


def demo_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.DataFrame(
        generate_rows(count=5_000),
        columns=["time", "device_id", "cpu_usage", "memory_usage", "temperature", "power_watts"],
    )
    raw["time"] = pd.to_datetime(raw["time"], utc=True)
    hourly = (
        raw.set_index("time")
        .groupby([pd.Grouper(freq="1h"), "device_id"])
        .agg(
            avg_cpu=("cpu_usage", "mean"),
            avg_memory=("memory_usage", "mean"),
            avg_temperature=("temperature", "mean"),
            total_power=("power_watts", "sum"),
            sample_count=("power_watts", "count"),
        )
        .reset_index()
        .rename(columns={"time": "bucket"})
    )
    return raw, hourly


def query_data(url: str, device: str) -> tuple[pd.DataFrame, pd.DataFrame, float]:
    with psycopg.connect(url) as connection:
        raw = pd.read_sql(
            """
            SELECT time, device_id, cpu_usage, memory_usage, temperature, power_watts
            FROM device_metrics
            WHERE device_id = %s AND time >= now() - INTERVAL '30 days'
            ORDER BY time
            """,
            connection,
            params=(device,),
        )
        hourly = pd.read_sql(
            """
            SELECT bucket, device_id, avg_cpu, avg_memory, avg_temperature,
                   total_power, sample_count
            FROM device_metrics_hourly
            WHERE device_id = %s AND bucket >= now() - INTERVAL '30 days'
            ORDER BY bucket
            """,
            connection,
            params=(device,),
        )
        before = datetime.now(timezone.utc)
        with connection.cursor() as cursor:
            cursor.execute("CALL refresh_continuous_aggregate('device_metrics_hourly', NULL, NULL)")
        refresh_ms = (datetime.now(timezone.utc) - before).total_seconds() * 1000
    return raw, hourly, refresh_ms


def main() -> None:
    url = db_url()
    database_mode = url is not None
    if database_mode:
        with psycopg.connect(url) as connection, connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT device_id FROM device_metrics ORDER BY device_id")
            devices = [row[0] for row in cursor.fetchall()]
        if not devices:
            st.error("The database has no telemetry. Run `python seed_data.py --reset` first.")
            st.stop()
        device = st.sidebar.selectbox("Device", devices)
        raw, hourly, refresh_ms = query_data(url, device)
    else:
        raw, hourly = demo_frame()
        device = st.sidebar.selectbox("Device", sorted(raw.device_id.unique()))
        raw = raw[raw.device_id == device]
        hourly = hourly[hourly.device_id == device]
        refresh_ms = None

    st.title("⚡ Edge Fleet Telemetry")
    st.caption("TimescaleDB continuous aggregates for fast operational dashboards")
    if database_mode:
        st.success("Database mode: live hypertable + continuous aggregate")
        if st.sidebar.button("Refresh aggregate"):
            st.cache_data.clear()
            st.rerun()
    else:
        st.warning("Demo mode: connect TIMESCALE_SERVICE_URL to run the real CAGG benchmark.")

    latest = raw.iloc[-1] if not raw.empty else None
    cards = st.columns(4)
    if latest is not None:
        cards[0].metric("CPU", f"{latest['cpu_usage']:.1f}%")
        cards[1].metric("Memory", f"{latest['memory_usage']:.1f}%")
        cards[2].metric("Temperature", f"{latest['temperature']:.1f} °C")
        cards[3].metric("Power", f"{latest['power_watts']:.1f} W")

    chart_data = hourly.copy()
    chart_data["bucket"] = pd.to_datetime(chart_data["bucket"], utc=True)
    st.subheader("Hourly performance (continuous aggregate)")
    st.plotly_chart(
        px.line(
            chart_data,
            x="bucket",
            y=["avg_cpu", "avg_memory"],
            labels={"value": "Percent", "variable": "Metric", "bucket": "Hour"},
        ),
        use_container_width=True,
    )
    left, right = st.columns(2)
    left.metric("Samples represented", f"{int(chart_data.sample_count.sum()):,}")
    right.metric("CAGG refresh time", f"{refresh_ms:.1f} ms" if refresh_ms is not None else "N/A (demo)")
    st.subheader("Why this is faster")
    st.markdown(
        "The raw hypertable stores every telemetry point. The dashboard reads "
        "`device_metrics_hourly`, where TimescaleDB has already materialized one row "
        "per device per hour in the background."
    )


if __name__ == "__main__":
    main()
