# SPEC.md — Databricks Genie Workbench Agent Skills + MCP Server

Status: draft 0.3
Target location: subdirectory inside `databricks-solutions/databricks-genie-workbench`
Primary user: Databricks users who want Genie Workbench workflows through Genie Code Agent mode, backed by an MCP server hosted by the existing Workbench Databricks App.

## 1. Summary

Build an Agent Skills bundle for Databricks Genie Code that delegates all deterministic logic to an MCP (Model Context Protocol) server exposed by the existing Genie Workbench Databricks App. Skills contain workflow instructions; the MCP server contains every action the agent can take. There is no second Python implementation of Workbench logic — the MCP server is a route group inside the Workbench backend that adapts existing services (scanner, create agent, GSO optimizer, space update) into MCP tools and resources.

This shape lets users drive create / score / optimize from inside Genie Code without leaving their development context, while keeping a single source of truth for scoring rubrics, validators, optimizer engines, and applied changes. The Workbench app remains the operational unit; its React UI is optional and can be disabled when an organization only needs the agent surface.

## 2. Architecture: skills + MCP server hosted by Workbench

### 2.1 Components and roles

**Genie Code (Agent mode).** The user-facing surface. Routes user intent to skills by `name` / `description`. Invokes MCP tools and renders results conversationally. Owns multi-turn dialog and approval prompts. Does not run any Genie Workbench logic locally.

**Agent Skills bundle.** A small set of `SKILL.md` files installed under `.assistant/skills/`. Each skill is a Markdown workflow that names the MCP tools to call, the order to call them in, what to ask the user before each step, and how to interpret results. Skills contain no Python logic — they are pure orchestration. References and assets are static templates and rubric documentation.

**MCP server (inside the Workbench app).** A FastAPI route group inside the existing Workbench backend. Exposes Workbench's existing services as MCP tools (actions) and MCP resources (read-only data). Authenticates Genie Code clients with the Workbench app's OAuth pass-through. Runs every deterministic operation — scoring, validation, ID hygiene, sort / merge, diff, gate evaluation, PATCH application — as in-process Python calls against existing Workbench services.

**Workbench Databricks App.** The host. Owns Lakebase, optimizer state tables, scan inventory, GSO Lakeflow job bootstrap, MLflow tracing, and (optionally) the React UI. Its existing service layer is unchanged; the MCP route group is a new consumer of those services.

### 2.2 Request flow

```
[User in Genie Code]
       |
       |  "@genie-space-score 3c409c00..."
       v
[Genie Code Agent mode]
   - matches skill by name/description
   - reads skills/genie-space-score/SKILL.md
   - calls MCP tool: score_space(space_id="...")
       |
       |  HTTPS + OAuth pass-through (user identity)
       v
[Workbench App: MCP route group  (backend/mcp/)]
   - validates auth context
   - dispatches to backend/services/scanner.py
       |
       v
[Workbench backend services]
   - scanner reads serialized_space
   - enriches via UC metadata
   - reads optimization history from Lakebase
   - returns deterministic score
       |
       v
[MCP route group]
   - serializes response per MCP tool schema
       |
       v
[Genie Code Agent mode]
   - renders Markdown report inline
   - optionally writes artifact to user workspace folder
   - prompts user for next action
```

Mutations (`create_genie_space`, `bootstrap_gso_job`, `apply_optimization_result`) follow the same flow but require an approval token issued by a prior validation tool and presented back to the mutating tool. The approval prompt is enforced in the skill instructions; the token is the cryptographic guard that prevents the agent from skipping the prompt.

### 2.3 Why this shape

- **Single source of truth.** Every rubric, validator, and optimizer change lands in Workbench services and is immediately reflected in MCP tool behavior. No parity tracking, no version-pinned baselines, no drift.
- **Determinism without local Python.** Genie Code clients do not need a Python environment, wheel installation, or `PYTHONPATH` manipulation. The MCP server is the runtime.
- **Centralized state.** Run history, scan inventory, optimizer outputs, and applied change events live in Lakebase as they already do. The agent surface and the UI surface read the same tables.
- **Centralized governance.** Approval gates, identity checks, and audit logs are enforced server-side, not by client convention.
- **Slim deploy when desired.** Organizations that only want the agent surface can deploy Workbench with the React UI disabled. The backend is unchanged.

### 2.4 Repository placement

Both the skills bundle and the MCP server live inside `databricks-solutions/databricks-genie-workbench`. This is a subdirectory within the existing repo, not a separate project, not a submodule.

