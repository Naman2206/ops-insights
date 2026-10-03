"""KPI access layer: reads vw_daily_kpis (defined in sql/03_kpi_views.sql) and derives ratio metrics."""
import pandas as pd


def daily_kpis(con):
    df = pd.read_sql("SELECT * FROM vw_daily_kpis", con, parse_dates=["order_date"])
    return add_ratios(df)


def add_ratios(df):
    df = df.copy()
    df["error_rate"] = df["error_orders"] / df["orders_completed"]
    df["sla_breach_rate"] = df["sla_breaches"] / df["orders_completed"]
    df["avg_cycle_hours"] = df["cycle_hours_sum"] / df["orders_completed"]
    return df
