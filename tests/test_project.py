from datetime import datetime

from benchmark import parse_execution_ms
from seed_data import generate_rows


def test_seed_is_deterministic_and_valid():
    rows = generate_rows(count=10, device_count=2, seed=3)
    assert rows == generate_rows(count=10, device_count=2, seed=3)
    assert len(rows) == 10
    assert all(isinstance(row[0], datetime) for row in rows)
    assert {row[1] for row in rows} == {"edge-01", "edge-02"}
    assert all(0 <= row[2] <= 100 for row in rows)


def test_execution_time_parser():
    plan = [{"Plan": {"Node Type": "Aggregate"}, "Execution Time": 1.25}]
    assert parse_execution_ms(plan) == 1.25
