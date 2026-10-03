"""Exploratory analysis: trends & bottlenecks. Saves charts and a findings summary."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from config import IMAGES, DOCS

PROC = ["Intake", "Verification", "Fulfillment", "Support"]
CEN = ["Mumbai", "Delhi", "Pune", "Bengaluru"]
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def run(con):
    IMAGES.mkdir(parents=True, exist_ok=True)
    f = pd.read_sql("SELECT * FROM fact_operations", con, parse_dates=["order_date"])
    done = f[f.status == "Completed"]
    daily = f.groupby("order_date").size().rename("orders")

    # 1. volume trend
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(daily.index, daily, color="#9ecae1", lw=0.8, label="Daily orders")
    ax.plot(daily.index, daily.rolling(7).mean(), color="#08519c", lw=2, label="7-day average")
    ax.set(title="Daily order volume", ylabel="Orders"); ax.legend(); ax.grid(alpha=.3)
    fig.tight_layout(); fig.savefig(IMAGES / "eda_volume_trend.png", dpi=130); plt.close(fig)

    # 2. weekday pattern
    wd = f.groupby(["order_date", "weekday"]).size().groupby("weekday").mean().reindex(DAYS)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(wd.index.str[:3], wd.values, color="#3182bd"); ax.set(title="Average orders by weekday", ylabel="Orders / day")
    fig.tight_layout(); fig.savefig(IMAGES / "eda_weekday.png", dpi=130); plt.close(fig)

    # 3. cycle-time heatmap (center x process), normalised to SLA
    piv = done.pivot_table(index="center", columns="process_type", values="cycle_hours", aggfunc="mean").loc[CEN, PROC]
    sla = done.groupby("process_type")["sla_hours"].first()[PROC]
    fig, ax = plt.subplots(figsize=(7, 4))
    im = ax.imshow((piv / sla).values, cmap="OrRd", vmin=0.2, vmax=1.0)
    ax.set_xticks(range(4), PROC); ax.set_yticks(range(4), CEN)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{piv.iloc[i, j]:.1f}h", ha="center", va="center", fontsize=10, color="white" if (piv / sla).iloc[i, j] > 0.7 else "black")
    ax.set_title("Avg cycle time (colour = share of SLA used)"); fig.colorbar(im, ax=ax, fraction=.046)
    fig.tight_layout(); fig.savefig(IMAGES / "eda_cycle_heatmap.png", dpi=130); plt.close(fig)

    # 4. error rate vs daily load
    d = f.assign(load=f.groupby("order_date")["order_id"].transform("count"))
    d = d[d.status == "Completed"]
    d["load_band"] = pd.qcut(d["load"], 4, labels=["Q1 (light)", "Q2", "Q3", "Q4 (peak)"])
    er = d.groupby("load_band", observed=True)["error_flag"].mean() * 100
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(er.index.astype(str), er.values, color=["#fdae6b", "#fd8d3c", "#e6550d", "#a63603"])
    ax.set(title="Error rate by daily load quartile", ylabel="Error rate (%)")
    fig.tight_layout(); fig.savefig(IMAGES / "eda_error_vs_load.png", dpi=130); plt.close(fig)

    # ---- findings (numbers computed, not hard-coded) ----
    first, last = daily.iloc[:90].mean(), daily.iloc[-90:].mean()
    ratio = (piv / sla).stack().sort_values(ascending=False)
    (c_top, p_top), r_top = ratio.index[0], ratio.iloc[0]
    proc_mean = done.groupby("process_type")["cycle_hours"].mean()
    others = done[(done.process_type == p_top) & (done.center != c_top)]["cycle_hours"].mean()
    breach = done.groupby(["center", "process_type"])["sla_breach"].mean().sort_values(ascending=False)
    mon = done.groupby("weekday")["cycle_hours"].mean()
    summary = {
        "growth_pct": (last / first - 1) * 100, "first90": first, "last90": last,
        "busiest_day": wd.idxmax(), "busiest_val": wd.max(), "quietest_day": wd.idxmin(), "quietest_val": wd.min(),
        "bn_center": c_top, "bn_proc": p_top, "bn_hours": piv.loc[c_top, p_top], "bn_other": others,
        "bn_breach": breach.iloc[0] * 100, "err_light": er.iloc[0], "err_peak": er.iloc[-1],
        "overall_err": done.error_flag.mean() * 100, "overall_breach": done.sla_breach.mean() * 100,
        "mon_cycle": mon["Monday"], "other_cycle": mon.drop("Monday").mean(),
    }
    s = summary
    md = f"""# EDA Findings

1. **Volume is growing steadily.** Average daily orders rose from {s['first90']:.0f} (first 90 days) to {s['last90']:.0f} (last 90 days), about **{s['growth_pct']:+.0f}%**.
2. **Strong weekly rhythm.** {s['busiest_day']} is the busiest day ({s['busiest_val']:.0f} orders) and {s['quietest_day']} the quietest ({s['quietest_val']:.0f}).
3. **Primary bottleneck: {s['bn_center']} {s['bn_proc']}.** Average cycle time is {s['bn_hours']:.1f}h versus {s['bn_other']:.1f}h for the same process at other centers, and {s['bn_breach']:.0f}% of its orders breach SLA.
4. **Quality degrades under load.** Error rate is {s['err_light']:.1f}% on the lightest-load days versus {s['err_peak']:.1f}% on the heaviest quartile.
5. **Monday backlog.** Average cycle time is {s['mon_cycle']:.1f}h on Mondays versus {s['other_cycle']:.1f}h on other days.

Overall: error rate {s['overall_err']:.1f}%, SLA breach rate {s['overall_breach']:.1f}%.
"""
    (DOCS / "eda_findings.md").write_text(md)
    print("[eda] charts + findings written")
    return summary
