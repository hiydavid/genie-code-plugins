# 3. Agent Comparison & Diff

**Home:** `mcp-genie-agent-versioning` (fifth tool, not a separate MCP)

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

## Proposed tool: `diff_agent_versions`

```
diff_agent_versions(space_id, version_id_a, version_id_b) → dict
```

Both versions must exist and be visible to the caller under the existing row filter.
Order does not matter (the tool labels them `a` and `b` by creation time).

### Return shape (sketch)

```json
{
  "ok": true,
  "space_id": "...",
  "version_id_a": { "version_id": "...", "created_at": "...", "config_hash": "..." },
  "version_id_b": { "version_id": "...", "created_at": "...", "config_hash": "..." },
  "config_hash_match": false,
  "top_level_changes": {
    "title":        { "changed": true,  "a": "...", "b": "..." },
    "description":  { "changed": true },
    "warehouse_id": { "changed": false },
    "parent_path":  { "changed": false }
  },
  "serialized_space_changes": {
    "version":               { "changed": true,  "a": 3, "b": 4 },
    "instructions_changed":  true,
    "tables_added":          ["catalog.schema.new_table"],
    "tables_removed":        ["catalog.schema.old_table"],
    "metric_views_added":    [],
    "metric_views_removed":  []
  }
}
```

### Design constraints

- **Never return full `serialized_space` or `instructions` text.** A boolean
  `instructions_changed` is sufficient for the diff. Callers who need the full content
  call `get_agent_version` deliberately.
- **Coarse granularity first.** Table-level add/remove, not column-level. The response
  must stay small enough to fit in model context even for Agents with hundreds of data
  sources.
- **Config hash shortcut.** If `config_hash` matches, skip the deep comparison and
  return `config_hash_match: true` immediately. This makes repeated diffs cheap.

### Implementation surface

| Module | Change |
|---|---|
| `contracts.py` | Add `validate_version_id_pair` (both non-empty, not identical) |
| `store.py` | Bulk-read two version envelopes in one round-trip (optional optimization; two `get_agent_version` calls work for v1) |
| `tools.py` | `diff_agent_versions_core` + registration in `register_tools` |
| `tests/test_tool_surface.py` | Add to the exact-surface test; add schema and edge-case tests |

No new storage, no new scopes, no new Genie API calls.

## Open questions

- What does the `serialized_space` internal structure look like beyond `version` and
  `data_sources`? The versioning MCP validates that `version` and `data_sources` exist,
  and that `instructions` or `config` is present. A diff tool needs to parse and compare
  these deeply nested structures. Start by inspecting real `serialized_space` payloads
  from representative Agents.
- Should the diff be purely structural (table name set comparison) or semantic
  (understand that a SQL function was renamed, not deleted+added)? Start structural;
  semantic diffing of SQL function bodies is a follow-on.
- Should the tool also support diffing a stored version against the *live* Agent (not
  just two stored versions)? That adds a Genie API call and an etag consideration.
  Defer until the stored-vs-stored case proves useful.
