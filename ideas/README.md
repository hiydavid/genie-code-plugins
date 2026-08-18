# Genie Code Plugin Ideas

Ideas for plugins, MCPs, tools, and other extensions that augment Genie One / Genie Agents
through Genie Code. These focus on product gaps not already covered by native Genie Code
skills, native Genie features, or the existing [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/).

---

| # | Idea | Type | Status |
|---|---|---|---|
| [1](./01-multi-turn-eval.md) | Multi-Turn Conversation Evaluation | MCP | Designed |
| [2](./02-workspace-usage-analytics.md) | Workspace-Wide Usage Analytics | MCP | Exploring |
| [3](./03-agent-diff.md) | Agent Comparison & Diff | MCP | Draft |
| [4](./04-agent-migration.md) | Agent Migration & Portability | MCP | Draft |
| [5](./05-impact-analysis.md) | Multi-Agent Impact Analysis (UC Lineage) | MCP | Draft |
| [6](./06-slash-commands.md) | Custom Slash Commands | Extension | Draft |

## Prioritization Notes

- Items 1-5 are candidates for MCP servers (like the existing `mcp-genie-agent-versioning`).
- Item 6 is a candidate for a non-MCP Genie Code extension.
- Several directions (analytics + impact analysis) could share a common "Agent index" that
  periodically crawls the workspace and materializes metadata to UC.
