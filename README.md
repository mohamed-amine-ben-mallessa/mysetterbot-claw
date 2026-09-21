<h1 align="center">🦅 MySetterBot Claw</h1>

<p align="center">
  <b>Instagram outreach your agent can actually run — it writes the opener, you approve, it sends.</b><br>
  42 MCP tools, a free LLM that personalizes every message, and anti-ban guardrails that are <i>on by default</i>.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/MCP-server-6E59F7" alt="MCP">
  <img src="https://img.shields.io/badge/42-tools-1f9d55" alt="42 tools">
  <img src="https://img.shields.io/badge/LLM-OpenRouter%20free-orange" alt="Free LLM">
  <img src="https://img.shields.io/badge/dry--run-by%20default-E1306C" alt="Dry-run default">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="Zero deps">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="MIT">
</p>

**Claude Code:**

```
/plugin marketplace add mohamed-amine-ben-mallessa/mysetterbot-claw
/plugin install mysetterbot-claw
```

**Codex, Cursor, Copilot, Gemini CLI, or any of 50+ [Agent Skills](https://agentskills.io) hosts:**

```
npx skills add mohamed-amine-ben-mallessa/mysetterbot-claw -g
```

Full setup — including the CLI action layer and the keychain login — in [Install](#install).

---

> **A "setter" opens conversations and qualifies leads — it doesn't pitch and it doesn't close.**
> This MCP gives your agent a setter's toolkit: find prospects, write a genuinely
> personalized opener with a **free** LLM, read the reply, qualify it — and never
> send a thing until a human says go.

## Why this exists

Instagram "automation" comes in two flavors, and both are bad: brittle browser macros that
break weekly, or paid SaaS that blasts the same template at 500 people until the account
gets banned.

The interesting job isn't *sending*. It's **reading a stranger's profile and writing one
message worth replying to** — and that's exactly what an LLM is good at. So: the model
writes, the guardrails pace, and a human presses send.

| Typical IG automation | **MySetterBot Claw** |
|---|---|
| Mass-DMs the same template | **Per-prospect** openers from their bio/posts (free LLM) |
| Fire-and-forget → bans | **Dry-run by default** — shows the draft, you approve, *then* it sends |
| No rate awareness | **Daily quotas + pacing** baked in (per-action, with cooldowns) |
| Paid SaaS, closed | **MIT, zero deps**, runs anywhere an agent runs |
| "Send" is the only verb | **Setter workflow**: source → personalize → reply → **qualify** |

## The two halves

| | Repo | Role |
|---|---|---|
| 🦅 | **mysetterbot-claw** (this) | MCP server: 42 agent tools + free-LLM copywriting + anti-ban guardrails |
| ⚙️ | [mysetterbot-claw-cli](https://github.com/mohamed-amine-ben-mallessa/mysetterbot-claw-cli) | The action layer: a JSON-clean Instagram CLI that owns the keychain session |

The MCP **never touches credentials** — every action is delegated to the CLI, which keeps
the session in your OS keychain. The MCP's job is orchestration, copywriting, and safety.

## The loop (how an agent uses it)

```text
1. hashtag_recent("frenchstartup")        →  candidate posts/users
2. user_info("@prospect") + user_posts    →  context
3. draft_opener(prospect, offer)           →  a personalized first message  ✍️ (free LLM)
4. dm_send(user, message)                  →  DRY-RUN: returns the preview   🛡️
5. dm_send(user, message, approve=true)    →  actually sends (quota-checked) ✅
6. ...they reply...
7. dm_thread(thread_id)                     →  read it (handles voice/media safely)
8. qualify_lead(conversation)               →  {temperature, stage, need, next_action}
9. draft_reply(...) → dm_send(approve=true) →  keep it moving
```

The LLM only ever **writes text**. The decision to send is the human's.

## The 42 tools

**🔎 Read / prospect** — `dm_inbox` · `dm_thread` · `dm_search` · `user_info` ·
`user_search` · `user_posts` · `hashtag_recent` · `hashtag_top` · `comments_list` ·
`followers_list` · `following_list` · `analytics_profile` · `analytics_post`

**🧠 Intelligence (free LLM, read-only)** — `extract_icp` (account → Ideal Customer
Profile + prospecting plan) · `find_prospects` (source from hashtag/search, enriched) ·
`score_prospect` (0-100 ICP-fit + best hook)

**✍️ Setter copy (free LLM, never sends)** — `draft_opener` · `draft_followup` ·
`draft_reply` · `qualify_lead`

**🔥 Warm-up (gated, dry-run default)** — `engagement_warmup` (like + a genuine
drafted comment on their latest post, *before* any cold DM)

**✉️ Write / growth (gated, dry-run default)** — `dm_send` · `dm_send_media` ·
`comments_add` · `comments_reply` · `follow` · `unfollow` · `like_post`

**📋 Pipeline (persisted lead CRM)** — `pipeline_set` · `pipeline_get` ·
`pipeline_board` · `pipeline_remove` · `csv_import` · `csv_export` (stages: sourced
→ contacted → no_reply → engaged → qualified → handoff → not_a_fit)

**🔭 Triage & planning** — `inbox_triage` (qualify every unread → board) ·
`prospect_brief` (one-shot profile + score + opener) · `sequence_plan` (paced
cadence) · `dm_listen` (new inbound) · `daily_plan` (safe budget) · `best_time`

**🛡️ Meta** — `usage` (quota report) · `doctor` (session health)

Every tool, argument, return shape and quota: [`ref/TOOLS.md`](ref/TOOLS.md).

## Install

| Surface | Install | Updates |
|---|---|---|
| **Claude Code** (recommended) | `/plugin marketplace add mohamed-amine-ben-mallessa/mysetterbot-claw` then `/plugin install mysetterbot-claw` | `claude plugin update mysetterbot-claw` |
| **Codex, Cursor, Copilot, Gemini CLI, or any of 50+ [Agent Skills](https://agentskills.io) hosts** | `npx skills add mohamed-amine-ben-mallessa/mysetterbot-claw -g` | `npx skills update instagram-setter -g` |
| **Any MCP client** | `pip install -e .` + the JSON config below | `git pull` |

Then, once, the action layer and the login:

```bash
pip install -e ../mysetterbot-claw-cli   # or: pip install clinstagram
msbc auth login --username <you>          # session goes to your OS keychain, never a file
```

### Wire it into an MCP client

```json
{
  "mcpServers": {
    "mysetterbot-claw": {
      "command": "python",
      "args": ["-m", "mysetterbot_claw"],
      "env": { "OPENROUTER_API_KEY": "sk-or-..." }
    }
  }
}
```

`OPENROUTER_API_KEY` powers the free-model cascade (Llama 3.3 70B → Qwen3 → Gemma →
gpt-oss → Nemotron → Hermes). Override the list with `MSBC_MODELS`. **The copywriting
costs nothing.**

## 🛡️ Safety model (read this)

This tool can get an Instagram account **action-blocked or banned** if abused.
The guardrails are on by default; keep them on.

- **Dry-run default** — `dm_send`, `follow`, `like_post`, `comments_*`, etc. return a
  *preview* unless you pass `approve=true`. Show the human, then approve.
- **Daily quotas** (env-overridable): `dm_send=40`, `follow=20`, `like_post=60`,
  `comments_add=20`, … Hit the cap → blocked until tomorrow (UTC).
- **Pacing** — a minimum cooldown between writes (no bursts). `usage` shows where you stand.
- **Growth gate** — follow/like/comment go through the CLI's `--enable-growth-actions`
  *and* the quota guard. Two locks, on purpose.
- **Be a human.** Personalized, sparse, warm. One thoughtful DM ≠ a spray of templates.
  The first is outreach; the second is how accounts die.

Tune quotas with env vars, e.g. `MSBC_QUOTA_DM_SEND=15`.

Use this within Instagram's terms of service, and within the law that applies to you
(GDPR, CAN-SPAM and friends cover unsolicited commercial messaging).

## Try it without sending anything

```bash
python scripts/demo_setter.py <a_username> "<your one-line offer>"
```

A guided, **dry-run-only** walkthrough of the whole loop. Nothing leaves your machine.

## Skill, scripts & docs

```
skills/instagram-setter/SKILL.md   portable agent skill (the safe setter loop)
scripts/demo_setter.py             guided DRY-RUN-ONLY end-to-end walkthrough
ref/TOOLS.md                       all 42 tools, args, returns, quotas
ref/WORKFLOW.md                    the step-by-step setter workflow
```

## Roadmap (ideas, not yet built)

- `sequence_run` — actually *execute* a `sequence_plan` step-by-step (still gated)
- `webhook_out` — POST board changes to n8n / a CRM
- `dedupe` — merge/clean duplicate leads
- `ab_openers` — generate N opener variants and track which gets replies

PRs and ideas welcome.

## Credits

Action layer forked from **[clinstagram](https://github.com/199-biotechnologies/clinstagram)**
(MIT). Not affiliated with Instagram / Meta. "Instagram" is a trademark of its owner.

## License

MIT — see [LICENSE](LICENSE).

---

<p align="center">
  <sub>Built by <a href="https://github.com/mohamed-amine-ben-mallessa">Mohamed Amine Ben Mallessa</a> · ⭐ star it if it got you a reply instead of a ban</sub>
</p>
