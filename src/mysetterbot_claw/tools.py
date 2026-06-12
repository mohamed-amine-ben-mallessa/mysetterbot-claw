"""
tools.py — the MCP tool catalog and their handlers.

Two families:
  A) CLI passthrough tools (1:1 with the clinstagram/msbc action surface), read
     tools run freely; WRITE/GROWTH tools are dry-run by default and gated.
  B) Setter tools (LLM text generation): draft_opener, draft_followup,
     draft_reply, qualify_lead — these NEVER send; they return text for approval.

Every handler returns a JSON-serializable dict.
"""
from __future__ import annotations

from typing import Any, Callable

from . import guardrails as G
from . import llm, prompts
from .cli_bridge import CliError, CliResult, run_cli

# ── helpers ───────────────────────────────────────────────────────────────────


def _result(r: CliResult) -> dict:
    if r.ok:
        return {"ok": True, "backend_used": r.backend_used, "data": r.data}
    return {
        "ok": False, "exit_code": r.exit_code, "error": r.error,
        "remediation": r.remediation or _hint(r.exit_code),
    }


def _hint(code: int) -> str:
    return {
        2: "Session expired — run `msbc auth login` (or `clinstagram auth login`).",
        3: "Rate-limited — wait and retry; respect daily quotas.",
        5: "2FA / checkpoint required — log in interactively once.",
        6: "Blocked by growth gate / compliance mode. Set approve=True + the action is gated for a reason.",
    }.get(code, "")


def _write_gate(action: str, approve: bool, force: bool) -> dict | None:
    """Return a dict to short-circuit (dry-run or blocked), or None to proceed."""
    decision = G.check(action)
    if not approve:
        return {
            "ok": True, "dry_run": True, "action": action,
            "would_send": True, "pacing": {
                "allowed_now": decision.allowed, "reason": decision.reason,
                "remaining_today": decision.remaining_today, "wait_seconds": decision.wait_seconds,
            },
            "note": "DRY-RUN (default). Review, then call again with approve=true to actually send.",
        }
    if not decision.allowed and not force:
        return {
            "ok": False, "blocked": True, "action": action, "reason": decision.reason,
            "wait_seconds": decision.wait_seconds, "remaining_today": decision.remaining_today,
            "note": "Pacing/quota guard. Pass force=true to override (NOT recommended).",
        }
    return None


# ── A) CLI passthrough — READ (safe, no gate) ────────────────────────────────


def t_dm_inbox(limit: int = 20, unread_only: bool = False, **_) -> dict:
    args = ["dm", "inbox", "--limit", str(limit)]
    if unread_only:
        args.append("--unread")
    return _result(run_cli(args))


def t_dm_thread(thread_id: str, limit: int = 20, **_) -> dict:
    return _result(run_cli(["dm", "thread", thread_id, "--limit", str(limit)]))


def t_dm_search(query: str, **_) -> dict:
    return _result(run_cli(["dm", "search", query]))


def t_user_info(username: str, **_) -> dict:
    return _result(run_cli(["user", "info", username]))


def t_user_search(query: str, **_) -> dict:
    return _result(run_cli(["user", "search", query]))


def t_user_posts(username: str, limit: int = 12, **_) -> dict:
    return _result(run_cli(["user", "posts", username, "--limit", str(limit)]))


def t_hashtag_recent(tag: str, limit: int = 30, **_) -> dict:
    return _result(run_cli(["hashtag", "recent", tag, "--limit", str(limit)]))


def t_hashtag_top(tag: str, limit: int = 30, **_) -> dict:
    return _result(run_cli(["hashtag", "top", tag, "--limit", str(limit)]))


def t_analytics_profile(**_) -> dict:
    return _result(run_cli(["analytics", "profile"]))


def t_analytics_post(media_id: str = "latest", **_) -> dict:
    return _result(run_cli(["analytics", "post", media_id]))


def t_comments_list(media_id: str, limit: int = 50, **_) -> dict:
    return _result(run_cli(["comments", "list", media_id, "--limit", str(limit)]))


def t_followers_list(limit: int = 50, **_) -> dict:
    return _result(run_cli(["followers", "list", "--limit", str(limit)]))


def t_following_list(limit: int = 50, **_) -> dict:
    return _result(run_cli(["followers", "following", "--limit", str(limit)]))


# ── A) CLI passthrough — WRITE / GROWTH (gated, dry-run default) ──────────────


def t_dm_send(user: str, message: str, approve: bool = False, force: bool = False, **_) -> dict:
    gate = _write_gate("dm_send", approve, force)
    if gate is not None:
        return {**gate, "preview": {"to": user, "message": message}}
    r = run_cli(["dm", "send", user, message])
    if r.ok:
        G.consume("dm_send")
    return _result(r)


