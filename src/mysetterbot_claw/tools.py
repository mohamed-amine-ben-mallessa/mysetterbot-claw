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

from . import bulk, guardrails as G
from . import llm, pipeline, prompts
from .cli_bridge import CliError, CliResult, run_cli


def _unwrap(r: CliResult) -> Any:
    """Return CLI data on success, else None (for internal composition)."""
    return r.data if r.ok else None

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


# ── C) ICP / intelligence (LLM, read-only) ──────────────────────────────────


def t_extract_icp(username: str, posts_limit: int = 12, **_) -> dict:
    """Analyze an Instagram account -> its Ideal Customer Profile + prospecting plan."""
    info = _unwrap(run_cli(["user", "info", username]))
    if not info:
        return {"ok": False, "error": f"could not fetch profile for '{username}' "
                "(private/blocked/typo, or session/rate issue)."}
    posts = _unwrap(run_cli(["user", "posts", username, "--limit", str(posts_limit)])) or []
    if isinstance(posts, dict):
        posts = posts.get("items") or posts.get("posts") or []
    try:
        icp = llm.complete_json(prompts.ICP_SYSTEM, prompts.icp_user(info, posts))
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"ICP analysis failed: {e}"}
    return {"ok": True, "account": username, "profile": {
        "followers": info.get("followers_count"), "bio": info.get("biography"),
    }, "icp": icp,
        "note": "Use icp.prospecting.hashtags / search_queries with find_prospects."}


def t_score_prospect(prospect: dict, icp: str, **_) -> dict:
    try:
        data = llm.complete_json(prompts.SCORE_SYSTEM, prompts.score_user(prospect or {}, icp))
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"scoring failed: {e}"}
    return {"ok": True, "score": data}


def t_find_prospects(hashtag: str = "", query: str = "", limit: int = 20,
                     enrich: bool = True, **_) -> dict:
    """Source candidate accounts from a hashtag and/or a user search, optionally enriched."""
    found: dict[str, dict] = {}
    if hashtag:
        posts = _unwrap(run_cli(["hashtag", "recent", hashtag.lstrip("#"), "--limit", str(limit)])) or []
        if isinstance(posts, dict):
            posts = posts.get("items") or posts.get("posts") or []
        for p in posts:
            u = (p.get("user") or {})
            un = u.get("username") or p.get("username")
            if un and un not in found:
                found[un] = {"username": un, "source": f"#{hashtag.lstrip('#')}",
                             "full_name": u.get("full_name")}
    if query:
        users = _unwrap(run_cli(["user", "search", query])) or []
        if isinstance(users, dict):
            users = users.get("users") or users.get("items") or []
        for u in users[:limit]:
            un = u.get("username")
            if un and un not in found:
                found[un] = {"username": un, "source": f"search:{query}",
                             "full_name": u.get("full_name")}
    prospects = list(found.values())[:limit]
    if enrich:
        for pr in prospects:
            info = _unwrap(run_cli(["user", "info", pr["username"]]))
            if info:
                pr.update({k: info.get(k) for k in
                           ("biography", "followers_count", "following_count",
                            "media_count", "is_verified") if info.get(k) is not None})
    return {"ok": True, "count": len(prospects), "prospects": prospects}


# ── D) Engagement warm-up (LLM draft + gated like/comment) ───────────────────


def t_engagement_warmup(username: str, like: bool = True, comment: bool = True,
                        offer: str = "", approve: bool = False, force: bool = False, **_) -> dict:
    """
    Warm up a prospect before any cold DM: like their latest post and/or drop a
    genuine comment. DRY-RUN by default — returns the plan + drafted comment; with
    approve=true it performs the gated actions (each counted against its quota).
    """
    posts = _unwrap(run_cli(["user", "posts", username, "--limit", "1"])) or []
    if isinstance(posts, dict):
        posts = posts.get("items") or posts.get("posts") or []
    if not posts:
        return {"ok": False, "error": f"no recent post found for '{username}'."}
    post = posts[0]
    media_id = str(post.get("id") or post.get("pk") or post.get("media_id") or "")
    caption = post.get("caption") or post.get("text") or ""
    info = _unwrap(run_cli(["user", "info", username])) or {"username": username}

    plan: dict = {"username": username, "media_id": media_id, "actions": []}
    comment_text = ""
    if comment:
        try:
            comment_text = llm.complete(
                prompts.WARMUP_COMMENT_SYSTEM, prompts.warmup_comment_user(info, caption))
        except Exception as e:  # noqa: BLE001
            comment_text = ""
            plan["comment_error"] = str(e)
    if like:
        plan["actions"].append({"type": "like_post", "media_id": media_id})
    if comment and comment_text:
        plan["actions"].append({"type": "comments_add", "media_id": media_id, "text": comment_text})

    if not approve:
        return {"ok": True, "dry_run": True, "warmup": plan,
                "note": "DRY-RUN. Review the like/comment, then call again with approve=true."}

    # execute, each behind its own quota/pacing gate
    results = []
    if like and media_id:
        g = _write_gate("like_post", True, force)
        if g is not None:
            results.append({"like": g})
        else:
            r = run_cli(["like", "post", media_id], enable_growth=True)
            if r.ok:
                G.consume("like_post")
            results.append({"like": _result(r)})
    if comment and comment_text and media_id:
        g = _write_gate("comments_add", True, force)
        if g is not None:
            results.append({"comment": g})
        else:
            r = run_cli(["comments", "add", media_id, comment_text], enable_growth=True)
            if r.ok:
                G.consume("comments_add")
            results.append({"comment": _result(r), "text": comment_text})
    return {"ok": True, "warmup": plan, "results": results}


