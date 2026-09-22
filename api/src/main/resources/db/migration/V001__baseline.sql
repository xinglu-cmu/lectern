-- Baseline: prove migrations run and pgvector is available.
-- Real schema (DESIGN §8) arrives in week-2 migrations.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE app_meta (
    key        text PRIMARY KEY,
    value      text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO app_meta (key, value) VALUES ('schema_version', 'baseline');
