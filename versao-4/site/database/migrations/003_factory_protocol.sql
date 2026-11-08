-- Migração aditiva. Não remove tabelas, imagens nem registros anteriores.
CREATE TABLE IF NOT EXISTS factory_devices (
    id TEXT PRIMARY KEY,
    role TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    telemetry JSONB NOT NULL DEFAULT '{}'::jsonb,
    authorized BOOLEAN NOT NULL DEFAULT FALSE,
    last_ack_id UUID
);
CREATE TABLE IF NOT EXISTS factory_device_boots (
    device_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    retired_at TIMESTAMPTZ,
    PRIMARY KEY(device_id,boot_id)
);
CREATE TABLE IF NOT EXISTS factory_commands (
    id UUID PRIMARY KEY,
    device_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    action TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    expires_at TIMESTAMPTZ NOT NULL,
    ack_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_factory_command_device ON factory_commands(device_id, created_at DESC);
CREATE TABLE IF NOT EXISTS factory_cycles (
    id UUID PRIMARY KEY,
    device_id TEXT NOT NULL,
    boot_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    recognition_event_id BIGINT NOT NULL REFERENCES recognition_events(id),
    status TEXT NOT NULL DEFAULT 'awaiting_capture',
    reason TEXT,
    component_id BIGINT REFERENCES components(id) ON DELETE SET NULL,
    component_name TEXT,
    confidence DOUBLE PRECISION,
    image_filename TEXT,
    image_sha256 TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    deadline TIMESTAMPTZ NOT NULL,
    completed BOOLEAN NOT NULL DEFAULT FALSE,
    lease_token TEXT,
    camera_boot_id TEXT,
    lease_expires_at TIMESTAMPTZ,
    worker_token TEXT,
    UNIQUE(device_id, boot_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_factory_cycle_work ON factory_cycles(status, created_at);
CREATE TABLE IF NOT EXISTS factory_worker_health (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_seen TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp(),
    status TEXT NOT NULL,
    reason TEXT,
    model_path TEXT
);
