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

## Open questions

- What Genie monitoring/usage APIs exist? Is there a `GET /api/2.0/genie/spaces/{space_id}/usage`
  or similar endpoint? Or does this data come from system tables / monitoring tables?
- Can conversation-level data (status, error, duration) be aggregated across Agents without
  pulling every conversation?
- Is warehouse cost attribution available per-Agent or only per-query?
