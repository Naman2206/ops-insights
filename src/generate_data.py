"""Generate a realistic, deliberately messy synthetic operations dataset from two source systems."""
import numpy as np
import pandas as pd
from config import RAW

SEED = 42
CENTERS = {"Mumbai": 0.35, "Pune": 0.20, "Delhi": 0.25, "Bengaluru": 0.20}
PROCESSES = {"Intake": 0.30, "Verification": 0.30, "Fulfillment": 0.30, "Support": 0.10}
BASE_CYCLE = {"Intake": 2.0, "Verification": 5.0, "Fulfillment": 14.0, "Support": 3.5}
DOW_FACTOR = [1.25, 1.10, 1.00, 1.00, 0.95, 0.60, 0.50]  # Mon..Sun
HOUR_P = np.array([2, 5, 9, 10, 10, 8, 8, 9, 9, 8, 6, 4, 2, 1], dtype=float)  # hours 7..20


def generate():
    rng = np.random.default_rng(SEED)
    dates = pd.date_range("2025-01-01", "2026-06-30")
    t = np.arange(len(dates))
    expected = (110 + 0.12 * t) * np.array([DOW_FACTOR[d.dayofweek] for d in dates])
    daily_n = rng.poisson(expected)
    load_ratio = pd.Series(daily_n / expected.mean(), index=dates)

    day_idx = np.repeat(np.arange(len(dates)), daily_n)
    n = len(day_idx)
    d = dates[day_idx]
    center = rng.choice(list(CENTERS), n, p=list(CENTERS.values()))
    process = rng.choice(list(PROCESSES), n, p=list(PROCESSES.values()))
    hour = rng.choice(np.arange(7, 21), n, p=HOUR_P / HOUR_P.sum())
    minute = rng.integers(0, 60, n)
    created = d + pd.to_timedelta(hour, "h") + pd.to_timedelta(minute, "m")

    lr = load_ratio.values[day_idx]
    mean = np.array([BASE_CYCLE[p] for p in process])
    mult = np.ones(n)
    mult[(center == "Delhi") & (process == "Verification")] = 1.6       # planted bottleneck
    mult[center == "Pune"] *= 0.9
    mult *= 1 + 0.35 * np.clip(lr - 1, 0, None)                         # slower on heavy days
    mult *= np.where(d.dayofweek == 0, 1.1, 1.0)                        # Monday backlog
    cycle = mean * mult * np.exp(rng.normal(-0.5 * 0.45**2, 0.45, n))

    p_err = 0.025 + 0.06 * np.clip(lr - 1, 0, None) + 0.02 * ((center == "Delhi") & (process == "Verification"))
    error = (rng.random(n) < p_err).astype(int)
    cancelled = rng.random(n) < 0.04
    error[cancelled] = 0
    units = rng.poisson(3, n) + 1
    completed = created + pd.to_timedelta(cycle, "h")

    df = pd.DataFrame({
        "order_id": [f"ORD-{i:07d}" for i in range(1, n + 1)],
        "center": center, "process_type": process, "created_at": created,
        "completed_at": completed, "status": np.where(cancelled, "Cancelled", "Completed"),
        "error_flag": error, "units": units.astype(float),
    })
    df.loc[cancelled, "completed_at"] = pd.NaT

    # ---- inject data quality problems ----
    comp = df.index[df.status == "Completed"]
    miss = rng.choice(comp, int(0.008 * len(comp)), replace=False)
    df.loc[miss, "completed_at"] = pd.NaT
    neg = rng.choice(comp.difference(miss), int(0.003 * len(comp)), replace=False)
    df.loc[neg, "completed_at"] = df.loc[neg, "created_at"] - pd.to_timedelta(rng.uniform(1, 6, len(neg)), "h")
    out = rng.choice(comp.difference(miss).difference(neg), int(0.001 * len(comp)), replace=False)
    df.loc[out, "completed_at"] = df.loc[out, "created_at"] + pd.to_timedelta(rng.uniform(100, 400, len(out)), "h")
    df.loc[rng.choice(n, int(0.005 * n), replace=False), "units"] = np.nan
    messy = rng.choice(n, int(0.05 * n), replace=False)
    variants = {"Mumbai": ["MUMBAI", " Mumbai "], "Pune": ["pune", "PUNE"],
                "Delhi": ["DELHI", " delhi"], "Bengaluru": ["Bangalore", "BENGALURU"]}
    df.loc[messy, "center"] = [rng.choice(variants[c]) for c in df.loc[messy, "center"]]

    df["source"] = rng.choice(["A", "B"], n, p=[0.6, 0.4])
    a, b = df[df.source == "A"].drop(columns="source"), df[df.source == "B"].drop(columns="source")
    a = pd.concat([a, a.sample(frac=0.01, random_state=1)])           # duplicate rows
    b = pd.concat([b, b.sample(frac=0.01, random_state=2)])

    iso = "%Y-%m-%dT%H:%M:%S"
    sys_a = a.assign(created_at=a.created_at.dt.strftime(iso), completed_at=a.completed_at.dt.strftime(iso))
    fmt_b = "%d/%m/%Y %H:%M"
    sys_b = pd.DataFrame({
        "OrderRef": b.order_id, "Site": b.center, "Process": b.process_type,
        "CreatedDate": b.created_at.dt.strftime(fmt_b), "ClosedDate": b.completed_at.dt.strftime(fmt_b),
        "State": np.where(b.status == "Completed", "DONE", "CANCELLED"),
        "HasError": np.where(b.error_flag == 1, "Y", "N"), "Qty": b.units,
    })

    # staffing roster (agents scheduled per center per day)
    share = pd.Series(CENTERS)
    rows = []
    for dt, nn in zip(dates, daily_n):
        for c, s in share.items():
            rows.append((dt.date().isoformat(), c, max(2, int(round(nn * s / 24 + rng.normal(0, 0.8))))))
    staffing = pd.DataFrame(rows, columns=["date", "center", "agents_scheduled"])

    RAW.mkdir(parents=True, exist_ok=True)
    sys_a.to_csv(RAW / "system_a_orders.csv", index=False)
    sys_b.to_csv(RAW / "system_b_orders.csv", index=False)
    staffing.to_csv(RAW / "staffing.csv", index=False)
    print(f"[generate] system_a={len(sys_a):,} system_b={len(sys_b):,} staffing={len(staffing):,}")


if __name__ == "__main__":
    generate()
