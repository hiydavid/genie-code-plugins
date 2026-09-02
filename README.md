# genie-code-plugins

Plugins and extensions for [Databricks Genie Code](https://docs.databricks.com/aws/en/genie-code/).

## MCP Servers

| Plugin | Description |
| --- | --- |
| [`mcp-genie-agent-versioning`](./mcp-genie-agent-versioning/) | Prompt-routed Genie Agent configuration version store on Databricks Apps. Provides save, list, get, and restore tools for Genie Agent configurations with OBO auth and Unity Catalog persistence. |

## Agent Skills

| Skill | Description |
| --- | --- |
| [`genie-ontology-readiness`](./genie-ontology-readiness/) | Evidence-backed, six-layer readiness assessment and guided remediation workflow for launching one business domain with Genie Ontology. |

Install a workspace skill by copying its folder to
`Workspace/.assistant/skills/`. Skills can also be prototyped as user skills under
`/Users/{username}/.assistant/skills/`.

## Ideas

See [`ideas/`](./ideas/) for proposed plugins and extensions under exploration.

## Development

MCP plugin directories are self-contained with their own `pyproject.toml`, requirements,
and tests. Agent skill directories follow the standard `SKILL.md` layout and can include
focused references or executable helpers when needed.