```text
databricks-genie-workbench/                  # existing repo
  backend/
    services/                                 # existing Workbench services (unchanged)
    routers/
      mcp.py                                  # NEW: MCP route registration
    mcp/                                      # NEW: MCP server module
      __init__.py
      server.py                               # MCP protocol handler
      auth.py                                 # OAuth context bridge
      approvals.py                            # token issuance + verification
      tools/
        spaces.py
        create.py
        score.py
        optimize.py
      resources/
        spaces.py
        runs.py
  packages/
    genie-skills/                             # NEW: installable skills bundle
      plugin.json
      README.md
      install.py
      build.py
      skills/
        genie-space-create/
        genie-space-score/
        genie-space-optimize/
      tests/
        static/
        integration/
    genie-space-optimizer/                    # existing
  databricks.yml                              # existing
```

Rationale for in-repo placement (versus submodule or standalone repo):

- The MCP server's only job is to expose Workbench services. Keeping it next to those services means tools are function calls, not RPC.
- Logic changes (scanner rubric, validator rules, optimizer levers) ship in the same commit as MCP tool changes. No drift, no parity skill, no version coordination.
- Single release train. Bundle release artifacts are produced as part of Workbench's release.
- One issue tracker, one CI surface, one set of integration tests against Lakebase.

This project does not include a `genie-workbench-parity` skill — the parity problem does not exist when the MCP server and Workbench services share a process.

## 3. Product goals

1. Provide task-specific Genie Code skills for the core Genie Workbench lifecycle:
   - Create a new Genie Space from business requirements and Unity Catalog sources.
   - Score an existing Genie Space for readiness and optimization suitability.
   - Run a benchmark-driven optimization workflow to improve benchmark accuracy.
2. Expose every deterministic action as an MCP tool backed by the existing Workbench service layer. No second implementation.
3. Package the skills bundle as a downloadable artifact that can be installed into a user or workspace skills folder.
4. Make the MCP server discoverable and connectable from Genie Code with one configuration step against the Workbench App URL.
5. Reuse Workbench's existing state model (Lakebase tables, optimizer state, change events) so agent runs and UI runs are visible to each other.

## 4. Non-goals

1. Do not maintain a separate Python implementation of scoring, validation, optimizer, or apply logic. Skills must call MCP tools, not local scripts.
2. Do not require workspace-admin permissions for installing the skills bundle into a user skills folder. (Workspace-admin is needed to deploy or upgrade the Workbench app, which is a separate operational concern.)
3. Do not auto-apply destructive or irreversible changes without an explicit user approval step, enforced server-side in the MCP layer.
4. Do not implement the deprecated standalone readiness-remediation workflow as a skill; remediation is part of optimization apply, behind approval gates.
5. Do not add a parity-tracking skill; both surfaces ship together.
6. Do not assume Genie Code clients have a Python runtime, the Databricks SDK, or workspace files access. Skills must function MCP-only.

## 5. External compatibility requirements

### 5.1 Agent Skills format

Each user-facing skill is a folder containing a required `SKILL.md` with YAML frontmatter (`name`, `description`, plus metadata) and Markdown instructions. Skill names are lowercase, hyphenated, and match the parent folder.

Skill folders may include:

```text
references/   # task-specific Markdown docs, schemas, checklists, examples
assets/       # templates and static input schemas
```

Skills do not contain `scripts/` directories. All actions are MCP tool calls.

### 5.2 Databricks Genie Code installation paths

```text
/Users/{username}/.assistant/skills/      # user skills (default)
Workspace/.assistant/skills/              # workspace skills
```

### 5.3 MCP protocol

The MCP server speaks Model Context Protocol over HTTP/SSE.

- Endpoint: `https://<workbench-app-host>/mcp`.
- Authentication: OAuth pass-through using the Workbench Databricks App's identity flow. The user authenticates once to the app; Genie Code reuses that token for MCP requests.
- Tool list and tool schemas are advertised through standard MCP discovery.
- Each tool response includes structured content (JSON) and an optional human-readable summary.
- The server exposes a `server_info` resource carrying the Workbench app version for compatibility checks.

### 5.4 Databricks Genie Space APIs

The MCP server is the only component that calls Databricks Genie REST APIs. Skills never call them directly. Underlying operations exposed through MCP tools:

- List spaces.
- Get a space and read `serialized_space`.
- Create a space (`POST /api/2.0/genie/spaces`).
- Update a space (`PATCH /api/2.0/genie/spaces/{space_id}`).
- Start conversations and retrieve generated SQL for benchmark runs.
- Native Genie evaluation endpoints when available and useful.

