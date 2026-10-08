CREATE TABLE IF NOT EXISTS message_results (
    id BIGSERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    send_time DOUBLE PRECISION NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_message_results_success ON message_results (success);
