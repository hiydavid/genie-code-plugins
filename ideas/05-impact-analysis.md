# 5. Multi-Agent Impact Analysis — UC Lineage for Genie Agents

**MCP name:** `mcp-genie-agent-impact`

When a Unity Catalog object (table, view, metric view) is about to be changed or
deprecated, downstream Genie Agents that reference it could silently break. There's no
tool that maps the blast radius across Genie Agents.

**Answer, after checking current platform coverage:** the *observed* half of this problem
is already covered by system tables — Genie Agent queries are captured in UC lineage and
query history with `genie_space_id` attribution. What nothing provides is the *declared*
half — a reverse index from UC objects to Agent configurations, independent of whether an
Agent has ever been asked anything — and the join of declared + observed + downstream UC
dependencies into one ranked blast-radius answer. That join is the MCP.

## What the platform already covers (research findings)

| Signal | Native coverage | Source |
|---|---|---|
| Observed table → Agent edges | `system.access.table_lineage` records read events from Genie Agents; `entity_metadata.genie_space_id` attributes the edge. Note: `entity_type` has no `GENIE` value — filter on `entity_metadata.genie_space_id IS NOT NULL`. | [Lineage system tables](https://docs.databricks.com/aws/en/admin/system-tables/lineage) |
| Indirect dependencies through views | Lineage rows with `direct_access = false` are emitted for underlying tables when a query reads a view — observed closure through views comes for free. | [Lineage system tables](https://docs.databricks.com/aws/en/admin/system-tables/lineage) |
| Observed column-level edges | `system.access.column_lineage` carries the same `entity_metadata.genie_space_id` — which Agents actually read a given column. | [Lineage system tables](https://docs.databricks.com/aws/en/admin/system-tables/lineage) |
| Per-Agent usage stats | `system.query.history.query_source.genie_space_id` ("Statement executed from a Genie Agent") yields per-Agent query counts, error rates, executing users, and warehouse; `query_tags` supports cost attribution. | [Query history system table](https://docs.databricks.com/aws/en/admin/system-tables/query-history) |
| Static view dependency closure | The Tables API returns `view_dependencies` — a structured list of table/function/volume/connection dependencies — for `VIEW`, `MATERIALIZED_VIEW`, and `STREAMING_TABLE`. Not populated by `listTables`; requires a per-object GET. | [Tables API](https://docs.databricks.com/api/workspace/tables/get) |
| Agent enumeration + configs | `GET /api/2.0/genie/spaces` is paginated (`page_token` → `next_page_token`) and returns `update_time` per Agent; full configs via `GET .../{space_id}?include_serialized_space=true`. The SDK documents that list responses exclude `serialized_space`, so a full crawl is N+1 calls. | [Genie Agents API](https://docs.databricks.com/aws/en/genie-agents/conversation-api) |
| Cost surface | `system.billing.usage` exposes `usage_metadata.genie.surface = GENIE_AGENTS` (workspace-level; no per-space attribution). | [Monitor Genie cost](https://docs.databricks.com/aws/en/genie/monitor-cost) |
| Audit events | `system.access.audit` service `aibiGenie` (conversation, feedback, review events with `request_params.space_id`). | [Audits & alerts](https://docs.databricks.com/aws/en/genie-agents/audits-alerts) |

Caveats: lineage system tables keep a **rolling 1-year window** (Catalog Explorer's Lineage
tab retains longer), and "both lineage tables represent a subset of all read/write events."
Observed data is also empty for Agents that have never been queried — exactly the Agents a
schema change will silently break next week.

### Verdict

Catalog Explorer's Lineage tab answers "who consumes this table" one table at a time in the
UI — it cannot separate Agent-config references from incidental reads, does not combine
declared and observed signals, does not rank by usage, and exposes no API Genie Code could
call. Nothing native answers:

> "I'm about to drop column X from `catalog.schema.table` — which Genie Agents will
> degrade, through which references (declared vs. observed, direct vs. via view V), and
> which of those serve real traffic?"

## The two signals (design core)

| | Declared (config crawl) | Observed (system tables) |
|---|---|---|
| Source | `serialized_space` of every Agent | `table_lineage` / `column_lineage` / `query.history` |
| Catches | registered data sources, metric views, SQL functions, join specs, example/benchmark SQL — whether or not ever executed | everything Genie actually queried, including ad-hoc SQL against objects never registered in any Agent |
| Misses | references that exist only in prose (flagged, never asserted); runtime-only references | Agents never queried; usage older than 1 year |
| Freshness | as of last crawl (incremental) | near-real-time; queried at impact time |

An Agent is **at risk** if *either* signal matches the changed object or any UC object that
depends on it. Declared-only matches with zero observed usage are still reported — they are
silent breakage waiting to happen — but ranked below Agents serving live traffic.

## v1 design

### Index build (crawler)

1. `GET /api/2.0/genie/spaces` (paginated) — cheap; returns `space_id`, `title`,
   `update_time` per Agent.
2. Compare against the stored index; `GET .../{space_id}?include_serialized_space=true`
   only for new Agents or changed `update_time`; delete rows for vanished Agents.
3. Parse each `serialized_space` **server-side** and upsert reference rows. The payload
   never passes through model context — same philosophy as `mcp-genie-agent-versioning`;
   the crawler emits compact rows, not payloads.
4. Full rebuild is the same loop with the cache disabled.

### Reference extraction (three tiers)

| Tier | Locations | Confidence |
|---|---|---|
| 1. Structured identifiers | `data_sources.tables[].identifier`, `data_sources.metric_views[].identifier`, `instructions.sql_functions[].identifier`, `instructions.join_specs[].left/right.identifier`; `column_configs[].column_name` as column-level detail | authoritative (`declared`) |
| 2. SQL text bodies | `example_question_sqls[].sql`, `sql_snippets.{filters,expressions,measures}[].sql`, `benchmarks.questions[].answer[].content` | parsed with idea 04's conservative token rules (exact three-part names; registered identifiers highest confidence; ambiguity reported, never guessed) (`parsed`) |
| 3. Prose | `text_instructions[].content`, table/metric-view `description` | locations flagged only (`heuristic`) — never asserted as a reference |

The extraction table mirrors the location map in [idea 4](./04-agent-migration.md); the
migration utility's remap rules and this parser should share one code module.

### UC dependency closure

For each distinct declared object, resolve its type via the Tables API; if it is a view
family object, record `view_dependencies` edges transitively (depth-capped, cycle-safe)
into a `uc_dependencies` table. This yields the static answer to "which Agents reference
objects that *depend* on this object" — e.g. Agent declares `v_orders`, which depends on
`orders`, so `orders` changes put that Agent on the report. Observed closure (through
`direct_access = false` lineage rows) is queried live as a complement, not materialized.

### Index schema (UC tables, provisioned like the versioning MCP)

- `agent_index (space_id, title, description, parent_path, warehouse_id, update_time, config_hash, crawled_at)`
- `agent_references (space_id, uc_object, object_kind, ref_kind, ref_location, tier, last_seen)` —
  `ref_kind` ∈ `data_source | metric_view | sql_function | join_spec | example_sql | benchmark_sql | snippet_sql | prose_mention`
- `uc_dependencies (object, depends_on, object_kind, depends_on_kind, resolved_at)`

Observed edges are **not** materialized: they are queried live from system tables at impact
time (already indexed server-side; the 1-year window is appropriate for current blast
radius).

### MCP tools

| Tool | Purpose |
|---|---|
| `check_uc_object_impact` | Blast-radius report for a UC object (optionally scoped to columns): affected Agents ranked, with match reasons and usage stats |
| `get_agent_references` | Forward index: every UC object one Agent declares or has been observed querying, with locations |
| `find_stale_references` | Declared objects that no longer exist in UC — Agents that are already broken or about to be (batch existence check via `listTables` per schema, set-difference) |
| `refresh_agent_index` | Run the crawl (incremental by default, full on request); returns crawl stats, never payloads |

`check_uc_object_impact` flow: ensure index freshness (TTL, default 24 h, else incremental
refresh) → declared matches (exact object, plus transitive closure through
`uc_dependencies`) → observed matches (lineage for edges, `query.history` for usage
aggregation, `column_lineage` when columns are specified) → merge, rank (declared-direct
and live traffic first, declared-only next, via-dependents grouped), emit a compact report:

```json
{
  "object": "prod.sales.orders",
  "columns": ["region"],
  "agents": [
    {
      "space_id": "3c409c00b54a44c79f79da06b82460e2",
      "title": "Sales Analytics",
      "declared": { "direct": ["data_source"], "via": [{"object": "prod.sales.v_orders", "kind": "view"}] },
      "observed": { "queries_30d": 412, "users_30d": 27, "last_query": "2026-08-18" },
      "column_hits": ["column_configs.region", "observed_reads: 88"],
      "config_updated": "2026-07-30"
    }
  ],
  "index": { "crawled_at": "2026-08-19T21:00:00Z", "stale": false }
}
```

### Deployment & auth

FastAPI + FastMCP on Databricks Apps, mirroring `mcp-genie-agent-versioning`: OBO with
`genie` + `sql` user scopes; app identity provisions the schema; system-schema SELECT
(lineage, query history) required for the observed half. One real decision: **crawl
identity**.

- **Per-user (default):** crawl runs as the caller. Zero extra admin grants; Agent
  configs never leak between users; blast-radius completeness equals the caller's Genie
  read access. Wrong shape when the schema-change reviewer has UC rights but no Genie
  permissions.
- **Shared (opt-in flag):** app service principal crawls, granted `CAN VIEW` on Agents by
  an admin; index is group-readable workspace metadata. Right shape for platform teams —
  and the natural substrate for the shared "Agent index" below. Requires admin grants and
  accepts that titles/references are visible to the grantee group.

## v2 candidates

- **Adoption & drift audit** (idea 4's v2): the crawl already fetches every
  `serialized_space`; diffing against bundle-exported `*.geniespace.json` adds
  `{managed, bundle_key, drift}` per Agent almost for free.
- **Shared Agent index for idea 2**: `agent_index` + `agent_references` are exactly the
  dimension tables the usage-analytics MCP needs; one crawl serves both.
- **Pre-flight in the migration flow**: a Genie Code skill runs `check_uc_object_impact`
  as step 0 of idea 4's promotion flow before rendering/deploying remapped payloads.

## Open questions

- ~~Can the index be built incrementally or does it need a full crawl each time?~~ →
  **Incremental.** The list call is cheap and returns `update_time` per Agent; re-GET only
  new/changed Agents. Verify at implementation that `update_time` reliably moves on every
  `serialized_space` edit (it is documented as matching the UI's last-modified value);
  fallback is periodic hash-comparison.
- ~~Should the index live in UC or in-memory?~~ → **UC.** Persistence across restarts,
  SQL-queryable by the analytics MCP, incrementally refreshable; freshness is a TTL-on-read
  plus an explicit refresh tool, not an in-memory cache. Observed edges stay in system
  tables and are queried live.
- ~~Can we detect UC references embedded in natural-language instructions, or only
  structured data source registrations?~~ → **Three tiers** (see above): structured
  identifiers are authoritative; SQL text is parsed with idea 04's conservative rules;
  prose is flagged, never asserted. Separately, observed lineage catches references that
  appear in no configuration at all.
- Is `view_dependencies` populated for `METRIC_VIEW` table type, or only
  `VIEW`/`MATERIALIZED_VIEW`/`STREAMING_TABLE`? If not, observed closure covers queried
  metric views; static closure for never-queried ones needs another source. Verify first.
- Per-surface lineage coverage (Genie One UI, Conversation API, Slack app, embedded) is
  documented in aggregate ("Genie Agents" are a captured source) but not per surface.
- Does Genie's generated SQL reliably emit `column_lineage` rows? Docs say column lineage
  is captured "as much as possible" — column-level impact must degrade gracefully to
  table-level.
- The securable-lineage API behind Catalog Explorer's Lineage tab (surfaced as
  `listSecurableLineagesBySecurable` audit events; absent from SDK 0.133) is not public.
  If it becomes public, `uc_dependencies` maintenance can be replaced by direct queries.
  The design assumes system tables only.
