-- Baseline: prove migrations run end to end (Flyway applies this from the api;
-- the worker reads schema_version back). The v2 schema (DESIGN §7) arrives
-- with the web path in week 4.

CREATE TABLE app_meta (
    key        text PRIMARY KEY,
    value      text NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now()
);

INSERT INTO app_meta (key, value) VALUES ('schema_version', 'baseline');