def t_dm_send_media(user: str, media: str, approve: bool = False, force: bool = False, **_) -> dict:
    gate = _write_gate("dm_send_media", approve, force)
    if gate is not None:
        return {**gate, "preview": {"to": user, "media": media}}
    r = run_cli(["dm", "send-media", user, media])
    if r.ok:
        G.consume("dm_send_media")
    return _result(r)


def t_comments_add(media_id: str, text: str, approve: bool = False, force: bool = False, **_) -> dict:
    gate = _write_gate("comments_add", approve, force)
    if gate is not None:
        return {**gate, "preview": {"media_id": media_id, "text": text}}
    r = run_cli(["comments", "add", media_id, text], enable_growth=True)
    if r.ok:
        G.consume("comments_add")
    return _result(r)


def t_comments_reply(comment_id: str, text: str, approve: bool = False, force: bool = False, **_) -> dict:
    gate = _write_gate("comments_reply", approve, force)
    if gate is not None:
        return {**gate, "preview": {"comment_id": comment_id, "text": text}}
    r = run_cli(["comments", "reply", comment_id, text], enable_growth=True)
    if r.ok:
        G.consume("comments_reply")
    return _result(r)


def t_follow(user: str, approve: bool = False, force: bool = False, **_) -> dict:
    gate = _write_gate("follow", approve, force)
    if gate is not None:
        return {**gate, "preview": {"follow": user}}
    r = run_cli(["followers", "follow", user], enable_growth=True)
    if r.ok:
        G.consume("follow")
    return _result(r)


def t_unfollow(user: str, approve: bool = False, force: bool = False, **_) -> dict:
    gate = _write_gate("unfollow", approve, force)
    if gate is not None:
        return {**gate, "preview": {"unfollow": user}}
    r = run_cli(["followers", "unfollow", user], enable_growth=True)
    if r.ok:
        G.consume("unfollow")
    return _result(r)


def t_like_post(media_id: str, approve: bool = False, force: bool = False, **_) -> dict:
    gate = _write_gate("like_post", approve, force)
    if gate is not None:
        return {**gate, "preview": {"like": media_id}}
    r = run_cli(["like", "post", media_id], enable_growth=True)
    if r.ok:
        G.consume("like_post")
    return _result(r)


# ── B) Setter tools (LLM text gen — never send) ──────────────────────────────


def t_draft_opener(prospect: dict, offer: str, **_) -> dict:
    text = llm.complete(prompts.OPENER_SYSTEM, prompts.opener_user(prospect or {}, offer))
    return {"ok": True, "draft": text, "kind": "opener",
            "note": "Review/edit, then send via dm_send(user, message, approve=true)."}


def t_draft_followup(prospect: dict, offer: str, previous: str, days_since: int = 3, **_) -> dict:
    text = llm.complete(
        prompts.FOLLOWUP_SYSTEM,
        prompts.followup_user(prospect or {}, offer, previous, days_since),
    )
    return {"ok": True, "draft": text, "kind": "followup",
            "note": "Review, then send via dm_send(..., approve=true)."}


def t_draft_reply(prospect: dict, offer: str, conversation: str, **_) -> dict:
    text = llm.complete(
        prompts.REPLY_SYSTEM, prompts.reply_user(prospect or {}, offer, conversation)
    )
    return {"ok": True, "draft": text, "kind": "reply",
            "note": "Review, then send via dm_send(..., approve=true)."}


def t_qualify_lead(conversation: str, offer: str = "", **_) -> dict:
    try:
        data = llm.complete_json(prompts.QUALIFY_SYSTEM, prompts.qualify_user(conversation, offer))
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"qualification parse failed: {e}"}
    return {"ok": True, "qualification": data}


# ── meta tools ───────────────────────────────────────────────────────────────


def t_usage(**_) -> dict:
    return {"ok": True, "usage": G.usage_report()}


def t_doctor(**_) -> dict:
    return _result(run_cli(["doctor"]))


# ── registry ──────────────────────────────────────────────────────────────────

# name -> (handler, description, input_schema)
TOOLS: dict[str, tuple[Callable[..., dict], str, dict]] = {}


def _reg(name, fn, desc, props, required=None):
    TOOLS[name] = (fn, desc, {
        "type": "object",
        "properties": props,
        "required": required or [],
    })


_S = {"type": "string"}
_I = {"type": "integer"}
_B = {"type": "boolean"}
_O = {"type": "object"}

