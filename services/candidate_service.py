from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any
import json

from config.logging_config import get_logger
from utils.constants import CANDIDATE_FIELDS
from utils.helpers import ensure_dir

logger = get_logger(__name__)


class CandidateStorage:
    """SQLite-backed candidate storage with WAL mode for concurrent writes.

    API matches previous CSV-based `CandidateStorage`:
    - `append_record(record: dict)`
    - `load_recent(limit: int)`
    """

    def __init__(self, db_path: str, legacy_csv_path: str | None = None) -> None:
        self.db_path = Path(db_path)
        ensure_dir(str(self.db_path.parent))
        # initialize DB and enable WAL for concurrency
        self._initialize_db()

        # optional automatic migration from legacy CSV
        if legacy_csv_path:
            csvp = Path(legacy_csv_path)
            if csvp.exists():
                try:
                    self.migrate_from_csv(str(csvp))
                except Exception as exc:
                    logger.exception("Automatic migration from CSV failed: %s", exc)

    def _get_conn(self):
        # each operation gets a short-lived connection; sqlite is file-based
        conn = sqlite3.connect(str(self.db_path), timeout=30, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _initialize_db(self) -> None:
        conn = self._get_conn()
        try:
            cols = [f"{c} TEXT" for c in CANDIDATE_FIELDS]
            # primary key is implicit rowid
            create_sql = f"CREATE TABLE IF NOT EXISTS candidates ({', '.join(cols)})"
            conn.execute(create_sql)
            conn.commit()
            # ensure optional JSON columns exist for structured fields
            self._ensure_json_columns(conn)
        finally:
            conn.close()

    def _ensure_json_columns(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(candidates)")
        existing = {row[1] for row in cur.fetchall()}  # column name at index 1
        extras = {
            "skills_json": "TEXT",
            "strengths_json": "TEXT",
            "weaknesses_json": "TEXT",
        }
        for col, typ in extras.items():
            if col not in existing:
                try:
                    conn.execute(f"ALTER TABLE candidates ADD COLUMN {col} {typ} DEFAULT ''")
                    logger.info("Added column %s to candidates table", col)
                except Exception as exc:
                    logger.warning("Could not add column %s: %s", col, exc)

    def append_record(self, record: dict[str, Any]) -> None:
        row = {field: "" for field in CANDIDATE_FIELDS}
        row["timestamp"] = record.get("timestamp", "")
        row["name"] = record.get("name", "")
        row["score"] = str(record.get("score", ""))
        row["recommendation"] = record.get("recommendation", "")
        row["skills"] = self._format_list(record.get("skills", []))
        row["strengths"] = self._format_list(record.get("strengths", []))
        row["weaknesses"] = self._format_list(record.get("weaknesses", []))

        placeholders = ", ".join(["?" for _ in CANDIDATE_FIELDS])
        insert_sql = f"INSERT INTO candidates ({', '.join(CANDIDATE_FIELDS)}) VALUES ({placeholders})"

        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            cur.execute(insert_sql, [row[f] for f in CANDIDATE_FIELDS])
            conn.commit()
            logger.info("Candidate record stored: %s", row.get("name"))
        except Exception as exc:
            logger.exception("Failed to store candidate record: %s", exc)
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        finally:
            conn.close()

    def load_recent(self, limit: int = 20) -> list[dict[str, Any]]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            # rowid gives insertion order
            cur.execute(f"SELECT {', '.join(CANDIDATE_FIELDS)} FROM candidates ORDER BY rowid DESC LIMIT ?", (limit,))
            rows = cur.fetchall()
            results: list[dict[str, Any]] = []
            for r in rows:
                rec = {field: r[idx] for idx, field in enumerate(CANDIDATE_FIELDS)}
                results.append(rec)
            return results
        except Exception as exc:
            logger.warning("Failed to load recent candidates: %s", exc)
            return []
        finally:
            conn.close()

    def _format_list(self, value: Any) -> str:
        # store lists as semicolon-separated strings for backward compatibility
        if isinstance(value, list):
            return "; ".join(str(item).strip() for item in value if str(item).strip())
        if isinstance(value, str):
            return value
        if value is None:
            return ""
        return str(value)

    def migrate_from_csv(self, csv_path: str, backup: bool = True) -> int:
        """Migrate rows from a legacy CSV into the SQLite `candidates` table.

        Returns the number of rows migrated. Optionally renames the CSV to '.bak' on success.
        """
        import csv
        from pathlib import Path

        csvp = Path(csv_path)
        if not csvp.exists():
            raise FileNotFoundError(csv_path)

        inserted = 0
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            with csvp.open("r", newline="", encoding="utf-8") as rf:
                reader = csv.DictReader(rf)
                for row in reader:
                    # build record mapping; preserve legacy columns
                    record = {}
                    for f in CANDIDATE_FIELDS:
                        record[f] = row.get(f, "")

                    # parse list-like fields into JSON
                    def parse_list_field(val: str):
                        if not val:
                            return []
                        parts = [p.strip() for p in val.split(";") if p.strip()]
                        return parts

                    skills = parse_list_field(record.get("skills", ""))
                    strengths = parse_list_field(record.get("strengths", ""))
                    weaknesses = parse_list_field(record.get("weaknesses", ""))

                    # prepare insert with extra json columns
                    all_fields = list(CANDIDATE_FIELDS) + ["skills_json", "strengths_json", "weaknesses_json"]
                    placeholders = ", ".join(["?" for _ in all_fields])
                    insert_sql = f"INSERT INTO candidates ({', '.join(all_fields)}) VALUES ({placeholders})"
                    values = [record.get(f, "") for f in CANDIDATE_FIELDS]
                    values.extend([json.dumps(skills), json.dumps(strengths), json.dumps(weaknesses)])
                    cur.execute("BEGIN IMMEDIATE")
                    cur.execute(insert_sql, values)
                    conn.commit()
                    inserted += 1

        finally:
            conn.close()

        if inserted and backup:
            try:
                bak = csvp.with_suffix(csvp.suffix + ".bak")
                csvp.rename(bak)
                logger.info("Migrated %s rows from %s to sqlite and backed up to %s", inserted, csv_path, bak)
            except Exception as exc:
                logger.warning("Migration succeeded but failed to backup CSV: %s", exc)

        return inserted
