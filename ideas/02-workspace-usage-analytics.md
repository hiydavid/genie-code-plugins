# 2. Workspace-Wide Genie Usage & Cost Analytics

**Proposed shape:** Genie Code workspace skill (curated SQL recipes) + a sibling Databricks App
(following the versioning MCP's bootstrap pattern) that provisions materialized views in Unity
Catalog. A thicker analytics MCP is optional and deferred.

## Research conclusion: native ability already exists

Genie Code can already do workspace-wide Genie cost & usage analysis with only the
Databricks CLI and workspace credentials — no special MCP required:

- **Arbitrary SQL:** the CLI has no `databricks sql query` command, but
  `databricks api post /api/2.0/sql/statements` (Statement Execution API passthrough)
  runs any query with CLI-managed auth. The `databricks-core` skill already teaches
  `databricks experimental aitools tools query`, and `databricks-unity-catalog` ships
  ready-made `system.billing.usage` + `system.billing.list_prices` queries.
- **Agent discovery & conversations:** the CLI has a full `databricks genie` command
  group — `list-spaces` (paginated), `list-conversations`, `list-conversation-messages`,
  all with `-o json`.
- **All required data is SQL-queryable** in `system.billing.usage`,
  `system.query.history`, `system.access.audit`, and `system.access.assistant_events`.

So the gap is not access. The gap is **correlation and repeatability**: every
cross-Agent question ("which Agents drive the most cost?", "error rates above 5%?",
"which Agents have declining usage?") currently requires an agent to compose
multi-table joins with non-obvious filters each time. The fix is curated queries and a
materialized rollup — not a new server.

## Corrected data model

Research corrected several assumptions in earlier drafts of this idea:

| Question | Answer |
|---|---|
| `system.assistant.*` tables? | **Do not exist.** The table is `system.access.assistant_events` (single table), and it covers **Genie Code only** — never Genie Agents/Spaces conversations. |
| Per-space cost in billing? | **No.** `system.billing.usage` rows with `billing_origin_product = 'GENIE'` attribute cost by workspace, user (`identity_metadata.run_as`), surface (`usage_metadata.genie.surface` ∈ `GENIE_CODE`, `GENIE_ONE`, `GENIE_AGENTS`), and channel — but not by Space ID. |
| Query Tags as billing join key? | **No.** There is no auto-injected `@@genie_*` query tag. The durable per-space bridge is `system.query.history.query_source.genie_space_id` (Public Preview). |
| AI Gateway per-space token attribution? | **Not possible today.** `system.ai_gateway.usage` has no documented join key to a Genie space/agent. Genie token cost lands in `system.billing.usage` under the Genie SKU anyway. |
| REST crawl needed for volume metrics? | **No.** Conversation/message counts, errors, and feedback per space are all in `system.access.audit` (`service_name = 'aibiGenie'`) as plain SQL. The per-Space REST API is only needed for message *content*. |

### Sources by analysis dimension

| Dimension | Source | Key fields |
|---|---|---|
| Genie cost (all surfaces) | `system.billing.usage` | `billing_origin_product = 'GENIE'`, `sku_name`, `usage_quantity` (DBUs), `usage_metadata.genie.surface`, `usage_metadata.genie.channel`, `identity_metadata.run_as`, `workspace_id`. Join `system.billing.list_prices` for dollars. |
| Warehouse compute per space | `system.query.history` | `query_source.genie_space_id`, `compute.warehouse_id`, `execution_status`, duration metrics |
| Volume / errors / feedback per space | `system.access.audit` | `service_name = 'aibiGenie'`; actions `createConversation`, `createConversationMessage` / `genieStartConversationMessage`, `executeMessageQuery`, `regenerateConversationMessage`, `updateConversationMessageFeedback` (with `feedback_rating`); `request_params.space_id`, `conversation_id`, `message_id`; `response.error_message` for failures |
| Genie Code usage | `system.access.assistant_events` | `event_time`, `initiated_by`, `workspace_id`. Genie Code only; background/automated calls (autocomplete, eval runs, indexing) are not logged since May 2026. |

Gotchas worth baking into the skill:

- Billed Genie usage sits under the shared **Serverless Real-Time Inference** SKU;
  always filter `billing_origin_product = 'GENIE'` or you'll pick up other products.
- Free usage appears as `sku_name = 'GENIE_FREE_USAGE'` (no `list_prices` match).
- `system.access.audit` is **regional** — account-wide rollups need per-region queries.
- Through Jan 31, 2027, Genie One / Genie Agents usage by users is free
  (service-principal usage is billed); Genie Code includes 150 free DBUs/user/month.
- Audit tables and AI Gateway tables require system schemas enabled by an account admin.

## Feature shape

### 1. Skill: `genie-workspace-analytics` (the bulk of the value)

A Genie Code workspace skill containing parameterized, curated SQL recipes that run via
`databricks api post /api/2.0/sql/statements` (or `databricks experimental aitools tools
query`). One recipe per analysis verb:

- **Volume & adoption per Agent:** distinct `conversation_id` + active users over time,
  from `aibiGenie` audit events grouped by `request_params.space_id` (daily/weekly/monthly).
- **Error/rejection rates per Agent:** failed `executeMessageQuery` /
  `createConversationMessage` outcomes and `system.query.history` rows with
  `execution_status = 'FAILED'` and `genie_space_id` populated, as a share of total messages.
- **Feedback per Agent:** `updateConversationMessageFeedback` ratings aggregated by space.
- **Cost by surface/user/workspace:** `system.billing.usage` joined to `system.billing.list_prices`.
- **Warehouse compute per Agent:** `system.query.history` grouped by `query_source.genie_space_id`.
- **Genie Code adoption:** `system.access.assistant_events` trends by user.
- **Ranking queries:** most/least used, declining usage (window functions over the volume
  rollup), cost-per-conversation.

The skill also documents the gotchas above and the auth prerequisites (system schemas
enabled, `SELECT` on `system` catalog, warehouse `CAN USE`).

### 2. Materialization: app-bootstrapped MVs following the versioning-MCP pattern

When [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/) is deployed on Databricks Apps,
its App service principal runs an idempotent bootstrap (`server/provisioning.py`) that creates a
schema in a designated catalog, its tables, row filters, and least-privilege grants — and never
raises. The analytics feature reuses exactly that pattern:

- **App startup bootstraps a `genie_analytics` schema containing materialized views:**
  - `space_metrics_daily(space_id, date, conversations, messages, active_users, failed_queries, feedback_avg, warehouse_dbus, ...)`
  - `cost_by_surface_daily`, `genie_code_usage_daily`, and the optional
    `space_warehouse_compute_daily` (the only MV requiring `system.query.history` grants;
    bootstrap reports a warning and skips it if the grant is missing — the rest still ships).
- **The App SP is the MV owner.** MV refresh runs on the MV's own schedule under the SP's
  privileges — the app runtime is not load-bearing for freshness. The app's runtime role stays
  thin: serve tools, bootstrap once. If the app is redeployed or briefly down, MVs keep refreshing.
- **Deployment is a sibling app sharing `provisioning.py`** (separate failure domain and release
  cycle from the versioning MCP), not an extension of it. The colocation is still valuable: the
  versioning store already crawls Genie Spaces, and joining `space_metrics_daily` with agent
  metadata (space titles) gives cost-per-Agent answers in one query.
- **A pure-DAB deployment (bundle creating MVs, no app) remains a documented alternative** for
  orgs that want DDL-only, but it is not the primary path.

Consequences of putting the rollup in UC:

- Genie Code answers cross-Agent questions with a single-table query instead of composing joins.
- **Genie One** can answer "which Agents drive the most cost?" in natural language directly.
- Lakeview dashboards and human analysts query the same table.
- This becomes the shared "Agent index" the ideas README envisions for idea 5
  (impact analysis); idea 5's crawl adds agent metadata (title, config, tables) to the same table.

### 3. Deployment & permissions model

**Personas:**

| Persona | Role |
|---|---|
| Genie agent admin | Deploys the app; owns the analytics schema and skill. No inherent access to system tables. |
| Metastore / account admin | Runs a one-time `GRANT SELECT` script (billing usage, query history, access audit) against the App SP. No infrastructure responsibility. |
| Team (agent authors, leads) | `SELECT` on `genie_analytics.*` only — aggregates, not raw query text. |

- **Deploy as the App SP, never a user identity** — MV ownership and refresh privileges stay
  stable when people leave or lose grants. Databricks Apps gives this for free.
- **The grant ask is unchanged by the app pattern**: the App SP still needs one-time grants on
  the source system schemas; the app changes who runs the DDL, not who authorizes source access.
  The grant script ships with the app setup README as copy-paste SQL, so the agent admin's ask to
  the platform team is a snippet, not a conversation.
- **Graceful degradation**: the query-history-dependent MV is optional. Without its grant, the
  deployment still ships audit-based volume/errors/feedback MVs; per-space warehouse compute
  arrives when the grant lands. ("Which Agents drive the most cost?" then degrades to a
  messages-per-space proxy — approximate, and the doc should say so.)
- **Source flexibility**: MV definitions should accept either live system tables or log-delivery
  copies where orgs centralize audit/billing data in UC owned by a data team — often easier to
  get access to than live system schemas.

### 4. Explicitly not built

- **A dedicated analytics MCP server that reimplements queries.** Every capability above is
  plain SQL the CLI already runs. A thin MCP hosted on the same app — whose tools are just
  parameterized `SELECT`s over the MVs, using the app's OBO auth — is the optional branch for
  consumers that are not Genie Code / Databricks-CLI agents (Claude, Cursor, internal copilots).
  The analytics logic lives entirely in the MVs; the server is a dumb reader. Defer building it
  until a non-CLI consumer actually exists.
- **REST-API crawling for volume metrics.** Audit logs already carry per-space counts;
  crawling `GET /api/2.0/genie/spaces/{id}/conversations` per space is redundant for analytics.
- **AI Gateway per-space token attribution.** No join key exists today.
- **Budget alerts/enforcement.** Already shipped natively (see below).

## Relationship to the built-in budget dashboard

Databricks ships an [account-level budget & cost monitoring dashboard](https://docs.databricks.com/aws/en/genie/monitor-cost)
and [budget controls](https://docs.databricks.com/aws/en/genie/budgets). That answers
"are we over budget?" — reactive cost gates for account admins. This skill answers
"what should we do about it?" — usage intelligence for agent authors and team leads
(rank Agents by cost/usage, adoption trends, error rates) so Genie Code can recommend
which Agents to fix, retire, or promote.

## Key references

- [Monitor and understand your Genie cost](https://docs.databricks.com/aws/en/genie/monitor-cost)
- [Genie cost and budgets FAQ](https://docs.databricks.com/aws/en/genie/genie-cost-budgets-faq)
- [Monitor Genie Agents usage with audit logs and alerts](https://docs.databricks.com/aws/en/genie-agents/audits-alerts)
- [Query history system table reference](https://docs.databricks.com/aws/en/admin/system-tables/query-history)
- [Audit log system table reference](https://docs.databricks.com/aws/en/admin/system-tables/audit-logs)
- [Genie Code system table reference](https://docs.databricks.com/aws/en/admin/system-tables/assistant)
- [Genie command group (CLI reference)](https://docs.databricks.com/aws/en/dev-tools/cli/reference/genie-commands)
- [Statement Execution tutorial (`databricks api post /api/2.0/sql/statements`)](https://docs.databricks.com/aws/en/dev-tools/sql-execution-tutorial)
- [Genie Agents conversation API](https://docs.databricks.com/aws/en/genie-agents/conversation-api)

## Open questions

- Error semantics: which `aibiGenie` audit outcomes and `execution_status` values count
  as a "rejection" vs a retryable failure? Needs a pass over real audit data.
- Does `genie_space_id` in `system.query.history` backfill reliably for older queries,
  or only from the Preview date forward? Affects how far back the rollup can go.
- Warehouse DBU attribution: is `system.query.history` joinable to `system.billing.usage`
  via warehouse_id + time bucket with acceptable accuracy, or should warehouse cost be
  approximated from query durations?
- Retention: audit tables keep ~365 days; the rollup table should be the long-term record.
