# Genie Code Plugin Ideas

Ideas for plugins, MCPs, tools, and other extensions that augment Genie One / Genie Agents
through Genie Code. These focus on product gaps not already covered by native Genie Code
skills, native Genie features, or the existing [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/).

---

| # | Idea | Type | Status |
|---|---|---|---|
| [1](./01-multi-turn-eval.md) | Multi-Turn Conversation Evaluation | MCP | Designed |
| [2](./02-workspace-usage-analytics.md) | Workspace-Wide Usage Analytics | MCP | Exploring |
| [4](./04-agent-migration.md) | Agent Migration & Portability | Genie Code workspace skill | Designed |
| [5](./05-impact-analysis.md) | Multi-Agent Impact Analysis (UC Lineage) | MCP | Designed |
| [6](./06-agent-production-coach.md) | Agent Production Coach | Markdown playbooks → workspace skill (optional diagnostic MCP later) | Designed |

## Prioritization Notes

- Items 1, 2, and 5 are candidates for MCP servers (like the existing `mcp-genie-agent-versioning`).
- Item 3 (Agent Comparison & Diff) shipped as the `diff_agent_versions` tool in
  [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/); its design doc was removed
  once implemented.
- Item 4 resolves to a Genie Code workspace skill with an executable script rather than an MCP.
- Item 6 is content-first: diagnosis protocol and playbooks as markdown, then the same
  files packaged as a Genie Code workspace skill. A thin diagnostic MCP is only in scope
  after native inspection proves insufficient. It sequences native Genie Code verbs
  (instructions, benchmarks, eval review); it does not re-implement them.
- A custom slash-commands idea was dropped after research: Genie Code's slash commands
  are not user-extensible, and the underlying workflows are better served by workspace
  skills (items 4 and 6) and the analytics MCP (item 2).
- Several directions (analytics + impact analysis) could share a common "Agent index" that
  periodically crawls the workspace and materializes metadata to UC.
