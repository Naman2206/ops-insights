"""Run the SQL data-quality checks in sql/02_quality_checks.sql and write a markdown report."""
import re
import pandas as pd
from config import SQL, DOCS

HEADER = re.compile(r"--\s*name:\s*(\w+)\s*\|\s*severity:\s*(\w+)\s*\|\s*desc:\s*(.+)")


def run_checks(con):
    text = (SQL / "02_quality_checks.sql").read_text()
    parts = re.split(r"(?m)^(?=--\s*name:)", text)
    results = []
    for part in parts:
        m = HEADER.search(part)
        if not m:
            continue
        name, severity, desc = m.groups()
        query = "\n".join(l for l in part.splitlines() if not l.strip().startswith("--"))
        n = int(con.execute(query).fetchone()[0])
        results.append({"check": name, "severity": severity, "description": desc.strip(), "rows_flagged": n})
    return pd.DataFrame(results)


def write_report(checks, total_in, log):
    rules = {k: v for k, v in log.items() if not k.startswith("_")}
    rows_out = log["_rows_out"]
    lines = ["# Data Quality Report", "",
             f"- Rows ingested (System A + B): **{total_in:,}**",
             f"- Rows in clean fact table: **{rows_out:,}**",
             f"- Rows rejected: **{total_in - rows_out:,}** ({(total_in - rows_out) / total_in:.2%})", "",
             "## Pre-clean checks (SQL)", "",
             "| Check | Severity | Description | Rows flagged |", "|---|---|---|---:|"]
    for r in checks.itertuples():
        lines.append(f"| `{r.check}` | {r.severity} | {r.description} | {r.rows_flagged:,} |")
    lines += ["", "## Cleansing rules applied", "", "| Rule | Rows affected |", "|---|---:|"]
    for k, v in rules.items():
        lines.append(f"| `{k}` | {v:,} |")
    lines += ["", "Rejected rows are kept in the `rejected_records` table with a reason for auditability."]
    DOCS.mkdir(exist_ok=True)
    (DOCS / "data_quality_report.md").write_text("\n".join(lines) + "\n")