### 5.5 `serialized_space` constraints

Validation rules remain authoritative and are enforced inside the MCP `validate_serialized_space` tool, implemented by Workbench's existing `serialized_space` service:

- `version` is required and should be `2` for new spaces unless Databricks changes the supported schema.
- Required IDs must be 32-character lowercase hexadecimal strings.
- Collections must be sorted by documented keys before create or update.
- Question IDs must be unique across sample questions and benchmark questions.
- Instruction IDs must be unique across text instructions, example SQLs, SQL functions, join specs, filters, expressions, and measures.
- Column configs must be unique by `(table_identifier, column_name)`.
- String fields must respect documented length limits.
- Only one text instruction is allowed per space.
- Join specs must use the required relationship annotation format.
- Table identifiers must use three-level `catalog.schema.table` names.
- Benchmark answers must have exactly one answer with format `SQL`.
- SQL snippet SQL fields cannot be empty.

Skills must call `validate_serialized_space` before any create or update step.

## 6. User personas and workflows

### 6.1 Genie Space developer

```text
@genie-space-create Build a Genie Space for sales performance using catalog.sales.orders and catalog.sales.customers.
```

```text
@genie-space-score Score space 3c409c00b54a44c79f79da06b82460e2 and tell me what is missing before optimization.
```

```text
@genie-space-optimize Run optimization for this space and show me accuracy before applying changes.
```

### 6.2 Data platform team

```text
@genie-space-score Scan all spaces I can manage and write a readiness report to my workspace folder.
```

The MCP server returns the score data; the skill instructs the agent to render Markdown and write it to the user's workspace folder via Genie Code's filesystem tools. The server simultaneously persists a row in `genie_skill_scores` for cross-surface visibility.

### 6.3 Workbench app operator

The team operating the Workbench app deploys it once. Both the UI and the MCP route group are enabled by default; the UI can be disabled via a deploy flag for agent-only deployments. MCP tool list, version, and connected client count are visible in the app's standard observability surface.

## 7. Skill catalog

### 7.1 `genie-space-create`

Purpose: Build a new Genie Space from requirements through MCP tool calls; create only after explicit approval.

When it should activate:

- User asks to create, build, scaffold, or configure a Genie Space.
- User asks to turn business requirements + UC tables into a Genie Space.
- User asks for sample questions, example SQLs, benchmarks, joins, measures, filters, expressions, or text instructions for a new space.

Bundled assets:

```text
skills/genie-space-create/
  SKILL.md
  references/create-workflow.md
  references/space-plan-schema.md
  references/serialized-space-rules.md
  references/gsl-instruction-template.md
  assets/space-plan-template.json
```

MCP tools the skill should call (defined in §9):

- `discover_uc_assets`
- `inspect_table`
- `profile_columns`
- `validate_space_plan`
- `assemble_serialized_space`
- `validate_serialized_space`
- `test_sql`
- `create_genie_space`

Workflow:

1. Gather business context, audience, terminology, default assumptions, target folder.
2. `discover_uc_assets` to find candidate tables and metric views.
3. `inspect_table` and `profile_columns` for selected sources.
4. Generate plan sections (LLM work, guided by skill instructions and `references/`).
5. `test_sql` for every example and benchmark SQL.
6. Repair or drop invalid SQL artifacts.
7. `assemble_serialized_space` then `validate_serialized_space` (validation issues an approval token if clean).
8. Present plan and diff for user approval.
9. After explicit approval: `create_genie_space` with the approval token.
10. Skill writes plan, validation, and create result artifacts to the user's workspace folder via Genie Code's filesystem tools. The MCP server simultaneously persists a `runs` row in Lakebase.

Safety rules (server-enforced where possible):

- `create_genie_space` rejects calls without a valid approval token bound to the same `serialized_space` payload hash.
- PII flags surface in `inspect_table` results; skill instructions tell the agent to confirm before including flagged columns.
- `validate_serialized_space` rejects invented categorical values (no surrogate value source).
- Length limits and "no SQL in text instructions" are enforced by `validate_serialized_space`.

### 7.2 `genie-space-score`

Purpose: Score readiness using Workbench's deterministic scanner exposed as MCP tools.

When it should activate:

- User asks to score, scan, grade, assess, audit, or check readiness of a space.
- User asks whether a space is ready to optimize.
- User asks for missing metadata, missing examples, missing benchmarks, or quality gaps.

Bundled assets:

