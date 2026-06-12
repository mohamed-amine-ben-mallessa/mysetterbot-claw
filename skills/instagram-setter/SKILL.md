---
name: instagram-setter
description: >
  Run Instagram outreach/setting safely: find and qualify prospects, write
  personalized openers/follow-ups/replies with a free LLM, warm up, send (with
  approval), and track leads in a pipeline. Use when the user wants to do Instagram
  outreach, DM prospects, find leads, qualify conversations, run a setter/SDR
  workflow, or manage an outreach pipeline. Uses the mysetterbot-claw MCP. Keywords:
  instagram outreach, setter, SDR, cold DM, lead generation, prospecting, ICP,
  follow-up, qualify lead, pipeline, dry-run, mysetterbot.
license: MIT
---

# Instagram Setter (MySetterBot Claw)

Drive the **mysetterbot-claw MCP** (42 tools) to do real setting: open
conversations and qualify leads — never spam. The LLM writes, you approve, it sends.

## The rule that matters
Everything that sends is **dry-run by default**. Always:
1. generate the message with a `draft_*` tool,
2. **show the human the draft**,
3. only then call the send tool with `approve: true`.
Never pass `approve: true` to a message the user hasn't seen.

## The loop
```
extract_icp(username)            → who to target + hashtags + opener angle
find_prospects(hashtag=…)        → enriched candidates
prospect_brief(username, offer)  → profile + last post + score + drafted opener
engagement_warmup(username)      → like + genuine comment (dry-run → approve)
draft_opener → dm_send(approve=true)
dm_listen → dm_thread → qualify_lead → draft_reply → dm_send(approve=true)
pipeline_set(stage=…)            → track the lead
```
Full detail: [ref/WORKFLOW.md](../../ref/WORKFLOW.md). Tool list:
[ref/TOOLS.md](../../ref/TOOLS.md).

## Safety (non-negotiable)
- One **personalized** message per prospect. No templates blasted at a list.
- Respect quotas — call `usage` / `daily_plan` if unsure (dm_send 40/day, follow 20…).
- Stop on any rate-limit. Spread actions across hours/days.
- Match the prospect's language. Short, specific, one easy question.

## Pipeline & bulk
- `pipeline_board` for the funnel; `pipeline_set` to advance a lead through
  sourced → contacted → engaged → qualified → handoff.
- `csv_import` / `csv_export` for bulk lists.
- `inbox_triage` to auto-qualify every unread thread and update the board.

## Helper
[scripts/demo_setter.py](../../scripts/demo_setter.py) — a guided, dry-run-only
end-to-end run you can read to see the sequence.
