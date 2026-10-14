CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS device_metrics (
    time TIMESTAMPTZ NOT NULL,
    device_id TEXT NOT NULL,
    cpu_usage DOUBLE PRECISION NOT NULL CHECK (cpu_usage BETWEEN 0 AND 100),
    memory_usage DOUBLE PRECISION NOT NULL CHECK (memory_usage BETWEEN 0 AND 100),
    temperature DOUBLE PRECISION NOT NULL,
    power_watts DOUBLE PRECISION NOT NULL CHECK (power_watts >= 0)
);

SELECT create_hypertable(
    'device_metrics',
    by_range('time', INTERVAL '1 day'),
    if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS device_metrics_device_time_idx
    ON device_metrics (device_id, time DESC);

DROP MATERIALIZED VIEW IF EXISTS device_metrics_hourly CASCADE;

CREATE MATERIALIZED VIEW device_metrics_hourly
WITH (timescaledb.continuous) AS
SELECT
    time_bucket(INTERVAL '1 hour', time) AS bucket,
    device_id,
    AVG(cpu_usage) AS avg_cpu,
    MAX(cpu_usage) AS max_cpu,
    AVG(memory_usage) AS avg_memory,
    AVG(temperature) AS avg_temperature,
    MAX(temperature) AS max_temperature,
    AVG(power_watts) AS avg_power,
    SUM(power_watts) AS total_power,
    COUNT(*) AS sample_count
FROM device_metrics
GROUP BY bucket, device_id
WITH NO DATA;

CREATE INDEX IF NOT EXISTS device_metrics_hourly_device_bucket_idx
    ON device_metrics_hourly (device_id, bucket DESC);

SELECT add_continuous_aggregate_policy(
    'device_metrics_hourly',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '5 minutes'
);
