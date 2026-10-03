"""Export Tableau / Power BI-ready flat files from the warehouse."""
import pandas as pd
from config import TABLEAU
from kpis import daily_kpis


def run(con):
    TABLEAU.mkdir(parents=True, exist_ok=True)
    k = daily_kpis(con)
    k["order_date"] = k["order_date"].dt.strftime("%Y-%m-%d")
    k.round(4).to_csv(TABLEAU / "daily_kpis.csv", index=False)
    pd.read_sql("SELECT * FROM dim_process", con).to_csv(TABLEAU / "dim_process.csv", index=False)
    pd.read_sql("SELECT * FROM staffing", con).to_csv(TABLEAU / "staffing.csv", index=False)
    print(f"[export] daily_kpis.csv ({len(k):,} rows) and supporting files -> data/tableau/")
