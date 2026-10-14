"""Create the challenge schema and load deterministic fleet telemetry."""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import psycopg


ROOT = Path(__file__).resolve().parent


def connection_url() -> str:
    url = os.getenv("TIMESCALE_SERVICE_URL")
    if not url:
        raise RuntimeError(
            "TIMESCALE_SERVICE_URL is not set. See README.md for local and Tiger Cloud examples."
        )
    return url


def generate_rows(
    count: int = 100_000,
    device_count: int = 5,
    seed: int = 7,
) -> list[tuple[datetime, str, float, float, float, float]]:
    """Generate repeatable, realistic-looking device metrics."""
    rng = np.random.default_rng(seed)
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    devices = [f"edge-{index:02d}" for index in range(1, device_count + 1)]
    rows = []
    for index in range(count):
        timestamp = start - timedelta(seconds=(count - index) * 30)
        device_index = index % device_count
        phase = index / 240
        cpu = float(np.clip(52 + 20 * np.sin(phase) + rng.normal(0, 7), 0, 100))
        memory = float(np.clip(58 + 12 * np.cos(phase / 2) + rng.normal(0, 4), 0, 100))
        temperature = float(42 + cpu * 0.18 + rng.normal(0, 2))
        power = float(np.clip(48 + cpu * 0.35 + rng.normal(0, 3), 1, None))
        rows.append((timestamp, devices[device_index], cpu, memory, temperature, power))
    return rows


def main(reset: bool) -> None:
    with psycopg.connect(connection_url()) as connection:
        with connection.cursor() as cursor:
            if reset:
                cursor.execute("DROP MATERIALIZED VIEW IF EXISTS device_metrics_hourly CASCADE")
                cursor.execute("DROP TABLE IF EXISTS device_metrics CASCADE")
            cursor.execute((ROOT / "setup_cagg.sql").read_text(encoding="utf-8"))
            rows = generate_rows()
            with cursor.copy(
                "COPY device_metrics (time, device_id, cpu_usage, memory_usage, temperature, power_watts) FROM STDIN"
            ) as copy:
                for row in rows:
                    copy.write_row(row)
            cursor.execute(
                "CALL refresh_continuous_aggregate('device_metrics_hourly', NULL, NULL)"
            )
    print(f"Loaded {len(rows):,} telemetry rows and refreshed device_metrics_hourly.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Recreate the schema before loading data.")
    main(parser.parse_args().reset)
