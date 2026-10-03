-- Data quality checks run against stg_operations BEFORE cleaning.
-- Format:  -- name: <check> | severity: <error|warn> | desc: <text>
-- Each query must return a single numeric column `n` (count of offending rows).

-- name: duplicate_order_ids | severity: error | desc: order_id appears more than once
SELECT COUNT(*) AS n FROM (SELECT order_id FROM stg_operations GROUP BY order_id HAVING COUNT(*) > 1);

-- name: completed_missing_timestamp | severity: error | desc: status Completed but completed_at is null
SELECT COUNT(*) AS n FROM stg_operations WHERE status = 'Completed' AND completed_at IS NULL;

-- name: negative_cycle_time | severity: error | desc: completed_at earlier than created_at
SELECT COUNT(*) AS n FROM stg_operations WHERE completed_at < created_at;

-- name: extreme_cycle_time | severity: warn | desc: cycle time greater than 72 hours
SELECT COUNT(*) AS n FROM stg_operations
WHERE completed_at IS NOT NULL AND (julianday(completed_at) - julianday(created_at)) * 24 > 72;

-- name: null_units | severity: warn | desc: units missing
SELECT COUNT(*) AS n FROM stg_operations WHERE units IS NULL;

-- name: inconsistent_center_labels | severity: warn | desc: rows whose center label is not in canonical form
SELECT COUNT(*) AS n FROM stg_operations WHERE center NOT IN ('Mumbai','Pune','Delhi','Bengaluru');

-- name: null_created_at | severity: error | desc: created_at missing
SELECT COUNT(*) AS n FROM stg_operations WHERE created_at IS NULL;