```text
skills/genie-space-score/
  SKILL.md
  references/iq-rubric.md
  references/score-output-schema.md
  references/readiness-next-steps.md
```

MCP tools:

- `score_space`
- `score_all_spaces`
- `get_space_findings`
- `render_score_report`

Score model: identical to Workbench's current readiness model — implemented exactly once, in Workbench's scanner service. The deterministic checks remain:

| # | Check | Pass rule |
|---|---|---|
| 1 | Data sources exist | At least one table or metric view configured |
| 2 | Table descriptions | At least 80% of tables have descriptions, including UC-enriched comments |
| 3 | Column descriptions | At least 50% of columns have descriptions, including UC-enriched comments |
| 4 | Text instructions | Present and more than 50 characters total |
| 5 | Join specifications | Present for multi-source spaces |
| 6 | Data source count | Between 1 and 12 tables plus metric views |
| 7 | Example SQLs | At least 8 example question-SQL pairs |
| 8 | SQL snippets | At least one function, expression, measure, or filter |
| 9 | Entity/format matching | At least one column has entity matching or format assistance |
| 10 | Benchmark questions | At least 10 benchmark questions |
| 11 | Optimization workflow completed | Terminal optimization run exists |
| 12 | Optimization accuracy | Best optimization accuracy is at least 85% |

Maturity tiers:

- `Trusted`: all checks pass.
- `Ready to Optimize`: checks 1–10 pass.
- `Not Ready`: any check in 1–10 fails.

`score_space` returns both `score` (0–12) and `score_percent` (`score / 12 * 100`).

Workflow:

1. Resolve target space (one or many).
2. `score_space` (or `score_all_spaces`) returns score, findings, recommended next steps, warnings.
3. Optional `render_score_report` for a Markdown report.
4. Skill writes outputs to user's workspace folder; the server persists a row in `genie_skill_scores`.

### 7.3 `genie-space-optimize`

Purpose: Run benchmark-driven optimization through MCP, with apply gated by explicit user approval.

When it should activate:

- User asks to optimize a space for accuracy.
- User asks to run benchmark eval, measure SQL quality, diagnose failures, improve pass rate.
- User asks to run Auto-Optimize / GSO-like workflow.

Bundled assets:

```text
skills/genie-space-optimize/
  SKILL.md
  references/optimization-workflow.md
  references/lever-catalog.md
  references/evaluation-gates.md
  references/apply-review-checklist.md
```

MCP tools:

- `preflight_optimization`
- `bootstrap_gso_job`
- `start_optimization_run`
- `get_optimization_run`
- `get_optimization_changes`
- `apply_optimization_result`

