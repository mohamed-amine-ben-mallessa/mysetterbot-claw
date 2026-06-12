# MySetterBot Claw MCP — tool reference (42 tools)

All tools return a JSON dict. Write/growth tools are **dry-run by default**: they
return a preview unless you pass `approve: true`.

## 🔎 Read / prospect (safe, no gate)

| tool | args | returns |
|---|---|---|
| `dm_inbox` | `limit`, `unread_only` | inbox threads |
| `dm_thread` | `thread_id`, `limit` | messages (handles voice/media safely) |
| `dm_search` | `query` | matching threads |
| `user_info` | `username` | profile (bio, counts, verified) |
| `user_search` | `query` | users |
| `user_posts` | `username`, `limit` | recent posts |
| `hashtag_recent` / `hashtag_top` | `tag`, `limit` | posts |
| `comments_list` | `media_id`, `limit` | comments |
| `followers_list` / `following_list` | `limit` | accounts |
| `analytics_profile` | — | your profile metrics |
| `analytics_post` | `media_id` (or `"latest"`) | post metrics |

## 🧠 Intelligence (free LLM, read-only)

| tool | args | returns |
|---|---|---|
| `extract_icp` | `username`, `posts_limit` | Ideal Customer Profile + prospecting plan (hashtags, lookalikes, queries, opener angle) |
| `find_prospects` | `hashtag`, `query`, `limit`, `enrich` | candidate accounts, enriched |
| `score_prospect` | `prospect`, `icp` | `{score 0-100, fit, reasons, best_hook}` |
| `prospect_brief` | `username`, `offer`, `icp` | profile + last post + score + drafted opener |

## ✍️ Setter copy (free LLM, never sends)

| tool | args | returns |
|---|---|---|
| `draft_opener` | `prospect`, `offer` | a personalized cold opener |
| `draft_followup` | `prospect`, `offer`, `previous`, `days_since` | a low-pressure follow-up |
| `draft_reply` | `prospect`, `offer`, `conversation` | the next qualifying reply |
| `qualify_lead` | `conversation`, `offer` | `{temperature, stage, need, next_action, confidence}` |

## 🔥 / ✉️ Write & growth (gated, dry-run default — pass `approve: true` to send)

| tool | args | notes |
|---|---|---|
| `dm_send` | `user`, `message`, `approve`, `force` | text DM |
| `dm_send_media` | `user`, `media`, `approve` | media DM |
| `comments_add` | `media_id`, `text`, `approve` | growth-gated |
| `comments_reply` | `comment_id`, `text`, `approve` | growth-gated |
| `follow` / `unfollow` | `user`, `approve` | growth-gated |
| `like_post` | `media_id`, `approve` | growth-gated |
| `engagement_warmup` | `username`, `like`, `comment`, `offer`, `approve` | like + drafted genuine comment on latest post |

## 📋 Pipeline (persisted lead CRM)

State: `~/.mysetterbot-claw/pipeline.json`. Stages: `sourced → contacted →
no_reply → engaged → qualified → handoff → not_a_fit`.

| tool | args |
|---|---|
| `pipeline_set` | `username`, `stage`, `temperature`, `need`, `note`, `thread_id` |
| `pipeline_get` | `username` |
| `pipeline_board` | `stage`, `temperature` (filters) |
| `pipeline_remove` | `username` |
| `csv_import` | `path` (CSV with a `username` column) |
| `csv_export` | `path`, `stage`, `temperature` |

## 🔭 Triage & planning

| tool | args | notes |
|---|---|---|
| `inbox_triage` | `limit`, `offer`, `thread_limit`, `update_board` | qualify every unread → board (LLM, no send) |
| `sequence_plan` | `usernames[]`, `offer` | paced warm-up→opener→follow-ups plan (no send) |
| `dm_listen` | `limit` | unread/new inbound |
| `daily_plan` | `target_dm` | safe action budget from remaining quotas |
| `best_time` | — | send-window suggestions |

## 🛡️ Meta

| tool | returns |
|---|---|
| `usage` | today's action usage vs quotas |
| `doctor` | CLI/session health |

## Quotas (defaults, env-overridable `MSBC_QUOTA_*`)

`dm_send=40` · `follow=20` · `unfollow=20` · `like_post=60` · `comments_add=20` ·
`comments_reply=30`. Min cooldown between writes: 25s. UTC daily reset.
