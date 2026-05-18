"""CLI to migrate legacy `candidates.csv` into SQLite-backed storage.

Usage:
    python scripts/migrate_candidates.py --csv path/to/candidates.csv --db path/to/candidates.db
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.candidate_service import CandidateStorage


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Migrate candidates CSV to SQLite DB")
    p.add_argument("--csv", required=True, help="Path to legacy candidates CSV")
    p.add_argument("--db", required=True, help="Path to SQLite DB to create/use")
    p.add_argument("--no-backup", action="store_true", help="Do not rename the CSV to .bak after migrating")

    args = p.parse_args(argv)

    csv_path = Path(args.csv)
    db_path = Path(args.db)

    if not csv_path.exists():
        print(f"CSV file not found: {csv_path}")
        return 2

    store = CandidateStorage(str(db_path))
    migrated = store.migrate_from_csv(str(csv_path), backup=not args.no_backup)
    print(f"Migrated {migrated} rows from {csv_path} into {db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
