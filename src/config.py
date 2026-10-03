from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
TABLEAU = ROOT / "data" / "tableau"
SQL = ROOT / "sql"
DOCS = ROOT / "docs"
IMAGES = DOCS / "images"
DB_PATH = PROCESSED / "ops.db"

CENTER_ALIASES = {
    "mumbai": "Mumbai", "pune": "Pune", "delhi": "Delhi",
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru",
}
MAX_CYCLE_HOURS = 72
FORECAST_HORIZON_DAYS = 14
HOLDOUT_DAYS = 28
