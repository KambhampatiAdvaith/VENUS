CREATE TABLE IF NOT EXISTS telemetry (
    id SERIAL PRIMARY KEY,
    substation VARCHAR(20) NOT NULL,
    voltage DOUBLE PRECISION NOT NULL,
    "current" DOUBLE PRECISION NOT NULL,
    temperature DOUBLE PRECISION NOT NULL,
    "load" DOUBLE PRECISION NOT NULL,
    frequency DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    edge_anomaly BOOLEAN DEFAULT FALSE,
    edge_anomaly_score DOUBLE PRECISION,
    edge_model VARCHAR(100),
    edge_processed_at TIMESTAMPTZ
);

ALTER TABLE telemetry
    ADD COLUMN IF NOT EXISTS edge_anomaly BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS edge_anomaly_score DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS edge_model VARCHAR(100),
    ADD COLUMN IF NOT EXISTS edge_processed_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS faults (
    id SERIAL PRIMARY KEY,
    substation VARCHAR(20) NOT NULL,
    fault_type VARCHAR(100) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id SERIAL PRIMARY KEY,
    message TEXT NOT NULL,
    severity VARCHAR(50) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    substation VARCHAR(50) NOT NULL,
    predicted_fault VARCHAR(100) NOT NULL,
    probability DOUBLE PRECISION NOT NULL,
    anomaly BOOLEAN NOT NULL DEFAULT FALSE,
    anomaly_score DOUBLE PRECISION NOT NULL DEFAULT 0,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS load_balancing_actions (
    id SERIAL PRIMARY KEY,
    source_node VARCHAR(20) NOT NULL,
    target_node VARCHAR(20) NOT NULL,
    load_shifted DOUBLE PRECISION NOT NULL,
    trigger_reason TEXT NOT NULL,
    action_status VARCHAR(50) NOT NULL,
    source_load_before DOUBLE PRECISION NOT NULL,
    source_load_after DOUBLE PRECISION NOT NULL,
    target_load_before DOUBLE PRECISION NOT NULL,
    target_load_after DOUBLE PRECISION NOT NULL,
    risk_before DOUBLE PRECISION NOT NULL,
    risk_after DOUBLE PRECISION NOT NULL,
    effectiveness VARCHAR(50) NOT NULL DEFAULT 'pending',
    execution_mode VARCHAR(50) NOT NULL,
    decision_notes TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_load_balancing_actions_created_at
    ON load_balancing_actions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_load_balancing_actions_action_status
    ON load_balancing_actions (action_status);

-- Legacy table retained for older code paths. Current backend routes write to
-- load_balancing_actions.
CREATE TABLE IF NOT EXISTS load_balancing (
    id SERIAL PRIMARY KEY,
    source_node VARCHAR(20) NOT NULL,
    target_node VARCHAR(20) NOT NULL,
    load_shifted DOUBLE PRECISION NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
