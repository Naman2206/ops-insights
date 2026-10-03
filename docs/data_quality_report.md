# Data Quality Report

- Rows ingested (System A + B): **71,388**
- Rows in clean fact table: **69,867**
- Rows rejected: **1,521** (2.13%)

## Pre-clean checks (SQL)

| Check | Severity | Description | Rows flagged |
|---|---|---|---:|
| `duplicate_order_ids` | error | order_id appears more than once | 707 |
| `completed_missing_timestamp` | error | status Completed but completed_at is null | 548 |
| `negative_cycle_time` | error | completed_at earlier than created_at | 209 |
| `extreme_cycle_time` | warn | cycle time greater than 72 hours | 69 |
| `null_units` | warn | units missing | 356 |
| `inconsistent_center_labels` | warn | rows whose center label is not in canonical form | 3,575 |
| `null_created_at` | error | created_at missing | 0 |

## Cleansing rules applied

| Rule | Rows affected |
|---|---:|
| `center_labels_standardized` | 3,575 |
| `unknown_center` | 0 |
| `duplicate_order_id` | 707 |
| `completed_missing_timestamp` | 542 |
| `negative_cycle_time` | 203 |
| `cycle_time_over_72h` | 69 |
| `units_imputed` | 345 |

Rejected rows are kept in the `rejected_records` table with a reason for auditability.
