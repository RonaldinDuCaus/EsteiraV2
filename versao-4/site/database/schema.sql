CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE components (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    category VARCHAR(100),
    code VARCHAR(100),
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE component_images (
    id BIGSERIAL PRIMARY KEY,
    component_id BIGINT NOT NULL REFERENCES components(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    original_name TEXT,
    content_type VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE recognition_events (
    id BIGSERIAL PRIMARY KEY,
    component_id BIGINT REFERENCES components(id) ON DELETE SET NULL,
    detected_name VARCHAR(160),
    confidence NUMERIC(5,4),
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    image_filename TEXT,
    device_id VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