Optimization modes (both backed by Workbench's existing optimizer):

- **Mode A — Full GSO mode.** Uses Workbench's `packages/genie-space-optimizer` engine and Lakeflow Job. `bootstrap_gso_job` is a privileged tool requiring approval. Supports the same lever categories (tables / columns, metric views, table-valued functions, join specs, instructions / example SQL) and 3-gate evaluation (slice, P0, full benchmark).
- **Mode B — Lightweight in-app mode.** Runs benchmark eval inside the Workbench backend without the GSO job. Sufficient for small spaces and quick experiments. `start_optimization_run` selects the mode based on availability and user request.

Preflight requirements (validated by `preflight_optimization`):

- User can manage or edit the target Genie Space.
- A SQL warehouse is available with CAN USE.
- User identity (or configured job identity) can read referenced UC tables.
- 10+ benchmark questions or candidate generation approved.
- `serialized_space` passes validation.
- For full GSO mode: MLflow / Prompt Registry / UC state schema prerequisites pass.

Apply rules (server-enforced):

- Default `apply_mode` is `staged`. `apply_optimization_result` returns a change artifact and does not PATCH the live space.
- `apply_mode=auto` requires (a) explicit user request via skill prompt, (b) accuracy non-regression vs. baseline, (c) all gates passed.
- Apply path: re-fetch live space → merge changes → sanitize IDs → validate → diff → require approval token → PATCH → rescore. All inside the MCP server.

## 8. Bundle and server design

### 8.1 Skills bundle layout

```text
packages/genie-skills/
  plugin.json
  README.md
  install.py
  build.py
  skills/
    genie-space-create/
      SKILL.md
      references/
      assets/
    genie-space-score/
      SKILL.md
      references/
      assets/
    genie-space-optimize/
      SKILL.md
      references/
      assets/
  tests/
    static/             # SKILL.md validation, MCP tool reference checks
    integration/        # opt-in tests against a running Workbench app
```

No `src/` Python package. No per-skill `scripts/` directory.

### 8.2 Distribution artifact

`python packages/genie-skills/build.py` produces:

```text
dist/databricks-genie-skills-<version>.zip
```

Zip contents:

```text
plugin.json
README.md
install.py
skills/
  genie-space-create/
  genie-space-score/
  genie-space-optimize/
```

The bundle ships zero executable Python beyond the installer.

### 8.3 Plugin manifest

```json
{
  "name": "databricks-genie-skills",
  "version": "0.3.0",
  "description": "Agent Skills bundle for Databricks Genie Spaces, backed by the Genie Workbench MCP server.",
  "skills": [
    "genie-space-create",
    "genie-space-score",
    "genie-space-optimize"
  ],
  "default_install_scope": "user",
  "supports_workspace_install": true,
  "mcp_server": {
    "required": true,
    "min_workbench_version": "<workbench-version>",
    "endpoint_template": "https://<workbench-host>/mcp",
    "auth": "oauth-passthrough",
    "tool_namespace": "genie"
  }
}
```

`min_workbench_version` is the only compatibility pin needed — there is no separate baseline ref because skills and MCP server ship from the same repo.

### 8.4 Install commands

```bash
python install.py --profile DEFAULT --scope user --workbench-host <host>
python install.py --profile DEFAULT --scope workspace --workbench-host <host>
```

Installer responsibilities:

1. Validate `plugin.json` and every `SKILL.md`.
2. Resolve target skills directory.
3. Copy skill folders.
4. Write `<skills>/genie-mcp.config.json` with the resolved Workbench MCP endpoint.
5. Probe the MCP endpoint to confirm reachability and version compatibility (refuse if Workbench version < `min_workbench_version`).
6. Preserve user-modified skill files unless `--overwrite`.
7. Write `install_result.json` locally and optionally to the workspace output folder.

Target workspace structure after user install:

```text
/Users/{username}/.assistant/skills/
  genie-space-create/
  genie-space-score/
  genie-space-optimize/
  genie-mcp.config.json
```

### 8.5 MCP server module

Lives in `backend/mcp/` inside the Workbench app:

```text
backend/mcp/
  __init__.py
  server.py                # MCP protocol handler, tool / resource registry
  auth.py                  # OAuth context bridge to existing app auth
  approvals.py             # approval token issuance + verification
  tools/
    spaces.py              # list_spaces, get_space, get_serialized_space
    create.py              # discover_uc_assets, inspect_table, profile_columns,
                           # validate_space_plan, assemble_serialized_space,
                           # validate_serialized_space, test_sql, create_genie_space
    score.py               # score_space, score_all_spaces, get_space_findings,
                           # render_score_report
    optimize.py            # preflight_optimization, bootstrap_gso_job,
                           # start_optimization_run, get_optimization_run,
                           # get_optimization_changes, apply_optimization_result
  resources/
    spaces.py              # genie://spaces/{space_id}/serialized_space
    runs.py                # genie://runs/{run_id}/optimization_report
```

Each tool is a thin function that calls existing Workbench services. No business logic is reimplemented in the MCP layer.

## 9. MCP tool catalog

### 9.1 Space identity and state (`tools/spaces.py`)

| Tool | Inputs | Output | Backed by |
|---|---|---|---|
| `list_spaces` | optional filter, `manage_only?` | array of `{space_id, title, owner, modified}` | `services/spaces.list_spaces` |
| `get_space` | `space_id` | metadata + permissions summary | `services/spaces.get_space` |
| `get_serialized_space` | `space_id` | full `serialized_space` JSON | Genie API via `services/genie_api` |

### 9.2 Create (`tools/create.py`)

| Tool | Inputs | Output |
|---|---|---|
| `discover_uc_assets` | search text, filters | matched catalogs / schemas / tables / metric views |
| `inspect_table` | three-level identifier | comments, columns, types, PII flags, sample-distinct values, date ranges, null rates |
| `profile_columns` | identifier, columns | profiling stats only (used after agent narrows scope) |
| `validate_space_plan` | plan JSON | normalized plan + warnings |
| `assemble_serialized_space` | plan JSON | candidate `serialized_space` |
| `validate_serialized_space` | `serialized_space` | errors, warnings, approval token if clean |
| `test_sql` | sql, warehouse_id, optional params | execution status + small preview |
| `create_genie_space` | title, description, parent_path, warehouse_id, `serialized_space`, approval_token | created space metadata + `space_id` |

### 9.3 Score (`tools/score.py`)

| Tool | Inputs | Output |
|---|---|---|
| `score_space` | `space_id` | score, score_percent, maturity, findings, next_steps, warnings |
| `score_all_spaces` | optional filter, optional `manage_only=true` | list of score records |
| `get_space_findings` | `space_id`, `run_id?` | full findings detail |
| `render_score_report` | `score_run_id` | Markdown report |

### 9.4 Optimize (`tools/optimize.py`)

| Tool | Inputs | Output |
|---|---|---|
| `preflight_optimization` | `space_id`, `mode?` | preflight report + selected mode |
| `bootstrap_gso_job` | options, approval_token | job id + status |
| `start_optimization_run` | `space_id`, `mode`, config | `run_id` |
| `get_optimization_run` | `run_id` | run status + accuracy + accepted / rejected counts |
| `get_optimization_changes` | `run_id` | staged change set + per-change rationale |
| `apply_optimization_result` | `run_id`, accepted_change_ids, approval_token, `apply_mode` | applied diff + new space version |

### 9.5 Resources

- `genie://spaces/{space_id}/serialized_space` — read-only fetch
- `genie://spaces/{space_id}/score_report/latest` — most recent score Markdown
- `genie://runs/{run_id}/optimization_report` — optimization Markdown
- `genie://server_info` — Workbench app version, MCP server version, available tool list, transport

Resources let the LLM pull bulky context on demand without consuming tool calls.

### 9.6 Approval tokens

Tools that mutate live state (`create_genie_space`, `bootstrap_gso_job`, `apply_optimization_result`) require an approval token. Tokens are issued by `validate_serialized_space` (for create) or `get_optimization_changes` (for apply). They are short-lived (minutes), single-use, scoped to a specific space + payload hash, and verifiable server-side.

The user-facing approval is the agent's confirmation prompt; the token is the cryptographic guard that prevents the agent from skipping the prompt. Tokens are not surfaced to the user and not part of the conversation transcript — the skill receives them as opaque strings from one tool and passes them to the next.

## 10. Artifact and history model

The system of record lives in Workbench's existing tables:

- `genie_skill_runs` — every MCP-driven run (skill invocation chain)
- `genie_skill_scores` — score outputs
- `genie_skill_optimization_runs` — optimization runs + accuracy
- `genie_skill_change_events` — applied changes with before / after diffs

These are the same tables Workbench's UI surface reads and writes; agent runs and UI runs are visible to each other.

User-facing artifacts (Markdown reports, plan JSONs) are written by the agent into the user's workspace folder via Genie Code's filesystem tools, using paths suggested by MCP tools. Local artifacts are convenience copies for human review, not the system of record.

Default agent artifact root:

```text
/Workspace/Users/{username}/.genie-skills/outputs/
```

Each MCP run writes a record to Lakebase. The agent may additionally maintain a local `outputs/index.jsonl` for the user's own browsing, but this is not authoritative.

## 11. Permissions and identity model

### 11.1 User identity (default)

OAuth pass-through. The user authenticates to the Workbench Databricks App. Genie Code's MCP client reuses the access token. The MCP server propagates the user's identity to:

- Unity Catalog discovery.
- SQL warehouse execution.
- Genie create / update operations.
- Lakebase reads and writes that are user-scoped.

### 11.2 Service-principal identity for jobs

Full GSO mode requires a Lakeflow Job that runs as either the user or a configured service principal. Configuration of the SP is done through Workbench app settings (admin path), not silently inferred. The MCP `bootstrap_gso_job` tool surfaces the SP requirement and refuses to create a job with an unconfigured identity. Preflight checks remain:

- The service principal can manage the target Genie Space if it will apply changes.
- The service principal can use the SQL warehouse.
- The service principal can read referenced schemas.
- The service principal can write optimizer state tables.

### 11.3 Approval boundaries (server-enforced)

The MCP server requires explicit user-issued approval tokens before:

- Creating a Genie Space.
- Updating a live Genie Space.
- Bootstrapping or updating the GSO job.
- Creating UC schemas or Delta tables outside the Workbench-managed namespace.
- Running long or expensive optimization jobs.
- Applying optimized config to production spaces.

Skills are responsible for prompting the user; the MCP server is responsible for refusing if no token is present.

## 12. Skill authoring standards

Every `SKILL.md` includes:

1. Frontmatter:

```yaml
---
name: genie-space-score
description: Score, scan, and assess Databricks Genie Spaces for readiness using the Genie Workbench quality rubric. Use when the user asks to score a Genie Space, check readiness, identify missing metadata, or determine whether a space is ready to optimize.
license: Databricks License
compatibility: Designed for Databricks Genie Code Agent mode. Requires the Databricks Genie Workbench MCP server.
metadata:
  bundle: databricks-genie-skills
  workbench_feature: iq-scanner
  mcp_tool_namespace: genie
---
```

2. Workflow overview.
3. Exact MCP tools to invoke and the order of invocation.
4. Required inputs for each tool.
5. Required outputs and how to render them.
6. Human approval points (which tools issue tokens, which require them).
7. Failure handling (server error categories and recommended retries).
8. References to bundled docs via relative paths.
9. Examples of user requests.

Skills must not embed business logic. If a skill's instructions describe "how to compute X," that is a hint to add or extend an MCP tool, not to inline the computation.

## 13. Compatibility versioning

Skills and MCP server ship from the same repo. Versioning is governed by:

- `plugin.json` `version` — bundle version.
- `plugin.json` `mcp_server.min_workbench_version` — minimum Workbench app version that exposes all MCP tools the bundle requires.
- Workbench app exposes its version through the MCP `server_info` resource.

The installer probes the configured Workbench host and refuses to install if the app version is below `min_workbench_version`. The MCP server, in turn, advertises tool list and schemas through standard MCP discovery so older bundles continue to function as long as they only call tools that still exist.

Tool deprecations follow standard MCP practice: mark deprecated, retain for one minor cycle, remove. Skill bundles must update before relying on a replacement.

## 14. Testing

### 14.1 Static validation

- Validate every `SKILL.md` against the Agent Skills spec.
- Validate `plugin.json` schema.
- Validate that every MCP tool referenced in skill instructions exists in the live tool registry of the targeted Workbench version (a build-time compatibility check).
- Validate no skill embeds business logic that should be a tool.
- Validate no `genie-workbench-parity` skill folder is reintroduced.

### 14.2 MCP server unit tests

Tests live alongside `backend/mcp/`:

- Tool input / output schema fidelity.
- Approval token issuance, expiry, and payload-hash binding.
- Auth context propagation to underlying services.
- Error normalization (Genie API → MCP error categories).
- Apply path: re-fetch + merge + diff + sanitize + revalidate.

### 14.3 Backend service unit tests (existing)

Workbench's existing tests for scanner, optimizer, `serialized_space`, and `space_update` remain authoritative. The MCP layer reuses them.

### 14.4 Integration tests (opt-in)

Run against a real Workbench deployment connected to a real Databricks workspace:

- Install bundle to user skills path.
- MCP probe returns tool list and matches the bundle's expectations.
- Score an existing space via skill → MCP → service.
- Create a test Genie Space from a small known schema.
- Run lightweight benchmark evaluation.
- Stage an optimization change without applying it.
- Apply a harmless approved optimization change to a disposable test space.
- Optionally bootstrap and trigger full GSO mode.

### 14.5 Safety tests

- `create_genie_space` refuses without a valid approval token.
- `apply_optimization_result` refuses without a valid approval token.
- Tokens are bound to one payload hash; re-use is rejected.
- PII flags surface in `inspect_table` results.
- Invalid `serialized_space` is not accepted by `validate_serialized_space`.
- Optimizer does not apply accuracy-regressing changes.
- Service principal configuration cannot be silently inferred or created.

## 15. Operational requirements

### 15.1 Logging

MCP tool calls log to Workbench's existing logging stack with:

- User identity.
- Tool name + input hash (PII-redacted).
- Outcome and duration.
- Approval token issuance and consumption events.

### 15.2 Error handling

MCP errors include:

- Error category (`auth`, `validation`, `permission`, `not_found`, `conflict`, `transient`, `internal`).
- Object involved (space_id, run_id, table identifier).
- Whether retry is safe.
- Suggested next action for the agent.

### 15.3 Dependency management

MCP server dependencies are part of Workbench's existing `pyproject.toml` (FastAPI, databricks-sdk, MCP server library, etc.). The skills bundle has minimal Python dependencies — only the installer needs anything beyond the standard library.

### 15.4 Security

- OAuth tokens are never persisted in skill artifacts.
- MCP responses redact secrets and known-sensitive fields.
- Profiling samples are size-limited.
- Approval tokens are short-lived and bound to payload hashes.
- The skills bundle ships zero executable Python beyond the installer; tools, validators, and apply logic only run server-side.

## 16. Milestones

### Milestone 1 — MCP server skeleton

Deliverables:

- `backend/mcp/server.py` with protocol handler.
- Auth bridge to existing app auth.
- One read-only tool (`get_serialized_space`) end-to-end.
- MCP discovery returns tool list.
- `server_info` resource.

Acceptance: Genie Code can connect to the MCP endpoint and call `get_serialized_space`.

### Milestone 2 — Skills bundle scaffold

Deliverables:

- `packages/genie-skills/` with `plugin.json`, three skill folders, installer, builder.
- Static validation tests.
- `genie-mcp.config.json` written by installer.

Acceptance: Bundle installs to a user skills folder; Genie Code discovers skill descriptions; installer refuses on version mismatch.

### Milestone 3 — Score path

Deliverables:

- MCP tools: `list_spaces`, `get_space`, `score_space`, `score_all_spaces`, `get_space_findings`, `render_score_report`.
- `genie-space-score` `SKILL.md` and references.
- Resource: `genie://spaces/{space_id}/score_report/latest`.

Acceptance: User can score a space end-to-end through Genie Code with output identical to Workbench's UI scanner.

### Milestone 4 — Create path

Deliverables:

- MCP tools: `discover_uc_assets`, `inspect_table`, `profile_columns`, `validate_space_plan`, `assemble_serialized_space`, `validate_serialized_space`, `test_sql`, `create_genie_space`.
- Approval token issuance bound to validation.
- `genie-space-create` `SKILL.md` and references.

Acceptance: User can create a valid Genie Space from selected UC tables. Generated config passes validation before create. Output artifacts written.

### Milestone 5 — Lightweight optimization path

Deliverables:

- MCP tools: `preflight_optimization`, `start_optimization_run` (in-app mode), `get_optimization_run`, `get_optimization_changes`, `apply_optimization_result`.
- Approval token bound to staged change set.
- `genie-space-optimize` `SKILL.md` and references.

Acceptance: User can run baseline + lightweight optimization; apply requires approval token; regression gates enforced server-side.

### Milestone 6 — Full GSO mode

Deliverables:

- MCP tool: `bootstrap_gso_job`.
- Mode selection inside `start_optimization_run`.
- Lakeflow job ingestion into MCP run state.

Acceptance: User can bootstrap and trigger Workbench-style GSO from Genie Code. The optimization report shows baseline, final accuracy, accepted changes, and rejected changes.

### Milestone 7 — Compatibility versioning and release

Deliverables:

- `min_workbench_version` enforcement in installer.
- MCP `server_info` resource.
- Bundle release flow as part of Workbench's release pipeline.

Acceptance: A user installing the bundle against an older Workbench app receives an actionable error before any tool call. Bundle release artifacts are produced alongside Workbench releases.

## 17. Open decisions

1. **MCP transport details.** HTTP/SSE is the assumed transport (standard for app-hosted MCP). Confirm Genie Code's supported transports and authentication modes before final design.
2. **UI-disabled deploy path.** Decide whether Workbench should ship a documented UI-disabled deploy mode, or whether agent-only deployments are an org-level configuration concern not officially supported.
3. **Resource granularity.** Decide which Markdown reports are exposed as MCP resources (read-only, agent-pulled) versus returned inline by tools. Default for MVP: tools return inline; resources are added when context size becomes a problem.
4. **Native Genie evaluation API surface.** When Databricks ships native eval APIs, decide whether they replace lightweight in-app eval or augment it. Currently treated as an internal optimization detail.
5. **Approval token UX.** Recommendation: tokens stay invisible to the user — the user approves a human-readable diff; the token plumbing is hidden from the conversation.
6. **Multi-tenant Workbench deployments.** If a single Workbench instance serves multiple workspaces, decide whether `server_info` discloses workspace boundaries or whether each workspace runs its own deployment.

## 18. Reference documents

- Databricks Genie Code Agent Skills: https://docs.databricks.com/aws/en/genie-code/skills
- Agent Skills specification: https://agentskills.io/specification
- Model Context Protocol specification: https://modelcontextprotocol.io/specification
- Databricks Genie API and `serialized_space` schema: https://docs.databricks.com/aws/en/genie/conversation-api
- Databricks Genie best practices: https://docs.databricks.com/aws/en/genie/best-practices
- Genie Workbench repo (this project's host): https://github.com/databricks-solutions/databricks-genie-workbench
- Genie Workbench create agent docs: `docs/04-create-agent.md`
- Genie Workbench IQ scanner docs: `docs/05-iq-scanner.md`
- Genie Workbench Auto-Optimize docs: `docs/07-auto-optimize.md`
- Genie Workbench authentication and permissions docs: `docs/03-authentication-and-permissions.md`
