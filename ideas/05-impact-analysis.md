# 5. Multi-Agent Impact Analysis — UC Lineage for Genie Agents

**MCP name:** `mcp-genie-agent-impact`

When a Unity Catalog object (table, view, metric view) is about to be changed or
deprecated, downstream Genie Agents that reference it could silently break. There's no
tool that maps the blast radius across Genie Agents.

## Idea

An MCP that indexes all Genie Agents in a workspace, extracts their data-source
references (tables, views, metric views, catalogs, schemas), and builds a reverse index.
Given a UC object (e.g. `catalog.schema.table`), it answers:

- Which Genie Agents reference this object as a data source?
- Which Agents reference objects that *depend* on this object (views built on the table)?
- Which Agents' SQL functions reference this object?
- How many users / queries does each affected Agent serve? (tie-in with the analytics MCP).

Genie Code could use this before a schema change: _"if I drop column X from table Y, which
Genie Agents should I review and update first?"_

## Potential approach

1. List all Genie Agents in the workspace (`GET /api/2.0/genie/spaces`).
2. For each Agent, read its config (`GET .../{space_id}?include_serialized_space=true`) and
   extract all UC references from `data_sources`, SQL functions, and instructions.
3. Build a reverse index in UC: `{uc_object → [space_ids]}`.
4. Periodically refresh the index (or on-demand when Genie Code queries it).
5. Cross-reference with the analytics MCP to add user/query impact to each entry.

## Open questions

- Can the index be built incrementally or does it need a full crawl each time?
- Should the index live in UC (for persistence) or in-memory (for freshness)?
- Can we detect UC references embedded in natural-language instructions, or only structured
  data source registrations?
