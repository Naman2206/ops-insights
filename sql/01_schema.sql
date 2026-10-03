-- Target warehouse schema (SQLite). stg_operations is created by src/clean.py (harmonize step).
DROP TABLE IF EXISTS dim_process;
CREATE TABLE dim_process (
    process_type TEXT PRIMARY KEY,
    sla_hours    REAL NOT NULL
);
INSERT INTO dim_process VALUES
 ('Intake', 4), ('Verification', 8), ('Fulfillment', 24), ('Support', 6);

DROP TABLE IF EXISTS fact_operations;
CREATE TABLE fact_operations (
    order_id      TEXT PRIMARY KEY,
    source_system TEXT NOT NULL,
    center        TEXT NOT NULL,
    process_type  TEXT NOT NULL REFERENCES dim_process(process_type),
    created_at    TEXT NOT NULL,
    completed_at  TEXT,
    order_date    TEXT NOT NULL,
    created_hour  INTEGER NOT NULL,
    weekday       TEXT NOT NULL,
    status        TEXT NOT NULL CHECK (status IN ('Completed','Cancelled')),
    error_flag    INTEGER NOT NULL CHECK (error_flag IN (0,1)),
    units         INTEGER NOT NULL,
    units_imputed INTEGER NOT NULL DEFAULT 0,
    cycle_hours   REAL,
    sla_hours     REAL NOT NULL,
    sla_breach    INTEGER NOT NULL DEFAULT 0
);

DROP TABLE IF EXISTS rejected_records;
CREATE TABLE rejected_records (
    order_id      TEXT,
    source_system TEXT,
    reject_reason TEXT NOT NULL
);
