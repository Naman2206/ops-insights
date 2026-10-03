# Building the Tableau Dashboard

Data sources (all in `data/tableau/` after running the pipeline):

| File | Grain | Use |
|---|---|---|
| `daily_kpis.csv` | day x center x process | Main KPI source |
| `daily_volume_history.csv` | day | Actual volume line |
| `forecast.csv` | day (next 14) | Forecast + staffing |
| `dim_process.csv` | process | SLA hours |
| `staffing.csv` | day x center | Optional capacity view |

## Connect
Data > New Data Source > Text file > `daily_kpis.csv`. Add `forecast.csv` as a second source (blend on nothing; used on its own sheets). Set `order_date` to **Date**.

## Calculated fields (consistent across every view)
Ratios are computed from SUMs so they aggregate correctly at any filter level. Never average a pre-computed rate.

```
Throughput            = SUM([orders_completed])
Avg Cycle Time (h)    = SUM([cycle_hours_sum]) / SUM([orders_completed])
Error Rate            = SUM([error_orders]) / SUM([orders_completed])
SLA Breach Rate       = SUM([sla_breaches]) / SUM([orders_completed])

// KPI cards: last 30 days vs prior 30
Max Date              = { MAX([order_date]) }
Is Current 30d        = [order_date] > DATEADD('day', -30, [Max Date])
Is Prior 30d          = [order_date] <= DATEADD('day', -30, [Max Date]) AND [order_date] > DATEADD('day', -60, [Max Date])
Throughput Current    = SUM(IF [Is Current 30d] THEN [orders_completed] END)
Throughput Prior      = SUM(IF [Is Prior 30d] THEN [orders_completed] END)
Throughput % Change   = [Throughput Current] / [Throughput Prior] - 1
```

## Sheets (match `docs/images/tableau_dashboard.png`)
1. **KPI cards (x4):** Text sheets using the fields above with `% Change` as a colored delta.
2. **Volume & Forecast:** `order_date` continuous line of `SUM(orders_created)` (7-day moving average via Quick Table Calc). Dual axis with `forecast.csv` `forecast_orders`; `lower_95`/`upper_95` as a band.
3. **Agents Needed:** bar of `agents_needed` by date from `forecast.csv`.
4. **Cycle Time Heatmap:** Rows = `center`, Columns = `process_type`, Color/Label = `Avg Cycle Time (h)`.
5. **Quality & SLA by Center:** bars of `Error Rate` and `SLA Breach Rate` by `center`.

## Dashboard
Size 1600 x 900. Add filters (center, process_type, date range) set to **Apply to all worksheets**. Add a Tooltip on the heatmap showing SLA hours.

## Export screenshot for the README
Dashboard > Export Image > save as `docs/images/tableau_dashboard.png` (replaces the preview).
