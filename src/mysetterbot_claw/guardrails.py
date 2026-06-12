"""
guardrails.py — anti-ban safety layer.

Two jobs:
  1. PACING: enforce per-action daily quotas + a minimum delay between writes,
     persisted to a small JSON state file so limits survive across calls.
  2. DRY-RUN GATING: write/growth actions are dry-run by DEFAULT. The agent must
     pass approve=True (after showing the draft to the human) to actually send.

This is deliberately conservative. The whole point of a "setter" bot is to be
*helpful and human*, not to torch the account.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# Actions that mutate Instagram / are detectable. Defaults are intentionally low.
DEFAULT_DAILY_QUOTAS = {
    "dm_send": 40,        # cold + warm DMs per day
    "comments_add": 20,
    "comments_reply": 30,
    "follow": 20,
    "unfollow": 20,
    "like_post": 60,
}

# Actions that require human approval before leaving dry-run.
WRITE_ACTIONS = set(DEFAULT_DAILY_QUOTAS.keys()) | {"dm_send_media", "post", "story_post"}

# Actions behind Instagram's growth gate (need --enable-growth-actions).
GROWTH_ACTIONS = {"follow", "unfollow", "like_post", "unlike_post", "comments_add", "comments_reply"}

MIN_DELAY_SECONDS = 25  # minimum gap between two write actions


def _state_path() -> Path:
    base = os.environ.get("MSBC_STATE_DIR") or os.path.join(
        os.path.expanduser("~"), ".mysetterbot-claw"
    )
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p / "pacing.json"


@dataclass
class PacingState:
    day: str = ""
    counts: dict = field(default_factory=dict)
    last_write_ts: float = 0.0


def _today(now: float) -> str:
    return time.strftime("%Y-%m-%d", time.gmtime(now))


def _load(now: float) -> PacingState:
    path = _state_path()
    if path.exists():
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
            st = PacingState(**d)
        except Exception:
            st = PacingState()
    else:
        st = PacingState()
    # reset counters on a new UTC day
    if st.day != _today(now):
        st.day = _today(now)
        st.counts = {}
    return st


def _save(st: PacingState) -> None:
    _state_path().write_text(
        json.dumps({"day": st.day, "counts": st.counts, "last_write_ts": st.last_write_ts}),
        encoding="utf-8",
    )


def quota_for(action: str) -> int:
    env_key = f"MSBC_QUOTA_{action.upper()}"
    if env_key in os.environ:
        try:
            return int(os.environ[env_key])
        except ValueError:
            pass
    return DEFAULT_DAILY_QUOTAS.get(action, 9999)


@dataclass
class GateDecision:
    allowed: bool
    reason: str = ""
    remaining_today: Optional[int] = None
    wait_seconds: int = 0


def check(action: str, now: Optional[float] = None) -> GateDecision:
    """Check (without consuming) whether a write action is currently allowed."""
    now = now if now is not None else time.time()
    st = _load(now)
    used = st.counts.get(action, 0)
    limit = quota_for(action)
    remaining = max(0, limit - used)
    if remaining <= 0:
        return GateDecision(False, f"daily quota reached for '{action}' ({limit}/day)", 0)
    gap = now - (st.last_write_ts or 0)
    if st.last_write_ts and gap < MIN_DELAY_SECONDS:
        wait = int(MIN_DELAY_SECONDS - gap) + 1
        return GateDecision(False, f"pacing: wait {wait}s between writes", remaining, wait)
    return GateDecision(True, "ok", remaining)


def consume(action: str, now: Optional[float] = None) -> None:
    """Record that a write action actually happened (call AFTER a successful send)."""
    now = now if now is not None else time.time()
    st = _load(now)
    st.counts[action] = st.counts.get(action, 0) + 1
    st.last_write_ts = now
    _save(st)


def usage_report(now: Optional[float] = None) -> dict:
    now = now if now is not None else time.time()
    st = _load(now)
    return {
        "day_utc": st.day,
        "actions": {
            a: {"used": st.counts.get(a, 0), "limit": quota_for(a),
                "remaining": max(0, quota_for(a) - st.counts.get(a, 0))}
            for a in DEFAULT_DAILY_QUOTAS
        },
        "min_delay_seconds": MIN_DELAY_SECONDS,
    }
