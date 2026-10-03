-- Single source of truth for KPI definitions. Tableau / Power BI / Python all read this view.
-- Additive counts are stored; ratios (error rate, SLA breach rate) are derived from SUMs
-- downstream so they re-aggregate correctly at any grain.
--   Throughput  = orders_completed (and units_completed)
--   Cycle time  = avg_cycle_hours  (completed orders only)
--   Error rate  = error_orders / orders_completed
DROP VIEW IF EXISTS vw_daily_kpis;
CREATE VIEW vw_daily_kpis AS
SELECT
    order_date,
    center,
    process_type,
    COUNT(*)                                                              AS orders_created,
    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END)                 AS orders_completed,
    SUM(CASE WHEN status = 'Completed' THEN units ELSE 0 END)             AS units_completed,
    SUM(CASE WHEN status = 'Completed' THEN cycle_hours ELSE 0 END)       AS cycle_hours_sum,
    ROUND(AVG(CASE WHEN status = 'Completed' THEN cycle_hours END), 3)    AS avg_cycle_hours,
    SUM(CASE WHEN status = 'Completed' AND error_flag = 1 THEN 1 ELSE 0 END) AS error_orders,
    SUM(CASE WHEN status = 'Completed' AND sla_breach = 1 THEN 1 ELSE 0 END) AS sla_breaches
FROM fact_operations
GROUP BY order_date, center, process_type;
