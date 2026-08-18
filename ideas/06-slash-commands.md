# 6. Custom Slash Commands

**Type:** Non-MCP Genie Code extension

Can Genie Code be extended with custom slash commands (e.g. `/audit-agent`, `/review-sql`,
`/suggest-questions`)? If so, a library of Genie-Agent-specific slash commands would be a
lightweight, non-MCP way to streamline common workflows.

## Idea

A set of slash command definitions and their backing prompts / tool chains for
common Genie Agent tasks:

- `/audit-agent <space-id>` — Run a comprehensive review covering instructions, SQL
  functions, example questions, and data source coverage.
- `/suggest-questions <space-id>` — Analyze the data model and generate diverse, realistic
  example questions.
- `/review-instructions <space-id>` — Check instructions for clarity, completeness, and
  alignment with the data model.
- `/agent-health <space-id>` — Summarize recent usage, errors, and feedback for an Agent.

## Open question

What is the extension point for custom slash commands in Genie Code? Can
they be defined in workspace files, or do they require a different mechanism?
