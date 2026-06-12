"""
bulk.py — CSV import/export for the pipeline board. Stdlib csv only.

Import: a CSV with at least a 'username' column (extra columns: stage, temperature,
need, note, thread_id) is upserted into the board.
Export: the whole board (or a stage/temperature filter) to a CSV file.
"""
from __future__ import annotations

import csv
import os
from typing import Optional

from . import pipeline

IMPORT_FIELDS = ("username", "stage", "temperature", "need", "note", "thread_id")
EXPORT_FIELDS = ("username", "stage", "temperature", "need", "thread_id", "updated_at", "created_at")


def import_csv(path: str) -> dict:
    if not os.path.exists(path):
        return {"ok": False, "error": f"file not found: {path}"}
    imported, skipped, errors = 0, 0, []
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "username" not in [c.strip().lower() for c in reader.fieldnames]:
                return {"ok": False, "error": "CSV must have a 'username' column"}
            # normalize header case
            cols = {c.strip().lower(): c for c in reader.fieldnames}
            for row in reader:
                uname = (row.get(cols.get("username", "username")) or "").strip()
                if not uname:
                    skipped += 1
                    continue
                kw = {}
                for field in ("stage", "temperature", "need", "note", "thread_id"):
                    src = cols.get(field)
                    if src and row.get(src):
                        kw[field] = row[src].strip()
                res = pipeline.upsert(uname, **kw)
                if res.get("ok"):
                    imported += 1
                else:
                    errors.append({uname: res.get("error")})
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "imported": imported, "skipped": skipped,
            "errors": errors[:10], "error_count": len(errors)}


def export_csv(path: str, stage: str = "", temperature: str = "") -> dict:
    board = pipeline.board(stage=stage, temperature=temperature)
    leads = board.get("leads", [])
    try:
        # board() returns a trimmed view; fetch full records for export fields
        full = []
        for l in leads:
            rec = pipeline.get(l["username"]).get("lead", {})
            full.append({k: rec.get(k, "") for k in EXPORT_FIELDS})
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=EXPORT_FIELDS)
            w.writeheader()
            w.writerows(full)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "exported": len(full), "path": os.path.abspath(path)}
