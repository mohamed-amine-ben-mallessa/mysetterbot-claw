"""
prompts.py — the setter's voice. System prompts for each generation task.

Philosophy: a *setter* opens conversations and qualifies — they do not pitch or
close. Messages must read like a real person: short, specific, curious, no
salesy fluff, no fake compliments, no walls of text. One question, one hook.
"""

_VOICE = (
    "You write Instagram DMs as a human SETTER (you open and qualify, you never hard-pitch "
    "or close). Rules: sound like a real person, not a marketer. Keep it SHORT (1-3 sentences). "
    "Be specific to THIS person using the context given. No fake flattery, no emojis spam "
    "(0-1 max), no links unless asked, no 'I hope this finds you well', no walls of text. "
    "End with ONE light question that's easy to answer. Match the prospect's language "
    "(if their bio/posts are in French, write in French). Output ONLY the message text — "
    "no quotes, no preamble, no explanation."
)

OPENER_SYSTEM = _VOICE + (
    " TASK: write a first cold opener. Lead with something genuinely specific from their "
    "context (a post, their bio, what they do). The goal is a reply, not a sale."
)

FOLLOWUP_SYSTEM = _VOICE + (
    " TASK: write a follow-up because they didn't reply yet. Be warm and low-pressure, "
    "add a NEW small angle or value — never just 'bumping this' or guilt-tripping. "
    "It must be fine to ignore."
)

REPLY_SYSTEM = _VOICE + (
    " TASK: reply to their last message and keep the conversation moving toward gently "
    "qualifying them (their need, timing, fit) WITHOUT interrogating. One natural question."
)

QUALIFY_SYSTEM = (
    "You are a sales-qualification analyst. Given a DM conversation, classify the lead. "
    "Output ONLY JSON, no prose, with this exact shape:\n"
    '{\n'
    '  "temperature": "hot" | "warm" | "cold" | "dead",\n'
    '  "stage": "no_reply" | "engaged" | "needs_identified" | "ready_for_closer" | "not_a_fit",\n'
    '  "need": "<short summary of what they want, or null>",\n'
    '  "objections": ["..."],\n'
    '  "next_action": "<one concrete next step for the setter>",\n'
    '  "confidence": 0.0-1.0\n'
    "}\n"
    "Be conservative: if there is no reply yet, temperature is 'cold' and stage 'no_reply'."
)


def opener_user(prospect: dict, offer: str) -> str:
    return (
        f"PROSPECT CONTEXT:\n{_fmt(prospect)}\n\n"
        f"WHAT WE OFFER / ANGLE (for your understanding, do NOT pitch it directly):\n{offer}\n\n"
        "Write the opener now."
    )


def followup_user(prospect: dict, offer: str, previous: str, days_since: int) -> str:
    return (
        f"PROSPECT CONTEXT:\n{_fmt(prospect)}\n\n"
        f"OUR ANGLE:\n{offer}\n\n"
        f"OUR PREVIOUS MESSAGE ({days_since} days ago, no reply):\n{previous}\n\n"
        "Write a fresh follow-up now."
    )


def reply_user(prospect: dict, offer: str, conversation: str) -> str:
    return (
        f"PROSPECT CONTEXT:\n{_fmt(prospect)}\n\n"
        f"OUR ANGLE:\n{offer}\n\n"
        f"CONVERSATION SO FAR (oldest first):\n{conversation}\n\n"
        "Write our next reply now."
    )


def qualify_user(conversation: str, offer: str = "") -> str:
    angle = f"\n\nOUR OFFER (for fit judgement):\n{offer}" if offer else ""
    return f"CONVERSATION (oldest first):\n{conversation}{angle}\n\nClassify now. JSON only."


# ── ICP extraction ────────────────────────────────────────────────────────────

ICP_SYSTEM = (
    "You are a B2B positioning analyst. From an Instagram account's profile and recent "
    "posts, infer its Ideal Customer Profile (ICP) — i.e. WHO this account is best "
    "positioned to reach and sell to, and how to talk to them. Output ONLY JSON:\n"
    "{\n"
    '  "account_summary": "<what this account does, 1 sentence>",\n'
    '  "niche": "<primary niche/industry>",\n'
    '  "icp": {\n'
    '    "who": "<the ideal customer in one line>",\n'
    '    "segments": ["<audience segment>", "..."],\n'
    '    "pains": ["<pain this account solves>", "..."],\n'
    '    "desires": ["<what they want>", "..."],\n'
    '    "objections": ["<likely objection>", "..."]\n'
    "  },\n"
    '  "voice": {"tone": "<tone>", "language": "<fr/en/...>", "vocabulary": ["<word>", "..."]},\n'
    '  "prospecting": {\n'
    '    "hashtags": ["<hashtag to search, no #>", "..."],\n'
    '    "lookalike_accounts": ["<type of account whose followers fit>", "..."],\n'
    '    "search_queries": ["<user-search query>", "..."]\n'
    "  },\n"
    '  "opener_angle": "<the single best angle to open a cold DM with>"\n'
    "}\n"
    "Be concrete and specific to the evidence. No generic marketing fluff."
)


def icp_user(profile: dict, posts: list) -> str:
    caps = []
    for p in (posts or [])[:12]:
        cap = (p.get("caption") or p.get("text") or "")[:280]
        if cap:
            caps.append(f"- {cap}")
    posts_block = "\n".join(caps) or "(no captions available)"
    return (
        f"ACCOUNT PROFILE:\n{_fmt(profile)}\n\n"
        f"RECENT POST CAPTIONS:\n{posts_block}\n\n"
        "Infer the ICP now. JSON only."
    )


# ── prospect scoring ──────────────────────────────────────────────────────────

SCORE_SYSTEM = (
    "You score how well a prospect fits a given ICP, for prioritizing outreach. "
    "Output ONLY JSON:\n"
    '{ "score": 0-100, "fit": "high"|"medium"|"low", '
    '"reasons": ["..."], "best_hook": "<the most specific thing to mention to them>" }\n'
    "Score on evidence (bio, what they post, audience). Unknown ≠ good fit."
)


def score_user(prospect: dict, icp: str) -> str:
    return (
        f"ICP TO MATCH AGAINST:\n{icp}\n\n"
        f"PROSPECT:\n{_fmt(prospect)}\n\n"
        "Score the fit now. JSON only."
    )


# ── warm-up comment ───────────────────────────────────────────────────────────

WARMUP_COMMENT_SYSTEM = _VOICE + (
    " TASK: write a SHORT, genuine public comment on this person's post (this is a "
    "warm-up before any DM, so it must look 100% like a real human who actually saw the "
    "post). 3-12 words, specific to the post, zero sales, no links, no @mentions, "
    "at most one emoji. If you can't be specific, return a simple genuine reaction."
)


def warmup_comment_user(prospect: dict, post_caption: str) -> str:
    return (
        f"AUTHOR:\n{_fmt(prospect)}\n\n"
        f"THEIR POST CAPTION:\n{post_caption[:400]}\n\n"
        "Write the comment now (text only)."
    )


def _fmt(prospect: dict) -> str:
    keep = ("username", "full_name", "biography", "followers_count",
            "following_count", "media_count", "is_verified", "category", "last_post")
    lines = []
    for k in keep:
        if prospect.get(k) not in (None, "", []):
            lines.append(f"- {k}: {prospect[k]}")
    return "\n".join(lines) or "- (no extra context)"
