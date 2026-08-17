# genie-code-plugins

Plugins and extensions for [Databricks Genie Code](https://docs.databricks.com/aws/en/genie-code/).

## MCP Servers

| Plugin | Description |
| --- | --- |
| [`mcp-genie-agent-versioning`](./mcp-genie-agent-versioning/) | Prompt-routed Genie Agent configuration version store on Databricks Apps. Provides save, list, get, and restore tools for Genie Agent configurations with OBO auth and Unity Catalog persistence. |

## Development

Each plugin directory is self-contained with its own `pyproject.toml`, `requirements.txt`, and tests. See the README inside each plugin for setup, deployment, and local verification instructions.
