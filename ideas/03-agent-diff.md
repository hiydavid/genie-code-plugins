# 3. Agent Comparison & Diff

**Home:** `mcp-genie-agent-versioning` (fifth tool, not a separate MCP)
**Status:** implementation-ready — the open questions below are resolved

The versioning MCP stores snapshots but deliberately keeps the serialized configuration
out of model context. When a user wants to understand *what actually changed* between two
versions, the only option today is to call `get_agent_version` twice and compare two large
JSON blobs client-side — expensive in model context and error-prone.

## Decision: a tool in the existing package, not a separate MCP

A standalone `mcp-genie-agent-diff` would need its own OBO plumbing, its own Unity Catalog
integration, and its own row-filter enforcement just to read rows the versioning MCP
already owns. That's unnecessary when:

- **The data is already there.** Both `config_envelope` JSON blobs sit in the store.
  A diff is a pure read over existing rows — no new storage, no new Genie API calls.
- **Same authorization model.** The row filter (`created_by = SESSION_USER()`) already
  enforces private-per-user histories, so diffs are private-per-user for free.
- **Same "keep payloads server-side" philosophy.** `restore_agent_config_version` already
  avoids relaying `serialized_space` through the model; diff extends that principle to
  comparison.
- **Completes the versioning workflow.** The natural sequence becomes
  `list_agent_versions` → `diff_agent_versions` → `restore_agent_config_version`.

## What the diff compares: the `serialized_space` map

