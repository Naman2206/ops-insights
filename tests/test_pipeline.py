import sqlite3, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from config import DB_PATH


def q(sql):
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(sql).fetchone()[0]


def test_no_duplicate_orders():
    assert q("SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM fact_operations") == 0


def test_no_negative_or_extreme_cycle_times():
    assert q("SELECT COUNT(*) FROM fact_operations WHERE cycle_hours < 0 OR cycle_hours > 72") == 0


def test_completed_orders_have_timestamp():
    assert q("SELECT COUNT(*) FROM fact_operations WHERE status='Completed' AND completed_at IS NULL") == 0


def test_canonical_centers_only():
    assert q("SELECT COUNT(DISTINCT center) FROM fact_operations") == 4


def test_kpi_view_reconciles_with_fact():
    assert q("SELECT SUM(orders_created) FROM vw_daily_kpis") == q("SELECT COUNT(*) FROM fact_operations")
