"""Writes database/sample_data.sql: the demonstration data as INSERT statements.

    python docs/tools/export_sample_data.py

It runs the application's own seeding code against a temporary database and dumps the rows, so the file
always matches `backend/app/utils/seed.py`. Load order: database/schema.sql first, then this file.
The demo accounts are for local use only (see README.md).
"""
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import Settings  # noqa: E402
from app.database import init_db, make_engine, make_session_factory  # noqa: E402
from app.utils import seed  # noqa: E402


def main() -> None:
    tmp = Path(tempfile.mkdtemp()) / "sample.db"
    settings = Settings(database_url=f"sqlite:///{tmp.as_posix()}", seed_demo_data=True)
    engine = make_engine(settings.database_url)
    init_db(engine)
    seed.seed_if_empty(make_session_factory(engine), settings)
    engine.dispose()
    con = sqlite3.connect(tmp)
    lines = [l for l in con.iterdump() if l.startswith("INSERT INTO")]
    con.close()
    counts = {}
    for l in lines:
        t = re.match(r'INSERT INTO "?(\w+)"?', l).group(1)
        counts[t] = counts.get(t, 0) + 1
    header = ["-- I-ITSM demonstration data (SQLite INSERT statements), generated from backend/app/utils/seed.py",
              "-- by docs/tools/export_sample_data.py. Load database/schema.sql first, then:",
              "--   sqlite3 itsm.db < database/sample_data.sql",
              "-- Passwords are bcrypt hashes of the demo passwords listed in README.md. Local use only.",
              "-- Rows: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())), "", "PRAGMA foreign_keys = OFF;", "BEGIN;"]
    (ROOT / "database" / "sample_data.sql").write_text("\n".join(header + lines + ["COMMIT;", "PRAGMA foreign_keys = ON;", ""]), encoding="utf-8")
    print("wrote database/sample_data.sql:", sum(counts.values()), "rows in", len(counts), "tables")


main()
