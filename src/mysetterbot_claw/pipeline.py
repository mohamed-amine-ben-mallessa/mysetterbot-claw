"""
pipeline.py — a tiny persisted lead board (the setter's CRM).

State lives in ~/.mysetterbot-claw/pipeline.json (override dir via MSBC_STATE_DIR).
Each lead is keyed by username. Stages model a setter's funnel:

    sourced -> contacted -> no_reply -> engaged -> qualified -> handoff -> not_a_fit

No external deps. All timestamps are passed in by the caller (the MCP layer)
or omitted; we never call Date.now-style clocks implicitly beyond time.time().
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Optional

STAGES = ["sourced", "contacted", "no_reply", "engaged", "qualified", "handoff", "not_a_fit"]


def _path() -> Path:
    base = os.environ.get("MSBC_STATE_DIR") or os.path.join(os.path.expanduser("~"), ".mysetterbot-claw")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p / "pipeline.json"


def _load() -> dict:
    path = _path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"leads": {}}
    return {"leads": {}}


def _save(db: dict) -> None:
    _path().write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def upsert(username: str, *, stage: Optional[str] = None, note: str = "",
           temperature: str = "", need: str = "", thread_id: str = "",
           extra: Optional[dict] = None) -> dict:
    username = username.lstrip("@").strip()
    if not username:
        return {"ok": False, "error": "username required"}
    if stage and stage not in STAGES:
        return {"ok": False, "error": f"invalid stage '{stage}'. valid: {STAGES}"}
    db = _load()
    lead = db["leads"].get(username, {
        "username": username, "stage": "sourced",
        "created_at": _now(), "history": [],
    })
    if stage:
        if stage != lead.get("stage"):
            lead.setdefault("history", []).append({"at": _now(), "stage": stage, "note": note})
        lead["stage"] = stage
    for k, v in (("temperature", temperature), ("need", need), ("thread_id", thread_id)):
        if v:
            lead[k] = v
    if note and not stage:
        lead.setdefault("history", []).append({"at": _now(), "note": note})
    if extra:
        lead.setdefault("meta", {}).update(extra)
    lead["updated_at"] = _now()
    db["leads"][username] = lead
    _save(db)
    return {"ok": True, "lead": lead}


def get(username: str) -> dict:
    username = username.lstrip("@").strip()
    lead = _load()["leads"].get(username)
    if not lead:
        return {"ok": False, "error": f"no lead '{username}'"}
    return {"ok": True, "lead": lead}


def board(stage: str = "", temperature: str = "") -> dict:
    leads = list(_load()["leads"].values())
    if stage:
        leads = [l for l in leads if l.get("stage") == stage]
    if temperature:
        leads = [l for l in leads if l.get("temperature") == temperature]
    leads.sort(key=lambda l: l.get("updated_at", ""), reverse=True)
    counts: dict[str, int] = {}
    for l in _load()["leads"].values():
        counts[l.get("stage", "?")] = counts.get(l.get("stage", "?"), 0) + 1
    return {"ok": True, "total": len(leads), "by_stage": counts,
            "leads": [{k: l.get(k) for k in
                       ("username", "stage", "temperature", "need", "thread_id", "updated_at")}
                      for l in leads]}


def remove(username: str) -> dict:
    username = username.lstrip("@").strip()
    db = _load()
    if username in db["leads"]:
        db["leads"].pop(username)
        _save(db)
        return {"ok": True, "removed": username}
    return {"ok": False, "error": f"no lead '{username}'"}
