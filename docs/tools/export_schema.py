"""Regenerates database/schema.sql from the SQLAlchemy models.   python docs/tools/export_schema.py"""
import sys
from pathlib import Path

import codeinfo as ci
from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateIndex, CreateTable

out = ["-- I-ITSM database schema (SQLite). Generated from the SQLAlchemy models by docs/tools/export_schema.py.",
       "-- The application creates these tables automatically on first start. Use this file for review or manual setup:",
       "--   sqlite3 itsm.db < database/schema.sql", "", "PRAGMA foreign_keys = ON;", ""]
dialect = sqlite.dialect()
for table in ci.tables():
    out.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";\n")
    for index in sorted(table.indexes, key=lambda i: i.name or ""):
        out.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    out.append("")
out += ["-- OPTIONAL hardening, applied only when you load this file by hand (the running application does not",
        "-- create these triggers). The application itself blocks UPDATE and DELETE of audit rows through ORM",
        "-- event listeners in app/models/audit.py. The triggers enforce the same rule inside the database.",
        "CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;",
        "CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete BEFORE DELETE ON audit_logs BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;", ""]
target = ci.ROOT / "database" / "schema.sql"
target.write_text("\n".join(out))
print("wrote", target)
