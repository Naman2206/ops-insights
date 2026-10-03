"""Load raw sources -> harmonized staging table -> cleaned fact table (+ rejects log)."""
import sqlite3
import numpy as np
import pandas as pd
from config import RAW, SQL, DB_PATH, CENTER_ALIASES, MAX_CYCLE_HOURS

TS = "%Y-%m-%d %H:%M:%S"


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def harmonize(con):
    """Unify the two source schemas. No rows are dropped here."""
    a = pd.read_csv(RAW / "system_a_orders.csv")
    a["source_system"] = "A"
    a["created_at"] = pd.to_datetime(a["created_at"], format="%Y-%m-%dT%H:%M:%S")
    a["completed_at"] = pd.to_datetime(a["completed_at"], format="%Y-%m-%dT%H:%M:%S")

    b = pd.read_csv(RAW / "system_b_orders.csv").rename(columns={
        "OrderRef": "order_id", "Site": "center", "Process": "process_type",
        "CreatedDate": "created_at", "ClosedDate": "completed_at",
        "State": "status", "HasError": "error_flag", "Qty": "units"})
    b["source_system"] = "B"
    b["created_at"] = pd.to_datetime(b["created_at"], format="%d/%m/%Y %H:%M")
    b["completed_at"] = pd.to_datetime(b["completed_at"], format="%d/%m/%Y %H:%M")
    b["status"] = b["status"].map({"DONE": "Completed", "CANCELLED": "Cancelled"})
    b["error_flag"] = (b["error_flag"] == "Y").astype(int)

    stg = pd.concat([a, b], ignore_index=True)
    for col in ("created_at", "completed_at"):
        stg[col] = stg[col].dt.strftime(TS).where(stg[col].notna(), None)
    stg.to_sql("stg_operations", con, if_exists="replace", index=False)
    pd.read_csv(RAW / "staffing.csv").to_sql("staffing", con, if_exists="replace", index=False)
    return len(stg)


def build_schema(con):
    con.executescript((SQL / "01_schema.sql").read_text())


def apply_rules(con):
    """Apply cleansing rules; returns a dict of {rule: rows_rejected/fixed}."""
    df = pd.read_sql("SELECT * FROM stg_operations", con, parse_dates=["created_at", "completed_at"])
    rejects, log = [], {}

    def reject(mask, reason):
        log[reason] = int(mask.sum())
        rejects.append(df.loc[mask, ["order_id", "source_system"]].assign(reject_reason=reason))
        return df[~mask].copy()

    # 1. standardize center labels (fix, not reject)
    canon = df["center"].str.strip().str.lower().map(CENTER_ALIASES)
    log["center_labels_standardized"] = int((df["center"] != canon).sum())
    df["center"] = canon
    df = reject(df["center"].isna(), "unknown_center")
    # 2. de-duplicate on order_id (keep first)
    df = reject(df.duplicated("order_id", keep="first"), "duplicate_order_id")
    # 3. completed orders must have a completion timestamp
    df = reject((df.status == "Completed") & df.completed_at.isna(), "completed_missing_timestamp")
    # 4. completion cannot precede creation
    df = reject(df.completed_at < df.created_at, "negative_cycle_time")
    # 5. implausible cycle times
    hrs = (df.completed_at - df.created_at).dt.total_seconds() / 3600
    df = reject(hrs > MAX_CYCLE_HOURS, f"cycle_time_over_{MAX_CYCLE_HOURS}h")
    # 6. impute missing units with the process median (fix, flagged)
    df["units_imputed"] = df["units"].isna().astype(int)
    log["units_imputed"] = int(df["units_imputed"].sum())
    df["units"] = df["units"].fillna(df.groupby("process_type")["units"].transform("median")).astype(int)

    sla = pd.read_sql("SELECT * FROM dim_process", con)
    df = df.merge(sla, on="process_type", how="left")
    df["cycle_hours"] = ((df.completed_at - df.created_at).dt.total_seconds() / 3600).round(3)
    df["sla_breach"] = ((df.cycle_hours > df.sla_hours) & (df.status == "Completed")).astype(int)
    df["order_date"] = df.created_at.dt.strftime("%Y-%m-%d")
    df["created_hour"] = df.created_at.dt.hour
    df["weekday"] = df.created_at.dt.day_name()
    for col in ("created_at", "completed_at"):
        df[col] = df[col].dt.strftime(TS).where(df[col].notna(), None)

    cols = ["order_id", "source_system", "center", "process_type", "created_at", "completed_at", "order_date",
            "created_hour", "weekday", "status", "error_flag", "units", "units_imputed", "cycle_hours",
            "sla_hours", "sla_breach"]
    df[cols].to_sql("fact_operations", con, if_exists="append", index=False)
    pd.concat(rejects).to_sql("rejected_records", con, if_exists="append", index=False)
    con.executescript((SQL / "03_kpi_views.sql").read_text())
    con.commit()
    log["_rows_out"] = len(df)
    return log
