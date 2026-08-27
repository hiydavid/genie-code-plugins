# Genie Code Plugin Ideas

Ideas for plugins, MCPs, tools, and other extensions that augment Genie One / Genie Agents
through Genie Code. These focus on product gaps not already covered by native Genie Code
skills, native Genie features, or the existing [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/).

---

| # | Idea | Type | Status |
|---|---|---|---|
| [1](./01-multi-turn-eval.md) | Multi-Turn Conversation Evaluation | MCP | Designed |
| [2](./02-workspace-usage-analytics.md) | Workspace-Wide Usage Analytics | Genie Code skill + sibling app provisioning UC MVs (versioning-MCP bootstrap pattern) | Designed |
| [4](./04-agent-migration.md) | Agent Migration & Portability | Genie Code workspace skill | Designed |
| [5](./05-impact-analysis.md) | Multi-Agent Impact Analysis (UC Lineage) | MCP | Designed |
| [6](./06-agent-production-coach.md) | Agent Production Coach | Markdown playbooks → workspace skill (optional diagnostic MCP later) | Designed |

## Prioritization Notes

- Item 2 was redesigned after research: all required data is plain SQL over system tables
  (billing, query history, audit logs), which Genie Code can already run via the CLI. It
  resolves to a skill with curated SQL recipes plus a sibling Databricks App (sharing the
  versioning MCP's provisioning pattern) that bootstraps materialized views — the common
  "Agent index" below — with a thin optional MCP deferred until a non-CLI consumer exists.
- Several directions (analytics + impact analysis) share that "Agent index": a DAB job that
  periodically materializes per-space usage metrics (item 2) and agent metadata (item 5) to UC.
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
  skills (items 4 and 6) and item 2's analytics skill.
- Several directions (analytics + impact analysis) could share a common "Agent index" that
  periodically crawls the workspace and materializes metadata to UC.