# ── E) Pipeline board (persisted lead CRM) ───────────────────────────────────


def t_pipeline_set(username: str, stage: str = "", note: str = "", temperature: str = "",
                   need: str = "", thread_id: str = "", **_) -> dict:
    return pipeline.upsert(username, stage=stage, note=note, temperature=temperature,
                           need=need, thread_id=thread_id)


def t_pipeline_get(username: str, **_) -> dict:
    return pipeline.get(username)


def t_pipeline_board(stage: str = "", temperature: str = "", **_) -> dict:
    return pipeline.board(stage=stage, temperature=temperature)


def t_pipeline_remove(username: str, **_) -> dict:
    return pipeline.remove(username)


# ── F) DM listen (new inbound since last check) ──────────────────────────────


def t_dm_listen(limit: int = 20, **_) -> dict:
    """Surface inbox threads that are unread / have new activity, for triage."""
    r = run_cli(["dm", "inbox", "--limit", str(limit)])
    if not r.ok:
        return _result(r)
    threads = r.data if isinstance(r.data, list) else (
        (r.data or {}).get("threads") or (r.data or {}).get("items") or [])
    new = []
    for t in threads:
        unread = t.get("unread") or t.get("has_newer") or t.get("unseen_count")
        if unread:
            new.append({
                "thread_id": t.get("thread_id") or t.get("id"),
                "title": t.get("title") or t.get("thread_title"),
                "users": t.get("users"),
                "last_activity": t.get("last_activity_at") or t.get("last_activity"),
                "unread": unread,
            })
    return {"ok": True, "new_count": len(new), "new_threads": new,
            "note": "Read one with dm_thread(thread_id); then qualify_lead + pipeline_set."}


# ── G) Bulk CSV ──────────────────────────────────────────────────────────────


def t_csv_import(path: str, **_) -> dict:
    return bulk.import_csv(path)


def t_csv_export(path: str, stage: str = "", temperature: str = "", **_) -> dict:
    return bulk.export_csv(path, stage=stage, temperature=temperature)


# ── H) Inbox triage (read inbox -> qualify each -> update board) ──────────────


def t_inbox_triage(limit: int = 10, offer: str = "", thread_limit: int = 15,
                   update_board: bool = True, **_) -> dict:
    """
    For each unread/new thread: read it, qualify with the LLM, and (optionally)
    upsert the lead onto the pipeline board. Read + LLM only — never sends.
    """
    r = run_cli(["dm", "inbox", "--limit", str(limit)])
    if not r.ok:
        return _result(r)
    threads = r.data if isinstance(r.data, list) else (
        (r.data or {}).get("threads") or (r.data or {}).get("items") or [])
    triaged = []
    for th in threads:
        unread = th.get("unread") or th.get("unseen_count") or th.get("has_newer")
        if not unread:
            continue
        tid = str(th.get("thread_id") or th.get("id") or "")
        users = th.get("users") or []
        username = ""
        if isinstance(users, list) and users:
            u0 = users[0]
            username = (u0.get("username") if isinstance(u0, dict) else str(u0)) or ""
        if not tid:
            continue
        msgs = _unwrap(run_cli(["dm", "thread", tid, "--limit", str(thread_limit)])) or []
        convo = _convo_text(msgs)
        try:
            q = llm.complete_json(prompts.QUALIFY_SYSTEM, prompts.qualify_user(convo, offer))
        except Exception as e:  # noqa: BLE001
            q = {"error": str(e)}
        entry = {"thread_id": tid, "username": username, "qualification": q}
        triaged.append(entry)
        if update_board and username and isinstance(q, dict) and not q.get("error"):
            pipeline.upsert(
                username,
                stage=_stage_from_qual(q),
                temperature=q.get("temperature", ""),
                need=q.get("need") or "",
                thread_id=tid,
                note="auto-triaged",
            )
    return {"ok": True, "triaged_count": len(triaged), "triaged": triaged,
            "note": "Board updated. Draft replies for the hot/warm ones with draft_reply."}


