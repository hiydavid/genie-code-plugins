# 3. Agent Comparison & Diff

**MCP name:** `mcp-genie-agent-diff`

The versioning MCP stores snapshots but deliberately keeps the serialized configuration
out of model context. When a user wants to understand *what actually changed* between two
versions, there's no tool for that.

## Idea

An MCP that compares two Agent versions (live vs. stored, or two stored versions)
server-side and returns a **semantic delta** — a compact, human-readable summary of what
changed, without relaying the full serialized configuration. The diff would cover:

- Added / removed / modified instructions.
- Added / removed / modified SQL functions (with function body diffs).
- Added / removed / modified example questions.
- Added / removed data sources (tables, metric views).
- Parameter / setting changes.

The output is small enough to fit in model context and structured enough for Genie Code
to reason about. Integrates with the versioning MCP by referencing its stored versions.

## Integration with versioning MCP

The diff MCP would read stored envelopes from `mcp-genie-agent-versioning` and the live Agent
from the Genie API, diff them server-side, and return only the delta. It would not duplicate
storage — the versioning MCP is the source of truth for snapshots.

## Open questions

- What does the `serialized_space` internal structure look like? The versioning MCP validates
  that `version` and `data_sources` exist, and that `instructions` or `config` is present.
  A diff tool needs to parse and compare these deeply nested structures.
- Should the diff be purely structural (JSON diff) or semantic (understand that a SQL function
  was renamed, not deleted+added)?
