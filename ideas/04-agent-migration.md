# 4. Agent Migration & Portability

**MCP name:** `mcp-genie-agent-migrate`

DABs (Databricks Asset Bundles) already supports Genie resources, so Genie Agent
definitions can be declared as code and deployed across environments. What would an MCP add?

## Idea

An MCP that helps Genie Code bridge the gap between the live Genie API world and
the DABs/workspace-files world. Possible directions:

- **Live-to-DABs export:** Read a live Genie Agent and generate the DAB YAML + resource
  files that represent it. Genie Code could then refine and commit them.
- **Cross-workspace import:** Given a DABs-style Agent definition (or an exported
  snapshot), create or update an Agent in a target workspace, remapping UC catalog/schema
  references as needed.
- **DABs drift detection:** Compare the live Agent against its DABs source of truth and
  flag any drift (someone edited the Agent in the UI since the last DABs deploy).

## Open question

With DABs already solving the "define as code" piece, what migration scenarios are still
painful enough that Genie Code + an MCP would meaningfully help?
