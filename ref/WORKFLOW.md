# The setter workflow

A *setter* opens conversations and qualifies leads — they don't pitch or close.
This is the loop the tools are designed for. The LLM **writes**, the code **acts**,
the human **approves**.

## 0. Define the offer (once)
Keep a one-line "angle" you can pass as `offer` to the copy tools. It's context for
the LLM, not a script to paste.

## 1. Understand who to target
```
extract_icp(username="<your_account_or_a_competitor>")
  → niche, ICP (who/pains/desires/objections), voice, and a prospecting plan:
    hashtags, lookalike account types, search queries, opener angle
```

## 2. Source prospects
```
find_prospects(hashtag="<from ICP>", query="<from ICP>", enrich=true)
  → enriched candidate accounts
```

## 3. Prioritize
```
score_prospect(prospect=<one candidate>, icp=<the ICP json/text>)
  → 0-100 fit + best_hook    # work the high-fit ones first
```
Or get everything in one call per prospect:
```
prospect_brief(username, offer, icp)  → profile + last post + score + drafted opener
```

## 4. Warm up (optional but more human)
```
engagement_warmup(username, offer)          # DRY-RUN: shows the like + drafted comment
engagement_warmup(username, offer, approve=true)   # performs them (quota-gated)
```

## 5. Open the conversation
```
draft_opener(prospect, offer)               → message text (review/edit it!)
dm_send(user, message)                       # DRY-RUN: returns the preview
dm_send(user, message, approve=true)         # actually sends
pipeline_set(username, stage="contacted", thread_id=<id>)
```

## 6. Handle replies
```
dm_listen()                                  → new inbound threads
dm_thread(thread_id)                         → read it
qualify_lead(conversation)                   → {temperature, stage, need, next_action}
draft_reply(prospect, offer, conversation)   → next message
dm_send(..., approve=true)
pipeline_set(username, stage="engaged"|"qualified", temperature=..., need=...)
```
Or triage the whole inbox at once:
```
inbox_triage(offer="...")   # reads every unread, qualifies, updates the board
```

## 7. Follow up (only if no reply)
```
draft_followup(prospect, offer, previous=<your last msg>, days_since=3)
dm_send(..., approve=true)
```
**Stop the moment they reply.** Two follow-ups max.

## 8. Hand off & track
```
pipeline_board()                  # full funnel view + counts by stage
pipeline_set(username, stage="handoff")     # ready for a closer
csv_export(path="leads.csv")
```

## Stay safe while doing all this
- `daily_plan()` before a session → what's your safe budget today.
- `usage()` any time → where you stand vs quotas.
- Everything that sends is **dry-run by default**. Show the human, then `approve=true`.
- Never blast. One personalized message per prospect, on a human cadence.
