#!/usr/bin/env python3
"""
demo_setter.py — a guided, DRY-RUN-ONLY walkthrough of the setter loop.

It calls the MCP tool handlers directly (no server round-trip) so you can read,
step by step, what a real outreach sequence looks like. It NEVER sends anything:
every write tool is invoked without approve=true, so you only ever see previews.

Usage:
    set OPENROUTER_API_KEY=...           # for the LLM tools
    set MSBC_CLI=...\\clinstagram.exe     # if the binary isn't on PATH
    python demo_setter.py <a_real_username> "<your one-line offer>"

Requires the package importable (run from repo root, or set PYTHONPATH=src).
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from mysetterbot_claw.tools import dispatch  # noqa: E402


def show(title, result):
    print(f"\n=== {title} ===")
    print(json.dumps(result, ensure_ascii=False, indent=2)[:1400])


def main() -> int:
    username = sys.argv[1] if len(sys.argv) > 1 else "n8n.io"
    offer = sys.argv[2] if len(sys.argv) > 2 else "I help agencies productize automation"

    # 1. health
    show("doctor", dispatch("doctor", {}))

    # 2. one-shot prospect brief (profile + last post + drafted opener)
    brief = dispatch("prospect_brief", {"username": username, "offer": offer})
    show("prospect_brief", brief)

    opener = brief.get("suggested_opener") or "(no opener generated)"

    # 3. DRY-RUN the send — note: NO approve=true, so nothing is sent
    show("dm_send (DRY-RUN, nothing sent)",
         dispatch("dm_send", {"user": username, "message": opener}))

    # 4. add to the pipeline board
    show("pipeline_set", dispatch("pipeline_set",
         {"username": username, "stage": "sourced", "note": "from demo"}))
    show("pipeline_board", dispatch("pipeline_board", {}))

    # 5. where do we stand on quotas
    show("usage", dispatch("usage", {}))

    print("\nDone. Nothing was sent — every write was dry-run. "
          "To actually send, add approve=true to dm_send AFTER reviewing the draft.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