The original blocking question — what the internal structure looks like beyond `version`
and `data_sources` — is now answered by the official documentation
([Genie Agents API](https://docs.databricks.com/aws/en/genie-agents/conversation-api),
"Understanding the serialized_space field"), which specifies the full schema, the
per-collection identity keys, and the sort/uniqueness invariants. Idea
[4](./04-agent-migration.md) independently mapped the same structure for identifier
remapping, and the versioning MCP's contract tests already encode its signature
(`version`, `data_sources`, plus `instructions` or legacy `config`).

| Path in `serialized_space` | Identity key (API-enforced sort key) | Diff treatment |
|---|---|---|
| `version` | — | scalar compare |
| `config.sample_questions[]` | `id` | added/removed/modified counts |
| `data_sources.tables[]` | `identifier` (three-part) | identifiers, plus column detail |
| `data_sources.tables[].column_configs[]` | `column_name` | column names |
| `data_sources.metric_views[]` (+ `column_configs`) | `identifier` / `column_name` | same as tables |
| `instructions.text_instructions[]` (max 1) | `id` | `modified` boolean |
| `instructions.example_question_sqls[]` | `id` | counts |
| `instructions.sql_functions[]` | `id` (sorted by `(id, identifier)`) | identifiers + `renamed` pairs |
| `instructions.join_specs[]` | `id` | counts |
| `instructions.sql_snippets.{filters,expressions,measures}[]` | `id` | counts |
| `benchmarks.questions[]` | `id` | counts |
| any other field | — | name-only flag |

Facts that shape the design:

- **Every collection has a stable identity key the API itself enforces** — arrays must be
  pre-sorted by that key, and ids must be unique within their collection group. A keyed
  set-diff is therefore well-defined without positional matching or fuzzy pairing.
- **Legacy payloads exist.** Older exports may carry `config` with no `instructions`
  (the store's validation accepts either). The diff must treat missing collections as
  empty, never as errors.
- **Documented size limits** (25,000 chars per string, 10,000 items per repeated field)
  are why the response carries identifiers and counts, never content.
- **Unknown fields are preserved** by the store envelope (forward compatibility); the
  diff reports them by name only.

## Proposed tool: `diff_agent_versions`

```
diff_agent_versions(space_id, version_id_a, version_id_b) → dict
```

Both versions must exist and be visible to the caller under the existing row filter;
otherwise the tool returns `{"ok": false, "error_type": "not_found", ...}` naming the
missing id(s), mirroring `get_agent_version`. The two ids must be non-empty and distinct
(validation error otherwise). Regardless of argument order, the response labels the
**older** row `a` and the **newer** row `b` (by `created_at`, tie-break `version_id`),
so `added` always reads as "present in the newer version only".

### Execution flow

1. Validate the id pair; read **both rows' metadata in one round trip** (`config_hash`,
   `created_at`, `created_by`, `reason`, `change_summary` — without `config_envelope`),
   ordered by `created_at, version_id` in SQL so the `a`/`b` assignment never compares
   timestamps in Python (their concrete shape differs between the warehouse
   `data_array` adapter and the in-memory test backend).
2. If either row is missing → `not_found`.
3. If the two `config_hash` values match → return immediately with
   `config_hash_match: true` and all-zero change sections. This shortcut is sound, not a
   heuristic: the hash basis in `contracts.py` covers the parsed `serialized_space` plus
   every envelope field except `etag` (and the server-stamped `format_version` /
   `space_id`, which are constant across a diff), so equal hashes imply identical
   restorable content.
   The common cases — repeated diffs and identical-content resaves, which the store
   appends as distinct versions — never load the two envelopes (up to `MAX_CONFIG_BYTES`
   each).
4. Otherwise load both envelopes in one additional round trip and run the pure
   structural diff. Worst case is two SQL statements total; the hash-match case is one.

### Return shape (refined against the real structure)

```json
{
  "ok": true,
  "space_id": "...",
  "config_hash_match": false,
  "version_a": {
    "version_id": "...", "created_at": "...", "created_by": "...",
    "reason": "before_update", "change_summary": "...", "config_hash": "..."
  },
  "version_b": { "…same fields…": "…" },
  "envelope_changes": {
    "title":        { "changed": true, "a": "Revenue analyst", "b": "Revenue analyst v2" },
    "description":  { "changed": true },
    "warehouse_id": { "changed": false },
    "parent_path":  { "changed": false }
  },
  "serialized_space_changes": {
    "version":          { "changed": true, "a": 2, "b": 3 },
    "sample_questions": { "added": 0, "removed": 1, "modified": 0 },
    "tables": {
      "added":    ["catalog.schema.new_table"],
      "removed":  ["catalog.schema.old_table"],
      "modified": [
        {
          "identifier": "catalog.schema.orders",
          "description_changed": true,
          "columns_added": ["region"],
          "columns_removed": [],
          "columns_modified": ["status"]
        }
      ]
    },
    "metric_views": { "added": [], "removed": [], "modified": [] },
    "instructions": {
      "text_instructions":     { "modified": true },
      "example_question_sqls": { "added": 1, "removed": 0, "modified": 2 },
      "sql_functions": {
        "added": ["catalog.schema.fiscal_quarter"],
        "removed": [],
        "modified": 0,
        "renamed": [{ "from": "catalog.schema.fn_old", "to": "catalog.schema.fn_new" }]
      },
      "join_specs": { "added": 0, "removed": 1, "modified": 0 },
      "sql_snippets": {
        "filters":     { "added": 0, "removed": 0, "modified": 1 },
        "expressions": { "added": 1, "removed": 0, "modified": 0 },
        "measures":    { "added": 0, "removed": 0, "modified": 0 }
      }
    },
    "benchmarks": { "added": 0, "removed": 0, "modified": 3 },
    "unknown_fields_changed": ["future_field"]
  }
}
```

### Design constraints

- **Never return content.** No `serialized_space`, instructions text, SQL, benchmark
  questions/answers, or `description` values (any of which can approach the 25k-char
  string limit). Identifiers, counts, booleans, and the short envelope scalars
  (`title`, `warehouse_id`, `parent_path`) only. Callers who need full content call
  `get_agent_version` deliberately.
- **Keyed, coarse granularity.** Table/metric-view level with column-name detail inside a
  modified table; counts for id-keyed instruction collections (32-hex ids are not worth
  relaying).
- **Bounded response.** Identifier lists cap at 50 entries per list with a `truncated`
  flag and total count, so even a catalog-wide rename on an Agent with hundreds of data
  sources stays small in model context.
- **Same authorization.** Both reads go through the existing row filter; no new storage,
  scopes, or Genie API calls.

### Implementation surface

| Module | Change |
|---|---|
| `contracts.py` | Add `validate_version_id_pair` (both non-empty, not identical) |
| `store.py` | Add a metadata-pair read in one round trip (`config_envelope` excluded); envelopes fetched only on hash mismatch |
| `diff.py` (new) | Pure `diff_agent_configs(config_a, config_b) → dict` — no I/O, fully unit-testable |
| `tools.py` | `diff_agent_versions_core` + registration in `register_tools` |
| `tests/test_diff.py` (new) | Structural diff over realistic v2 and legacy (`config`-only) fixtures |
| `tests/test_versions.py` | Tool-core tests: hash shortcut, `not_found`, a/b ordering, identical-id validation; plus a test that the hash-match path issues exactly one SELECT that never references `config_envelope` (model: `test_save_lineage_checks_and_readback_never_select_envelope`) |
| `tests/test_tool_surface.py` | Exact-surface test gains `diff_agent_versions`; schema and description assertions |
| `tests/conftest.py` | The `InMemoryBackend` dispatches on SQL shape, so the pair-read and envelope-pair queries need matching branches — without them the fake returns empty rows and every diff test reads as `not_found` |
| plugin `README.md` | Tool-table row + the `list → diff → restore` workflow |

No new storage, no new scopes, no new Genie API calls. Verified against the code: the
diff core needs only the store (the `sql` scope), never the Genie API, so `app.yaml`,
`provisioning.py`, `schema.py`, `config.py`, `pyproject.toml`, and `requirements.txt`
all stay unchanged. The tool follows the package's existing conventions exactly — a
`*_core` function over `(store, ...)` run through `_run_tool` via `to_thread.run_sync`,
`not_found` returned as a plain dict like `get_agent_version_core`, and input problems
raised as `ToolValidationError`.

## Resolved questions

### 1. What does `serialized_space` look like beyond `version` and `data_sources`?

Answered — this was the implementation blocker. The current API documentation specifies
the complete schema (see the map above): `config.sample_questions`, `data_sources`
(tables and metric_views with per-column configs), `instructions` (text_instructions,
example_question_sqls, sql_functions, join_specs, sql_snippets), and `benchmarks`, each
collection with a documented identity key and sort invariant. Residual verification:
inspect real payloads from a representative workspace — this research had no
authenticated workspace available, so it rests on the official docs, idea 4's independent
reference table, and the store's contract tests, which all agree. The unknown-field
tolerance makes the diff forward-compatible even if the schema grows.

### 2. Structural or semantic diff?

Structural, keyed by the API's own identity keys. A renamed SQL function changes its
`identifier`, which surfaces as remove+add — with one cheap exception: `sql_functions`
entries carry both `id` and `identifier`, so same-id/different-identifier pairs are
reported as `renamed` (from → to) rather than remove+add. Semantic diffing of SQL bodies
(whitespace-insensitive comparison, table renames inside SQL text) remains a follow-on.
One undocumented behavior to watch: whether the Genie UI preserves item `id`s across
edits. If ids churn, an edit degrades to add+remove instead of `modified` — cosmetic,
detectable from production checkpoint-vs-target diffs, and non-blocking.

### 3. Diff a stored version against the live Agent?

Stays deferred — and the research simplified it. Get Space returns an optional `etag`
(and `update_time`), and a read-only diff needs neither. A later variant accepting
`version_id_b: "live"` would reuse `_get_live_agent_config` and this same pure diff
function unchanged, and live-content hash comparison is already available through
`prepare_envelope`. Defer until the stored-vs-stored case proves useful.

## Implementation readiness

**Verdict: ready to implement.**

- The gating unknown (payload structure) is resolved by an officially documented schema
  whose identity keys make the keyed diff well-defined.
- The `config_hash` shortcut is proven sound from the existing hash basis, and the
  metadata-first flow keeps the common case from loading envelopes at all.
- The change is purely additive: one tool, one pure module, no schema/scope/API changes,
  same authorization.
- The core is a pure function, testable without any Databricks dependency.
- Baseline verified: the plugin's test suite (99 tests) passes against a fresh install
  of the declared dependency range (`fastmcp>=3.4,<4`) after repairing the surface-test
  helper — `FastMCP.get_tools()` no longer exists in any 3.x release; the current API is
  `await list_tools()`. Without that repair, the exact-surface test this design extends
  cannot run.

Suggested build order:

1. `diff.py` + `tests/test_diff.py` — the pure structural diff over realistic v2 and
   legacy fixtures (no infra required).
2. `validate_version_id_pair` + the metadata-pair store read.
3. `diff_agent_versions_core`, registration, surface tests, plugin README row.

Residual risks (none blocking):

- Real-payload confirmation pending workspace access; first production use should eyeball
  one real diff against the Genie UI's settings tab.
- `id` stability across UI edits — affects `modified` vs add/remove labeling only.
- Pathological diffs (catalog-wide rename) hit the identifier-list caps; the counts keep
  the response honest.
