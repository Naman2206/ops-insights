"""Simple log-linear regression forecast of daily order volume + staffing translation."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from config import IMAGES, DOCS, TABLEAU, FORECAST_HORIZON_DAYS, HOLDOUT_DAYS


def features(dates, start):
    X = pd.DataFrame({"t": (dates - start).days}, index=dates)
    dow = pd.get_dummies(dates.dayofweek, prefix="dow").reindex(columns=[f"dow_{i}" for i in range(7)], fill_value=0)
    dow.index = dates
    return pd.concat([X, dow.iloc[:, 1:].astype(int)], axis=1)   # drop Monday as baseline


def mape(y, p):
    return float(np.mean(np.abs((y - p) / y)) * 100)


def run(con):
    f = pd.read_sql("SELECT order_date, COUNT(*) AS orders FROM fact_operations GROUP BY order_date", con,
                    parse_dates=["order_date"]).set_index("order_date")["orders"].asfreq("D")
    start = f.index[0]
    train, test = f.iloc[:-HOLDOUT_DAYS], f.iloc[-HOLDOUT_DAYS:]

    m = LinearRegression().fit(features(train.index, start), np.log(train))
    pred = pd.Series(np.exp(m.predict(features(test.index, start))), index=test.index)
    naive = f.shift(7).loc[test.index]                                   # same weekday last week
    metrics = {"model_mae": float(np.mean(np.abs(test - pred))), "model_mape": mape(test, pred),
               "naive_mae": float(np.mean(np.abs(test - naive))), "naive_mape": mape(test, naive)}

    final = LinearRegression().fit(features(f.index, start), np.log(f))
    resid_sd = float(np.std(np.log(f) - final.predict(features(f.index, start))))
    future = pd.date_range(f.index[-1] + pd.Timedelta(days=1), periods=FORECAST_HORIZON_DAYS)
    mu = final.predict(features(future, start))
    yhat, lo, hi = np.exp(mu), np.exp(mu - 1.96 * resid_sd), np.exp(mu + 1.96 * resid_sd)
    fc = pd.DataFrame({"date": future, "forecast_orders": yhat.round(0),
                       "lower_95": lo.round(0), "upper_95": hi.round(0)})

    # staffing translation: historical orders handled per scheduled agent per day
    staff = pd.read_sql("SELECT date, SUM(agents_scheduled) AS agents FROM staffing GROUP BY date", con,
                        parse_dates=["date"]).set_index("date")["agents"]
    productivity = float((f / staff).median())
    fc["agents_needed"] = np.ceil(fc.forecast_orders / productivity).astype(int)
    fc["agents_needed_peak"] = np.ceil(fc.upper_95 / productivity).astype(int)
    fc["weekday"] = fc["date"].dt.day_name()

    TABLEAU.mkdir(parents=True, exist_ok=True)
    fc.to_csv(TABLEAU / "forecast.csv", index=False)
    hist = f.reset_index().rename(columns={"order_date": "date", "orders": "actual_orders"})
    hist.to_csv(TABLEAU / "daily_volume_history.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 4))
    recent = f.iloc[-90:]
    ax.plot(recent.index, recent, color="#08519c", label="Actual")
    ax.plot(test.index, pred, color="#fd8d3c", ls="--", label="Holdout prediction")
    ax.plot(fc.date, fc.forecast_orders, color="#e6550d", lw=2, label="Forecast")
    ax.fill_between(fc.date, fc.lower_95, fc.upper_95, color="#e6550d", alpha=.2, label="95% interval")
    ax.set(title="Daily order volume: 14-day forecast", ylabel="Orders"); ax.legend(ncol=4, fontsize=8); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(IMAGES / "forecast.png", dpi=130); plt.close(fig)

    md = f"""# Forecast Model Summary

- Model: log-linear regression on trend + day-of-week (Monday baseline); multiplicative seasonality
- Holdout: last {HOLDOUT_DAYS} days, training on everything before
- Horizon: next {FORECAST_HORIZON_DAYS} days

| Model | MAE (orders/day) | MAPE |
|---|---:|---:|
| Regression | {metrics['model_mae']:.1f} | {metrics['model_mape']:.1f}% |
| Naive (same weekday last week) | {metrics['naive_mae']:.1f} | {metrics['naive_mape']:.1f}% |

Historical productivity: **{productivity:.1f} orders per scheduled agent per day** (median), used to convert the forecast into agents needed.
"""
    (DOCS / "forecast_summary.md").write_text(md)
    print(f"[forecast] {metrics}")
    return {"metrics": metrics, "forecast": fc, "productivity": productivity}