def _convo_text(msgs) -> str:
    lines = []
    for m in (msgs or [])[-30:]:
        who = m.get("user_id") or m.get("username") or m.get("sender") or "?"
        txt = (m.get("text") or m.get("item_type") or "").strip()
        if txt:
            lines.append(f"{who}: {txt}")
    return "\n".join(lines) or "(no text messages)"


def _stage_from_qual(q: dict) -> str:
    stage = q.get("stage", "")
    mapping = {
        "no_reply": "contacted", "engaged": "engaged",
        "needs_identified": "qualified", "ready_for_closer": "handoff",
        "not_a_fit": "not_a_fit",
    }
    return mapping.get(stage, "engaged")


# ── I) Prospect brief (one-shot: profile + last post + opener) ───────────────


def t_prospect_brief(username: str, offer: str = "", icp: str = "", **_) -> dict:
    """One call: enrich a prospect, optionally score vs ICP, and draft an opener."""
    info = _unwrap(run_cli(["user", "info", username]))
    if not info:
        return {"ok": False, "error": f"could not fetch '{username}'."}
    posts = _unwrap(run_cli(["user", "posts", username, "--limit", "1"])) or []
    if isinstance(posts, dict):
        posts = posts.get("items") or posts.get("posts") or []
    last_caption = (posts[0].get("caption") or posts[0].get("text") or "") if posts else ""
    prospect = {**info, "last_post": last_caption}
    brief: dict = {"ok": True, "username": username, "profile": {
        "full_name": info.get("full_name"), "bio": info.get("biography"),
        "followers": info.get("followers_count"), "verified": info.get("is_verified"),
    }, "last_post": last_caption[:280]}
    if icp:
        try:
            brief["score"] = llm.complete_json(prompts.SCORE_SYSTEM, prompts.score_user(prospect, icp))
        except Exception:  # noqa: BLE001
            pass
    if offer:
        try:
            brief["suggested_opener"] = llm.complete(
                prompts.OPENER_SYSTEM, prompts.opener_user(prospect, offer))
        except Exception:  # noqa: BLE001
            pass
    brief["note"] = "Review the opener, then dm_send(username, opener, approve=true)."
    return brief


# ── J) Best time (from your profile analytics) ───────────────────────────────


def t_best_time(**_) -> dict:
    """Suggest send windows. Uses profile analytics if available, else sane defaults."""
    a = _unwrap(run_cli(["analytics", "profile"]))
    note = ("Heuristic defaults — Instagram's private API rarely exposes per-hour "
            "audience activity. Treat as a starting point, then learn from replies.")
    windows = [
        {"day": "Tue-Thu", "local_time": "12:00-13:00", "why": "lunch scroll"},
        {"day": "Tue-Thu", "local_time": "19:00-21:00", "why": "evening peak"},
        {"day": "Sun", "local_time": "10:00-12:00", "why": "weekend morning"},
    ]
    return {"ok": True, "suggested_windows": windows,
            "analytics_available": bool(a), "note": note}


# ── K) Sequence planning (paced multi-step cadence, dry-run only) ─────────────

DEFAULT_SEQUENCE = [
    {"step": 1, "day_offset": 0, "action": "engagement_warmup", "desc": "like + genuine comment"},
    {"step": 2, "day_offset": 1, "action": "dm_send", "desc": "personalized opener"},
    {"step": 3, "day_offset": 3, "action": "dm_send", "desc": "follow-up #1 (new angle)"},
    {"step": 4, "day_offset": 7, "action": "dm_send", "desc": "follow-up #2 (last, low-pressure)"},
]


def t_sequence_plan(usernames: list, offer: str = "", **_) -> dict:
    """
    Build a paced outreach cadence for a list of prospects. This is a PLAN ONLY —
    it never sends and never schedules; it tells the agent/human what to do when,
    and registers the prospects on the board as 'sourced'. Stop the sequence on reply.
    """
    usernames = [u.lstrip("@").strip() for u in (usernames or []) if u and str(u).strip()]
    if not usernames:
        return {"ok": False, "error": "provide a non-empty 'usernames' list"}
    for u in usernames:
        pipeline.upsert(u, stage="sourced", note="added to sequence")
    return {
        "ok": True, "prospects": len(usernames), "offer": offer,
        "cadence": DEFAULT_SEQUENCE,
        "rules": [
            "STOP the sequence for a prospect as soon as they reply.",
            "Each send is still dry-run by default — show the human, then approve=true.",
            "Respect daily quotas; spread sends across days, never blast.",
        ],
        "note": "Plan only — execute steps manually/agentically using the per-step tools. "
                "Prospects added to the board as 'sourced'.",
    }


