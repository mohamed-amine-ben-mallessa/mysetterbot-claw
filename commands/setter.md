---
description: Run an Instagram setting/outreach loop with MySetterBot Claw (dry-run by default).
---

You have the **mysetterbot-claw** MCP available. Help the user do Instagram setting
(opening + qualifying conversations) — never spammy mass-DMing.

Workflow:
1. **Source** with `hashtag_recent` / `user_search` / `user_posts` if the user gives a niche.
2. **Enrich** each prospect with `user_info` (bio, counts) for personalization.
3. **Draft** the message with `draft_opener` (or `draft_followup` / `draft_reply`).
4. **Show the user the draft** and let them edit it.
5. Only after explicit approval, send with `dm_send(..., approve=true)`.
6. When a reply comes in, `dm_thread` to read it, then `qualify_lead` to classify.

Rules:
- Default to **dry-run**. Never pass `approve=true` until the user has seen and OK'd the text.
- Respect quotas — call `usage` if you're unsure how much room is left today.
- One personalized message per prospect. No templates blasted at a list.
- Match the prospect's language.

$ARGUMENTS
