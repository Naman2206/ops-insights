"""End-to-end pipeline: generate -> load -> quality checks -> clean -> KPIs -> EDA -> forecast -> exports."""
import generate_data, clean, data_quality, eda, forecast, export_tableau, dashboard


def main():
    generate_data.generate()
    con = clean.connect()
    clean.build_schema(con)
    total = clean.harmonize(con)
    checks = data_quality.run_checks(con)
    print(checks.to_string(index=False))
    log = clean.apply_rules(con)
    data_quality.write_report(checks, total, log)
    print(f"[clean] {total:,} -> {log['_rows_out']:,} rows")
    eda.run(con)
    forecast.run(con)
    export_tableau.run(con)
    dashboard.run(con)
    con.close()


if __name__ == "__main__":
    main()
