# Genie Code Plugin Ideas

Ideas for plugins, MCPs, tools, and other extensions that augment Genie One / Genie Agents
through Genie Code. These focus on product gaps not already covered by native Genie Code
skills, native Genie features, or the existing [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/).

---

| # | Idea | Type | Status |
|---|---|---|---|
| [1](./01-multi-turn-eval.md) | Multi-Turn Conversation Evaluation | MCP | Designed |
| [2](./02-workspace-usage-analytics.md) | Workspace-Wide Usage Analytics | MCP | Exploring |
| [3](./03-agent-diff.md) | Agent Comparison & Diff | Tool in `mcp-genie-agent-versioning` | Implementation-ready |
| [4](./04-agent-migration.md) | Agent Migration & Portability | Genie Code workspace skill | Designed |
| [5](./05-impact-analysis.md) | Multi-Agent Impact Analysis (UC Lineage) | MCP | Designed |

## Prioritization Notes

- Items 1, 2, and 5 are candidates for MCP servers (like the existing `mcp-genie-agent-versioning`).
- Item 3 folds into `mcp-genie-agent-versioning` as an additional tool; item 4 resolves to a
  Genie Code workspace skill with an executable script rather than an MCP.
- Item 6 (custom slash commands) was dropped after research: Genie Code's slash commands
  are not user-extensible, and the underlying workflows are better served by the surfaces
  already covered here — workspace skills (item 4's model) and the analytics MCP (item 2).
- Several directions (analytics + impact analysis) could share a common "Agent index" that
  periodically crawls the workspace and materializes metadata to UC.
