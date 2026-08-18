# 2. Agent Analytics & Monitoring — Workspace-Wide Usage MCP

**MCP name:** `mcp-genie-agent-analytics`

Genie Code can already review past conversations for a single Agent, but there is no
workspace-level view of **cost, usage, and adoption** across all Genie Agents.

## Idea

An MCP that calls Genie Agent usage APIs across the workspace and exposes:

- Query volume per Agent (daily/weekly/monthly trends).
- Active user counts and adoption metrics.
- Cost attribution (warehouse consumption, token usage estimates).
- Error/rejection rates per Agent.
- Most and least used Agents.

Genie Code could use these tools to answer questions like _"which Agents drive the most
cost?"_, _"which Agents have declining usage?"_, or _"show me Agents with error rates
above 5%."_ This gives Genie Code the data it needs to prioritize optimization work.

## Why this isn't covered by the built-in budget dashboard

Databricks already ships an [account-level budget & cost monitoring dashboard](https://docs.databricks.com/aws/en/genie/monitor-cost)
and [budget controls](https://docs.databricks.com/aws/en/genie/budgets) that let admins:

- Set per-space/workspace budgets with alerts and enforcement.
- View cost trends and breakdowns by Genie Space in a pre-built UI.
- Block Genie usage when a budget limit is reached.

**That dashboard answers "are we over budget?" — this MCP answers "what should we
do about it?"** The built-in tools are reactive cost gates for account admins. The
MCP is for Genie Code users (developers, agent authors, team leads) who need to
understand and improve agent performance:

| Capability | Built-in Budget Dashboard | This MCP |
|---|---|---|
| Cost per Genie Space | ✅ Pre-built chart | ✅ Natural-language query |
| Budget alerts & enforcement | ✅ Alerts, hard blocks | ❌ (out of scope — use built-in) |
| **Rank** Agents by cost/usage | ❌ Single-space view | ✅ Cross-agent ranking |
| Agent adoption metrics (active users, trends) | ❌ | ✅ |
| **Error/rejection rates** per Agent | ❌ | ✅ |
| Token usage estimates per Agent | ❌ | ✅ |
| "Which Agents have declining usage?" | ❌ | ✅ Conversational query |
| "Show Agents with error rates > 5%" | ❌ | ✅ Conversational query |
| Combine with agent diff, migration, versioning MCPs | ❌ | ✅ Compound workflows |
| Enable Genie Code to prioritize optimization work | ❌ | ✅ |

**In short:** the built-in dashboard is an admin cost-control tool. This MCP is an
analytics & optimization tool that puts usage intelligence into Genie Code's hands,
so it can recommend which Agents to fix, retire, or promote.

## Cost Data Sources (from Databricks Docs Research)

Genie Agent costs come from **three independent billing dimensions**, each tracked in a
different place. An MCP must correlate across all three to produce a complete per-Agent
cost picture.

### 1. Genie Usage SKU (Conversation/Query Billing)

Tracked in `system.billing.usage` with SKU names containing "GENIE". Filter on
`usage_sku` and aggregate by `workspace_id` / date. This covers the flat per-query or
per-conversation Genie charge.

- [Monitor and understand your Genie cost](https://docs.databricks.com/aws/en/genie/monitor-cost)
- [Genie cost and budgets FAQ](https://docs.databricks.com/aws/en/genie/genie-cost-budgets-faq)

### 2. SQL Warehouse Compute (Query Execution Cost)

Every Genie-generated SQL runs on a SQL Warehouse. Warehouse DBU consumption is tracked
in `system.billing.usage` with the relevant warehouse SKUs. **Query Tags** (in public
preview) can label queries with the originating Genie Space/Agent, enabling per-Agent
attribution of warehouse costs.

- [Manage budgets and cost controls for Genie](https://docs.databricks.com/aws/en/genie/budgets)

### 3. Foundation Model Token Usage (LLM Cost)

Genie's LLM calls go through **Unity AI Gateway**. Token usage is tracked in AI Gateway
system tables (`system.ai_gateway.*` or model serving usage tables) with
`user_id`/`team`/`project` dimensions. Cost per token is derived from the model serving
endpoint rate card.

- [Track foundation model spend by user, team, or project](https://docs.databricks.com/aws/en/ai-gateway/track-cost-tutorial)
- [AI Gateway usage tracking](https://docs.databricks.com/aws/en/ai-gateway/usage-tracking)

### 4. Conversation Metadata (volume, status, agents)

| Source | What It Provides | Scope |
|---|---|---|
| `system.assistant.conversations` | conversation_id, user_id, workspace_id, started_at, status, duration | Genie Code (Assistant) |
| `system.assistant.messages` | message content, role, token_count estimates | Genie Code (Assistant) |
| `system.assistant.events` | event stream within conversations (tool calls, errors) | Genie Code (Assistant) |
| Genie Agents REST API `GET /api/2.0/genie/spaces/{space_id}/conversations` | List/Get conversations, messages, query results per Genie Space | Genie Agents/Spaces |
| Audit logs (`aibiGenie` service) | `genieStartConversationMessage`, `genieCreateMessage` events | All Genie interactions |

Key references:
- [Genie Code system table reference](https://docs.databricks.com/aws/en/admin/system-tables/assistant)
- [Genie Agents conversation API](https://docs.databricks.com/aws/en/genie-agents/conversation-api)
- [List conversations in a Genie Space (API reference)](https://docs.databricks.com/api/workspace/genie/listconversations)
- [Monitor Genie Agents with audit logs and alerts](https://docs.databricks.com/aws/en/genie-agents/audits-alerts)

## Open questions

- ~~What Genie monitoring/usage APIs exist?~~ → **Answered.** There is no single
  `GET .../usage` endpoint. Data lives across: (a) the Genie Agents REST API for
  per-Space conversation listing, (b) `system.assistant.*` system tables for
  workspace-wide Genie Code conversation data, (c) `system.billing.usage` for SKU
  costs, (d) AI Gateway system tables for token usage, and (e) audit logs for event
  monitoring.
- ~~Can conversation-level data (status, error, duration) be aggregated across Agents
  without pulling every conversation?~~ → **Partially.** `system.assistant.conversations`
  and `system.assistant.events` allow SQL aggregation across all Genie Code usage.
  Genie Agents/Spaces conversation data is only available via the REST API
  (per-Space, paginated). A periodic indexer that materializes both into a UC table
  would enable arbitrary cross-Agent queries.
- ~~Is warehouse cost attribution available per-Agent or only per-query?~~ → **Per-query
  today, rolling up to per-Agent with Query Tags.** Warehouse billing is at the query
  level. Query Tags (public preview) can label queries with the originating Genie
  Space, enabling per-Agent roll-ups in `system.billing.usage`. The MCP could automate
  this roll-up by joining on the tag.

## Remaining unknowns

- Do `system.assistant.*` tables cover Genie **Agents/Spaces** conversations, or only
  Genie **Code** (Assistant) usage? The docs name this "Genie Code system table
  reference" — it may not include Genie Agents/Spaces conversations, which would mean
  the REST API is the only source for those.
- Is there a programmatic way to list all Genie Spaces/Agents in a workspace? (So the
  MCP can discover what to crawl.)
- What is the exact join key between a Genie conversation and a `system.billing.usage`
  record? Query Tags may be the bridge, but the field name and availability need
  confirmation.
- Are token counts surfaced per message in the Genie Agents API response, or only via
  AI Gateway tables?
