# Forecast Model Summary

- Model: log-linear regression on trend + day-of-week (Monday baseline); multiplicative seasonality
- Holdout: last 28 days, training on everything before
- Horizon: next 14 days

| Model | MAE (orders/day) | MAPE |
|---|---:|---:|
| Regression | 11.2 | 7.9% |
| Naive (same weekday last week) | 12.1 | 8.4% |

Historical productivity: **15.3 orders per scheduled agent per day** (median), used to convert the forecast into agents needed.