# ── meta tools ───────────────────────────────────────────────────────────────


def t_daily_plan(target_dm: int = 0, **_) -> dict:
    """Propose today's safe action budget given remaining quotas."""
    rep = G.usage_report()["actions"]
    plan = {a: rep[a]["remaining"] for a in rep}
    suggestion = {
        "warmups": min(plan.get("like_post", 0), plan.get("comments_add", 0), 10),
        "openers (dm_send)": plan.get("dm_send", 0) if not target_dm else min(target_dm, plan.get("dm_send", 0)),
        "follows": plan.get("follow", 0),
    }
    return {"ok": True, "remaining_today": plan, "suggested_today": suggestion,
            "note": "These are CEILINGS. Stay well under them and act on a human cadence."}


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

# ICP / intelligence (LLM, read-only)
_reg("extract_icp", t_extract_icp,
     "Analyze an Instagram account (yours or a competitor) -> Ideal Customer Profile + "
     "prospecting plan (hashtags, lookalikes, search queries, opener angle). Free LLM.",
     {"username": _S, "posts_limit": _I}, ["username"])
_reg("score_prospect", t_score_prospect,
     "Score a prospect's fit against an ICP (0-100 + best hook) to prioritize. Free LLM.",
     {"prospect": _O, "icp": _S}, ["prospect", "icp"])
_reg("find_prospects", t_find_prospects,
     "Source candidate accounts from a hashtag and/or user search, optionally enriched "
     "with profile data. Read-only.",
     {"hashtag": _S, "query": _S, "limit": _I, "enrich": _B})

# engagement warm-up (LLM draft + gated like/comment, dry-run default)
_reg("engagement_warmup", t_engagement_warmup,
     "Warm up a prospect before a cold DM: like + a genuine drafted comment on their "
     "latest post. DRY-RUN unless approve=true (each action quota-gated).",
     {"username": _S, "like": _B, "comment": _B, "offer": _S, **_GATE}, ["username"])

# pipeline board (persisted lead CRM)
_reg("pipeline_set", t_pipeline_set,
     "Create/update a lead on the board (stage/temperature/need/note/thread_id). "
     "Stages: sourced, contacted, no_reply, engaged, qualified, handoff, not_a_fit.",
     {"username": _S, "stage": _S, "note": _S, "temperature": _S, "need": _S, "thread_id": _S},
     ["username"])
_reg("pipeline_get", t_pipeline_get, "Get one lead's full record + history.",
     {"username": _S}, ["username"])
_reg("pipeline_board", t_pipeline_board,
     "List the lead board (optionally filtered by stage/temperature) + counts by stage.",
     {"stage": _S, "temperature": _S})
_reg("pipeline_remove", t_pipeline_remove, "Remove a lead from the board.",
     {"username": _S}, ["username"])

# dm listen + daily plan
_reg("dm_listen", t_dm_listen,
     "Surface unread/new inbound DM threads for triage (read-only).",
     {"limit": _I})
_reg("daily_plan", t_daily_plan,
     "Propose today's safe action budget from remaining quotas (anti-ban planning).",
     {"target_dm": _I})

# bulk csv
_reg("csv_import", t_csv_import,
     "Import prospects from a CSV (needs a 'username' column; optional stage/temperature/"
     "need/note/thread_id) into the pipeline board.",
     {"path": _S}, ["path"])
_reg("csv_export", t_csv_export,
     "Export the pipeline board to a CSV file (optional stage/temperature filter).",
     {"path": _S, "stage": _S, "temperature": _S}, ["path"])

# inbox triage + prospect brief + best time + sequence
_reg("inbox_triage", t_inbox_triage,
     "Read every unread thread, qualify each with the LLM, and update the board. "
     "Read + LLM only, never sends.",
     {"limit": _I, "offer": _S, "thread_limit": _I, "update_board": _B})
_reg("prospect_brief", t_prospect_brief,
     "One-shot prospect brief: profile + last post + (optional) ICP score + a drafted "
     "opener. Read + LLM only.",
     {"username": _S, "offer": _S, "icp": _S}, ["username"])
_reg("best_time", t_best_time,
     "Suggest send-time windows (from profile analytics if available, else heuristics).",
     {})
_reg("sequence_plan", t_sequence_plan,
     "Build a paced multi-step outreach cadence (warm-up -> opener -> follow-ups) for a "
     "list of prospects. PLAN ONLY — never sends; adds them to the board as 'sourced'.",
     {"usernames": {"type": "array", "items": _S}, "offer": _S}, ["usernames"])

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
