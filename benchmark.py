"""Benchmark raw aggregation against the TimescaleDB continuous aggregate."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parent
QUERY = """
SELECT time_bucket(INTERVAL '1 hour', time) AS bucket,
       device_id,
       AVG(cpu_usage) AS avg_cpu,
       AVG(memory_usage) AS avg_memory,
       AVG(temperature) AS avg_temperature,
       SUM(power_watts) AS total_power,
       COUNT(*) AS sample_count
FROM device_metrics
GROUP BY bucket, device_id
ORDER BY bucket
"""
CAGG_QUERY = """
SELECT bucket, device_id, avg_cpu, avg_memory, avg_temperature,
       total_power, sample_count
FROM device_metrics_hourly
ORDER BY bucket
"""


def parse_execution_ms(plan: list[dict]) -> float:
    text = json.dumps(plan)
    match = re.search(r'"Execution Time":\s*([0-9.]+)', text)
    if not match:
        raise ValueError("EXPLAIN ANALYZE did not include an execution time.")
    return float(match.group(1))


def main() -> None:
    url = os.getenv("TIMESCALE_SERVICE_URL")
    if not url:
        raise RuntimeError("TIMESCALE_SERVICE_URL is not set.")
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        results = {}
        for name, query in (("raw hypertable", QUERY), ("continuous aggregate", CAGG_QUERY)):
            cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {query}")
            plan = cursor.fetchone()[0]
            results[name] = parse_execution_ms(plan)
            print(f"\n{name.title()} plan:")
            print(json.dumps(plan, indent=2))
        raw_ms = results["raw hypertable"]
        cagg_ms = results["continuous aggregate"]
        print("\nSummary")
        print(f"raw_ms={raw_ms:.3f}")
        print(f"cagg_ms={cagg_ms:.3f}")
        print(f"speedup={raw_ms / cagg_ms:.2f}x")
        print("database_mode=true")


if __name__ == "__main__":
    main()