# read
_reg("dm_inbox", t_dm_inbox, "List DM inbox threads.",
     {"limit": _I, "unread_only": _B})
_reg("dm_thread", t_dm_thread, "Read messages in a DM thread (handles voice/media items safely).",
     {"thread_id": _S, "limit": _I}, ["thread_id"])
_reg("dm_search", t_dm_search, "Search DM threads by keyword.", {"query": _S}, ["query"])
_reg("user_info", t_user_info, "Get a user's profile (bio, counts, verified).",
     {"username": _S}, ["username"])
_reg("user_search", t_user_search, "Search users by name/username.", {"query": _S}, ["query"])
_reg("user_posts", t_user_posts, "List a user's recent posts (for personalization).",
     {"username": _S, "limit": _I}, ["username"])
_reg("hashtag_recent", t_hashtag_recent, "Recent posts for a hashtag (prospecting).",
     {"tag": _S, "limit": _I}, ["tag"])
_reg("hashtag_top", t_hashtag_top, "Top posts for a hashtag (prospecting).",
     {"tag": _S, "limit": _I}, ["tag"])
_reg("analytics_profile", t_analytics_profile, "Your profile analytics.", {})
_reg("analytics_post", t_analytics_post, "Analytics for a post ('latest' or media_id).",
     {"media_id": _S})
_reg("comments_list", t_comments_list, "List comments on a post.",
     {"media_id": _S, "limit": _I}, ["media_id"])
_reg("followers_list", t_followers_list, "List your followers.", {"limit": _I})
_reg("following_list", t_following_list, "List accounts you follow.", {"limit": _I})

# write / growth (gated)
_GATE = {"approve": _B, "force": _B}
_reg("dm_send", t_dm_send, "Send a text DM. DRY-RUN unless approve=true. Rate-limited.",
     {"user": _S, "message": _S, **_GATE}, ["user", "message"])
_reg("dm_send_media", t_dm_send_media, "Send a media DM. DRY-RUN unless approve=true.",
     {"user": _S, "media": _S, **_GATE}, ["user", "media"])
_reg("comments_add", t_comments_add, "Comment on a post (growth-gated). DRY-RUN unless approve=true.",
     {"media_id": _S, "text": _S, **_GATE}, ["media_id", "text"])
_reg("comments_reply", t_comments_reply, "Reply to a comment (growth-gated). DRY-RUN unless approve=true.",
     {"comment_id": _S, "text": _S, **_GATE}, ["comment_id", "text"])
_reg("follow", t_follow, "Follow a user (growth-gated). DRY-RUN unless approve=true.",
     {"user": _S, **_GATE}, ["user"])
_reg("unfollow", t_unfollow, "Unfollow a user (growth-gated). DRY-RUN unless approve=true.",
     {"user": _S, **_GATE}, ["user"])
_reg("like_post", t_like_post, "Like a post (growth-gated). DRY-RUN unless approve=true.",
     {"media_id": _S, **_GATE}, ["media_id"])

# setter (LLM, never sends)
_reg("draft_opener", t_draft_opener,
     "Write a personalized cold opener from prospect context (free LLM). Returns text only.",
     {"prospect": _O, "offer": _S}, ["offer"])
_reg("draft_followup", t_draft_followup,
     "Write a low-pressure follow-up (free LLM). Returns text only.",
     {"prospect": _O, "offer": _S, "previous": _S, "days_since": _I}, ["offer", "previous"])
_reg("draft_reply", t_draft_reply,
     "Write the next reply that gently qualifies (free LLM). Returns text only.",
     {"prospect": _O, "offer": _S, "conversation": _S}, ["offer", "conversation"])
_reg("qualify_lead", t_qualify_lead,
     "Classify a conversation (temperature/stage/need/next_action) as JSON (free LLM).",
     {"conversation": _S, "offer": _S}, ["conversation"])

# meta
_reg("usage", t_usage, "Show today's action usage vs daily quotas (anti-ban pacing).", {})
_reg("doctor", t_doctor, "CLI/session health check.", {})


def dispatch(name: str, arguments: dict) -> dict:
    if name not in TOOLS:
        return {"ok": False, "error": f"unknown tool '{name}'"}
    fn, _, _schema = TOOLS[name]
    try:
        return fn(**(arguments or {}))
    except CliError as e:
        return {"ok": False, "exit_code": e.exit_code, "error": str(e),
                "remediation": e.remediation or _hint(e.exit_code)}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def list_tools() -> list[dict]:
    return [
        {"name": n, "description": d, "inputSchema": s}
        for n, (_, d, s) in TOOLS.items()
    ]
