"""Render a static preview of the Tableau dashboard layout from the exported KPI data."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.gridspec import GridSpec
from config import IMAGES, TABLEAU
from kpis import daily_kpis

BLUE, ORANGE, GREY = "#1f77b4", "#ff7f0e", "#595959"


def agg(df):
    s = df[["orders_completed", "units_completed", "error_orders", "sla_breaches", "cycle_hours_sum"]].sum()
    return {"thr": s.orders_completed, "cyc": s.cycle_hours_sum / s.orders_completed,
            "err": s.error_orders / s.orders_completed * 100, "sla": s.sla_breaches / s.orders_completed * 100}


def run(con):
    k = daily_kpis(con)
    end = k.order_date.max()
    cur = agg(k[k.order_date > end - pd.Timedelta(days=30)])
    prev = agg(k[(k.order_date <= end - pd.Timedelta(days=30)) & (k.order_date > end - pd.Timedelta(days=60))])
    fc = pd.read_csv(TABLEAU / "forecast.csv", parse_dates=["date"])
    hist = pd.read_csv(TABLEAU / "daily_volume_history.csv", parse_dates=["date"]).set_index("date")["actual_orders"]

    fig = plt.figure(figsize=(16, 9), facecolor="white")
    gs = GridSpec(3, 4, figure=fig, height_ratios=[0.7, 1.6, 1.6], hspace=0.55, wspace=0.35, left=.07, right=.98, top=.88, bottom=.07)
    fig.text(.04, .94, "Ops Insights | Operations Performance Dashboard", fontsize=20, weight="bold", color="#1b3a5c")
    fig.text(.04, .905, f"Last 30 days ending {end:%d %b %Y} vs prior 30 days  |  Centers: All  |  Processes: All", fontsize=10, color=GREY)

    cards = [("Throughput (orders)", f"{cur['thr']:,.0f}", cur["thr"] / prev["thr"] - 1, True),
             ("Avg Cycle Time", f"{cur['cyc']:.1f} h", cur["cyc"] / prev["cyc"] - 1, False),
             ("Error Rate", f"{cur['err']:.2f}%", cur["err"] - prev["err"], False),
             ("SLA Breach Rate", f"{cur['sla']:.1f}%", cur["sla"] - prev["sla"], False)]
    for i, (name, val, delta, up_good) in enumerate(cards):
        ax = fig.add_subplot(gs[0, i]); ax.axis("off")
        ax.add_patch(plt.Rectangle((0, 0), 1, 1, transform=ax.transAxes, fc="#f4f7fb", ec="#d0d7e2"))
        good = (delta >= 0) == up_good
        unit = "%" if i < 2 else " pts"
        ax.text(.05, .72, name, fontsize=11, color=GREY, transform=ax.transAxes)
        ax.text(.05, .30, val, fontsize=24, weight="bold", color="#1b3a5c", transform=ax.transAxes)
        d = delta * 100 if i < 2 else delta
        ax.text(.95, .30, f"{'▲' if d >= 0 else '▼'} {abs(d):.1f}{unit}", ha="right", fontsize=11,
                color="#2ca02c" if good else "#d62728", transform=ax.transAxes)

    ax = fig.add_subplot(gs[1, :3])
    r = hist.iloc[-120:]
    ax.plot(r.index, r, color="#aec7e8", lw=1); ax.plot(r.index, r.rolling(7).mean(), color=BLUE, lw=2, label="Actual (7-day avg)")
    ax.plot(fc.date, fc.forecast_orders, color=ORANGE, lw=2, label="Forecast")
    ax.fill_between(fc.date, fc.lower_95, fc.upper_95, color=ORANGE, alpha=.2)
    ax.set_title("Daily Order Volume & 14-Day Forecast", loc="left", fontsize=12, weight="bold"); ax.legend(fontsize=8, loc="upper left"); ax.grid(alpha=.25)
    import matplotlib.dates as mdates; ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))

    ax = fig.add_subplot(gs[1, 3])
    st = fc.assign(d=fc.date.dt.strftime("%a %d"))
    ax.bar(st.d, st.agents_needed, color="#9467bd"); ax.set_xticks(range(len(st)), st.d, rotation=90, fontsize=7)
    ax.set_title("Agents Needed (forecast)", loc="left", fontsize=12, weight="bold")

    ax = fig.add_subplot(gs[2, :2])
    last = k[k.order_date > end - pd.Timedelta(days=90)]
    g = last.groupby(["center", "process_type"]).agg(c=("cycle_hours_sum", "sum"), n=("orders_completed", "sum"))
    piv = (g.c / g.n).unstack().loc[["Mumbai", "Delhi", "Pune", "Bengaluru"], ["Intake", "Verification", "Fulfillment", "Support"]]
    im = ax.imshow(piv.values, cmap="YlOrRd", aspect="auto", vmin=0, vmax=20)
    ax.set_xticks(range(4), piv.columns); ax.set_yticks(range(4), piv.index)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, f"{piv.iloc[i, j]:.1f}h", ha="center", va="center", fontsize=10, color="white" if piv.iloc[i, j] > 12 else "black")
    ax.set_title("Avg Cycle Time by Center x Process (last 90 days)", loc="left", fontsize=12, weight="bold")

    ax = fig.add_subplot(gs[2, 2:])
    ce = last.groupby("center")[["error_orders", "sla_breaches", "orders_completed"]].sum()
    ce = ce.loc[["Mumbai", "Delhi", "Pune", "Bengaluru"]]
    x = np.arange(4); w = .38
    ax.bar(x - w / 2, ce.error_orders / ce.orders_completed * 100, w, color="#d62728", label="Error rate %")
    ax.bar(x + w / 2, ce.sla_breaches / ce.orders_completed * 100, w, color="#ff9896", label="SLA breach %")
    ax.set_xticks(x, ce.index); ax.legend(fontsize=8); ax.grid(axis="y", alpha=.25)
    ax.set_title("Quality & SLA by Center (last 90 days)", loc="left", fontsize=12, weight="bold")

    fig.savefig(IMAGES / "tableau_dashboard.png", dpi=110); plt.close(fig)
    print("[dashboard] preview saved")
