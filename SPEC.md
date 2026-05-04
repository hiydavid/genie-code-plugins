# SPEC.md — Databricks Genie Workbench Agent Skills Plugin

Status: draft 0.2  
Target repository name: `databricks-genie-workbench-skills`  
Source-of-truth companion project: `databricks-solutions/databricks-genie-workbench`  
Primary user: Databricks users who want Genie Workbench workflows through Genie Code Agent mode without deploying a Databricks App.

## 1. Summary

Build a workspace-installable Agent Skills bundle for Databricks Genie Code. The bundle packages focused user-facing skills plus a shared Python implementation layer that allows a coding agent to create, score, and optimize Databricks Genie Spaces using the same operating model and quality standards as Genie Workbench, but without a FastAPI/React Databricks App.

The project is a companion repo to Genie Workbench. Genie Workbench remains the app-based, UI-first product. This project is the agent-first alternative: users invoke skills in Genie Code Agent mode and the agent runs bundled scripts, reads bundled references, produces auditable artifacts, and calls Databricks APIs directly.

This project should not include a standalone readiness-remediation skill. That Workbench workflow is expected to be deprecated. Any space-update logic required by create or optimization workflows must live in shared code and must only run behind explicit review and approval gates.

## 2. Architecture decision: skill bundle with shared core

The project should use **multiple task-specific skills**, not one large skill.

Recommended skill set:

1. `genie-space-create`
2. `genie-space-score`
3. `genie-space-optimize`
4. `genie-workbench-parity`

The skills should share one implementation package: `genie_workbench_skills`. Each skill folder contains a focused `SKILL.md`, small wrapper scripts, and task-specific reference files. Common logic such as Genie API access, `serialized_space` validation, Unity Catalog discovery, SQL execution, artifact writing, config diffing, and approved configuration application belongs in the shared package.

Rationale:

- Genie Code routes skills by `name` and `description`; narrower skills make routing and manual `@skill` invocation clearer.
- Agent Skills use progressive disclosure: only the matching skill instructions are loaded into context. A single large skill would load unrelated create, score, optimization, and maintainer instructions together.
- Shared code avoids duplicated assets. The overlap is implementation-level, not user-intent-level.
- Separate skills make it easier to add or update one capability when Genie Workbench changes.
- A bundle-level manifest can still make the repository feel like a plugin even though the runtime unit is a collection of skills.

Do not create separate copies of Genie API wrappers, `serialized_space` schemas, scoring helpers, or optimizer helpers inside each skill. Use thin skill scripts that call the shared package.

## 3. Product goals

1. Provide task-specific Genie Code skills for the core Genie Workbench lifecycle:
   - Create a new Genie Space from business requirements and Unity Catalog sources.
   - Score an existing Genie Space for readiness and optimization suitability.
   - Run a benchmark-driven optimization workflow to improve benchmark accuracy.
   - Track outputs and change history without a Databricks App.
2. Package all skills and helper code as a downloadable bundle that can be installed into a Databricks workspace skills folder or a user skills folder.
3. Make the skill instructions explicit enough that a coding agent knows what to inspect, what code to run, what artifacts to create, when to ask for approval, and how to apply changes safely.
4. Keep parity with Genie Workbench features over time through a documented upstream-feature map and update workflow.
5. Avoid requiring users to deploy Genie Workbench, Lakebase, Node.js, React, FastAPI, or a Databricks App.

## 4. Non-goals

1. Do not build a web UI, FastAPI backend, React frontend, or Databricks App.
2. Do not replace Genie Workbench for dashboard-style administration, central scan inventory, org-wide leaderboard views, persistent multi-user UI state, or version rollback UI.
3. Do not implement the deprecated standalone readiness-remediation workflow as a skill.
4. Do not auto-apply destructive or irreversible changes without an explicit user approval step.
5. Do not require workspace-admin permissions for basic user-scope installation.
6. Do not assume every workspace has MLflow Prompt Registry, a GSO Lakeflow job, or Workbench state tables already configured; the plugin must preflight and degrade or fail clearly.

## 5. External compatibility requirements

### 5.1 Agent Skills format

Each user-facing skill must be a folder containing a required `SKILL.md` file. `SKILL.md` must contain YAML frontmatter with at least `name` and `description`, followed by Markdown instructions. Skill names must be lowercase, hyphenated, and match the parent folder name.

Skill folders may include:

```text
scripts/      # thin executable wrappers for the shared Python package
references/   # task-specific Markdown docs, schemas, checklists, examples
assets/       # templates and static input schemas
```

### 5.2 Databricks Genie Code installation paths

The bundle must support two install scopes:

```text
/Users/{username}/.assistant/skills/      # user skills
Workspace/.assistant/skills/              # workspace skills
```

Workspace installation is intended for shared team use and may require workspace-admin rights or write access to the workspace skills folder. User installation is the default.

### 5.3 Databricks Genie Space APIs

The bundle must use Databricks Genie management and conversation APIs through `databricks-sdk` or direct REST calls through `WorkspaceClient.api_client.do()`.

Minimum API operations:

- List spaces.
- Get a space and read `serialized_space`.
- Create a space with `POST /api/2.0/genie/spaces`.
- Update a space with `PATCH /api/2.0/genie/spaces/{space_id}` when approved optimization results need to be applied.
- Start conversations and retrieve generated SQL for benchmark runs.
- Use native Genie evaluation endpoints when available and useful.

### 5.4 `serialized_space` constraints

All generated or updated space configs must pass Databricks validation rules before API submission:

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

## 6. User personas and workflows

### 6.1 Genie Space developer

The developer wants to create or improve a Genie Space using conversational assistance inside Genie Code.

Example requests:

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

The team wants reusable, version-controlled workflows that can be installed as workspace skills and used consistently across teams.

Example request:

```text
@genie-space-score Scan all spaces I can manage and write a readiness report to my workspace folder.
```

### 6.3 Maintainer of this companion repo

The maintainer wants to update skills when Genie Workbench adds or changes a feature.

Example request:

```text
@genie-workbench-parity Compare this repo against the current Genie Workbench main branch and propose skill updates.
```

## 7. Skill catalog

The project must ship the following skills in the first release.

### 7.1 `genie-space-create`

Purpose: Build a new Genie Space from requirements, inspect data sources, generate a plan, validate SQL, assemble `serialized_space`, and create the space after explicit approval.

When it should activate:

- User asks to create, build, scaffold, or configure a Genie Space.
- User asks to turn business requirements and Unity Catalog tables into a Genie Space.
- User asks for sample questions, example SQLs, benchmarks, joins, measures, filters, expressions, or text instructions for a new space.

Required bundled assets:

```text
skills/genie-space-create/
  SKILL.md
  references/create-workflow.md
  references/space-plan-schema.md
  references/serialized-space-rules.md
  references/gsl-instruction-template.md
  assets/space-plan-template.json
  assets/create-request-template.json
  scripts/create_space.py
  scripts/discover_sources.py
  scripts/profile_sources.py
  scripts/generate_config.py
  scripts/validate_config.py
  scripts/test_sqls.py
```

Expected workflow:

1. Gather business context, intended audience, domain terminology, default assumptions, required metrics, and target workspace folder.
2. Discover candidate Unity Catalog assets with the user’s permissions.
3. Inspect selected tables or metric views:
   - Table comments.
   - Column names, types, comments.
   - Candidate PII or sensitive columns.
   - ETL or metadata columns to exclude.
   - Distinct values for categorical columns.
   - Date ranges for date columns.
   - Null rates and simple quality issues.
4. Generate a structured plan with these sections:
   - Space title and description.
   - Included tables and metric views.
   - Column configs, descriptions, synonyms, exclusions, entity matching, and format assistance.
   - Five sample questions.
   - One concise text instruction body using canonical sections.
   - At least 8 and preferably 10–15 example question-SQL pairs with usage guidance.
   - At least 10 benchmark question-SQL pairs.
   - Join specs for multi-source spaces.
   - SQL snippets: measures, filters, and expressions.
5. Test all example SQLs and benchmark SQLs against the selected warehouse.
6. Repair or drop invalid SQL artifacts before create.
7. Build `serialized_space` and run validation.
8. Present a plan and diff-like summary for user approval.
9. Only after approval, call the Genie create-space API.
10. Write output artifacts.

Required outputs:

```text
outputs/<space-slug-or-id>/plan.json
outputs/<space-slug-or-id>/serialized_space.json
outputs/<space-slug-or-id>/validation.json
outputs/<space-slug-or-id>/create_result.json
outputs/<space-slug-or-id>/README.md
```

Safety rules:

- Do not create a space until the user has reviewed the plan.
- Do not include columns flagged as PII unless the user explicitly confirms they are safe and permitted.
- Do not invent categorical values; use profiled values or omit value-specific filters.
- Prefer SQL expressions, example SQLs, and snippets over long text instructions.
- Keep text instructions short and business-focused; do not put SQL code in text instructions.

### 7.2 `genie-space-score`

Purpose: Score a Genie Space for readiness using a deterministic scanner modeled on Genie Workbench quality scoring.

When it should activate:

- User asks to score, scan, grade, assess, audit, or check readiness of a Genie Space.
- User asks whether a space is ready to optimize.
- User asks for missing metadata, missing examples, missing benchmarks, or quality gaps.

Required bundled assets:

```text
skills/genie-space-score/
  SKILL.md
  references/iq-rubric.md
  references/score-output-schema.md
  references/readiness-next-steps.md
  scripts/score_space.py
  scripts/score_all_spaces.py
  scripts/render_score_report.py
```

Required score model:

The scanner must implement the current Genie Workbench readiness model as a source-of-truth port. The first implementation should support these deterministic checks, then keep the rubric synchronized through the parity workflow.

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

The report may show both `score` out of 12 and normalized `score_percent = score / 12 * 100` to align with percentage-style Workbench quality reporting.

Required scanner behavior:

1. Fetch `serialized_space` for the target space.
2. Enrich table and column descriptions from Unity Catalog when possible. Inline space descriptions take precedence and must not be overwritten.
3. Load terminal optimization run data from plugin output history, optional Delta state tables, and Workbench/GSO state tables if configured.
4. Run all checks deterministically without LLM calls.
5. Return findings, recommended next steps, warnings, and warning next steps.
6. Render a Markdown report and JSON result.

Required outputs:

```text
outputs/<space-id>/score.json
outputs/<space-id>/score_report.md
outputs/<space-id>/findings.json
```

### 7.3 `genie-space-optimize`

Purpose: Run a benchmark-driven optimization workflow to improve Genie Space benchmark accuracy.

When it should activate:

- User asks to optimize a Genie Space for accuracy.
- User asks to run benchmark evaluation, measure generated SQL quality, diagnose failures, or improve benchmark pass rate.
- User asks to run Auto-Optimize or GSO-like workflow without deploying the Workbench app.

Required bundled assets:

```text
skills/genie-space-optimize/
  SKILL.md
  references/optimization-workflow.md
  references/lever-catalog.md
  references/evaluation-gates.md
  references/gso-job-setup.md
  references/apply-review-checklist.md
  scripts/preflight_optimizer.py
  scripts/bootstrap_gso_job.py
  scripts/run_baseline.py
  scripts/run_optimization.py
  scripts/poll_run.py
  scripts/render_optimization_report.py
  scripts/apply_optimization_result.py
```

Optimization modes:

#### Mode A — Full GSO parity mode

This is the preferred mode. It reuses, vendors, submodules, or depends on the Genie Workbench `packages/genie-space-optimizer` engine and runs the same Lakeflow Job workflow without deploying the Workbench app.

Pipeline:

1. Preflight.
2. Baseline evaluation.
3. Enrichment.
4. Lever loop.
5. Finalize.
6. Staged deploy review.

Required characteristics:

- Uses the same optimizer state schema and Delta table model where practical.
- Supports the same lever categories:
  - Tables and columns.
  - Metric views.
  - Table-valued functions.
  - Join specs.
  - Instructions and example SQL.
- Supports 3-gate evaluation:
  - Slice gate.
  - P0 gate.
  - Full benchmark gate.
- Tracks accepted and rejected changes.
- Stores baseline and final accuracy.
- Allows staged review before applying changes to the live space.

#### Mode B — Lightweight local optimization mode

This mode is used when the full GSO job is not installed or cannot run. It should be sufficient for small spaces and quick experiments but must not be represented as full Workbench parity.

Pipeline:

1. Validate benchmarks.
2. Ask Genie benchmark questions and retrieve generated SQL.
3. Execute generated SQL and expected SQL.
4. Compare results using deterministic checks and optional LLM judge prompts.
5. Cluster failure causes.
6. Generate candidate changes for metadata, examples, joins, snippets, or benchmarks.
7. Test candidates on a small benchmark slice.
8. Present measured results and a staged change plan.
9. Apply only after user approval.

Preflight requirements for both modes:

- The user can manage or edit the target Genie Space.
- A SQL warehouse is available and the user has CAN USE.
- The user or configured job identity can read referenced Unity Catalog tables.
- The space has at least 10 benchmark questions or the skill can generate benchmark candidates and ask the user to approve them.
- `serialized_space` passes validation before optimization begins.
- The output folder is writable.
- If full GSO mode is selected, required MLflow/Prompt Registry and UC state schema prerequisites are checked.

Required outputs:

```text
outputs/<space-id>/optimization/<run-id>/preflight.json
outputs/<space-id>/optimization/<run-id>/baseline_results.json
outputs/<space-id>/optimization/<run-id>/failure_clusters.json
outputs/<space-id>/optimization/<run-id>/change_candidates.json
outputs/<space-id>/optimization/<run-id>/accepted_changes.json
outputs/<space-id>/optimization/<run-id>/final_results.json
outputs/<space-id>/optimization/<run-id>/optimization_report.md
```

Apply rules:

- Default `apply_mode` is `staged`; the bundle produces a change artifact but does not update the live space.
- `apply_mode=auto` is allowed only if the user explicitly requests it and the final result improves accuracy without failing regression gates.
- Applying optimization results must re-fetch the live space, merge changes, sanitize IDs, validate `serialized_space`, show a diff, require user approval, PATCH the space, and rescore.

### 7.4 `genie-workbench-parity`

Purpose: Help maintainers update this bundle when Genie Workbench adds or changes features.

When it should activate:

- User asks to update skills based on a new Workbench release.
- User asks to compare this repo against the Workbench repo.
- User asks to add a new skill that mirrors a Workbench capability.

Required bundled assets:

```text
skills/genie-workbench-parity/
  SKILL.md
  references/parity-process.md
  references/upstream-feature-map.yaml
  scripts/check_workbench_parity.py
  scripts/generate_skill_stub.py
  scripts/update_feature_map.py
```

Required behavior:

1. Read `references/upstream-feature-map.yaml`.
2. Compare mapped Workbench files, docs, APIs, and tests against the plugin implementation.
3. Identify added, removed, or changed capabilities.
4. Classify each change:
   - Update an existing skill instruction.
   - Update shared code assets.
   - Add a new skill.
   - Mark as app-only or excluded.
5. Generate a proposed changelog entry and implementation tasks.
6. Refuse to silently overwrite skill instructions; produce a diff for maintainer review.

## 8. Bundle package design

### 8.1 Repository layout

```text
databricks-genie-workbench-skills/
  SPEC.md
  README.md
  LICENSE.md
  NOTICE.md
  pyproject.toml
  uv.lock
  plugin.json
  skills/
    genie-space-create/
      SKILL.md
      references/
      assets/
      scripts/
    genie-space-score/
      SKILL.md
      references/
      assets/
      scripts/
    genie-space-optimize/
      SKILL.md
      references/
      assets/
      scripts/
    genie-workbench-parity/
      SKILL.md
      references/
      assets/
      scripts/
  src/
    genie_workbench_skills/
      __init__.py
      artifact_store.py
      auth.py
      benchmark_eval.py
      create_plan.py
      genie_api.py
      gso_bootstrap.py
      iq_score.py
      optimizer.py
      parity.py
      reporting.py
      safety.py
      serialized_space.py
      space_update.py
      sql_warehouse.py
      uc_metadata.py
  scripts/
    build_plugin.py
    install_plugin.py
    validate_plugin.py
    sync_from_workbench.py
  tests/
    fixtures/
      serialized_spaces/
      score_results/
      optimization_runs/
    unit/
    integration/
  dist/
    .gitkeep
```

### 8.2 Distribution artifact

`python scripts/build_plugin.py` must produce:

```text
dist/databricks-genie-workbench-skills-<version>.zip
```

Zip contents:

```text
plugin.json
README.md
skills/
  genie-space-create/
  genie-space-score/
  genie-space-optimize/
  genie-workbench-parity/
plugin/
  src/genie_workbench_skills/
  wheels/genie_workbench_skills-<version>-py3-none-any.whl
install.py
```

### 8.3 Plugin manifest

`plugin.json` is project-defined metadata, not an external Agent Skills standard. It lets the installer, parity checks, and validation scripts reason about the bundle.

Required fields:

```json
{
  "name": "databricks-genie-workbench-skills",
  "version": "0.2.0",
  "description": "Agent Skills bundle for creating, scoring, and optimizing Databricks Genie Spaces.",
  "workbench_baseline_ref": "<tag-or-commit>",
  "skills": [
    "genie-space-create",
    "genie-space-score",
    "genie-space-optimize",
    "genie-workbench-parity"
  ],
  "python_package": "genie_workbench_skills",
  "default_install_scope": "user",
  "supports_workspace_install": true,
  "shared_support_dir": ".assistant/plugins/databricks-genie-workbench-skills"
}
```

### 8.4 Install commands

Local install from a cloned repo:

```bash
python scripts/install_plugin.py --profile DEFAULT --scope user
python scripts/install_plugin.py --profile DEFAULT --scope workspace
```

Install from a downloaded zip:

```bash
python install.py --profile DEFAULT --scope user
python install.py --profile DEFAULT --scope workspace
```

Installer responsibilities:

1. Validate `plugin.json`.
2. Validate all `SKILL.md` files.
3. Resolve the target workspace path.
4. Import skill folders into the selected skills directory.
5. Import shared plugin code into a predictable plugin support directory.
6. Preserve existing user-modified skill files by default.
7. Support `--overwrite` for explicit upgrades.
8. Write `install_result.json` locally and optionally to the workspace output folder.

Target workspace structure after user install:

```text
/Users/{username}/.assistant/skills/
  genie-space-create/
  genie-space-score/
  genie-space-optimize/
  genie-workbench-parity/
/Users/{username}/.assistant/plugins/databricks-genie-workbench-skills/
  plugin.json
  src/genie_workbench_skills/
  wheels/
```

Target workspace structure after workspace install:

```text
Workspace/.assistant/skills/
  genie-space-create/
  genie-space-score/
  genie-space-optimize/
  genie-workbench-parity/
Workspace/.assistant/plugins/databricks-genie-workbench-skills/
  plugin.json
  src/genie_workbench_skills/
  wheels/
```

The installer must support path normalization because Databricks UI paths and CLI workspace paths may differ by environment. The implementation must verify by listing the target folder after import.

### 8.5 How skills call shared assets

Each skill script should be a thin wrapper that locates the shared support directory and imports the shared package.

Example wrapper pattern:

```python
# skills/genie-space-score/scripts/score_space.py
from genie_workbench_skills.cli.score_space import main

if __name__ == "__main__":
    raise SystemExit(main())
```

The shared package may be made importable by one of these mechanisms, in order of preference:

1. Install the wheel into the active Python environment used by Genie Code.
2. Add the plugin support directory to `PYTHONPATH` for script execution.
3. Use a wrapper that prepends the support directory to `sys.path`.

The first release should support options 2 and 3 because workspace users may not control the active Python environment.

## 9. Shared code asset requirements

### 9.1 `auth.py`

Responsibilities:

- Create `WorkspaceClient()` using Databricks default authentication.
- Allow explicit host/profile/token configuration only through standard Databricks mechanisms.
- Detect when code is running in a Databricks notebook, Databricks workspace file context, or local environment.
- Provide clear errors for missing credentials.

### 9.2 `genie_api.py`

Responsibilities:

- Wrap Genie REST API calls.
- Provide typed helper functions:
  - `list_spaces()`
  - `get_space(space_id)`
  - `get_serialized_space(space_id)`
  - `create_space(title, description, parent_path, warehouse_id, serialized_space)`
  - `update_space(space_id, serialized_space)`
  - `start_conversation(space_id, content)`
  - `get_generated_sql(space_id, conversation_id, message_id)`
  - `create_eval_run(space_id, config)` when available.
- Normalize API errors into actionable messages.

### 9.3 `serialized_space.py`

Responsibilities:

- Generate valid 32-character lowercase hex IDs.
- Clean configs:
  - Wrap string fields as arrays where required.
  - Remove nulls from arrays.
  - Sort arrays by required sort keys.
  - Deduplicate IDs.
  - Deduplicate column configs.
  - Normalize join spec relationship annotations.
  - Remove empty SQL snippets.
  - Enforce one text instruction.
  - Validate size limits.
- Produce validation errors and warnings separately.

### 9.4 `uc_metadata.py`

Responsibilities:

- List accessible catalogs, schemas, tables, and metric views.
- Search by table names, column names, comments, and synonyms.
- Fetch table and column comments.
- Produce metadata summaries for agent context.
- Redact or flag likely PII and sensitive columns.

### 9.5 `sql_warehouse.py`

Responsibilities:

- Discover eligible SQL warehouses.
- Execute SQL with concurrency limits.
- Substitute default parameter values safely for SQL validation.
- Return compact result previews.
- Detect syntax errors, missing permissions, missing tables, and empty result issues.

### 9.6 `create_plan.py`

Responsibilities:

- Store a normalized plan model.
- Convert plan sections into `serialized_space`.
- Generate plan reports.
- Validate all SQL artifacts before config assembly.

### 9.7 `iq_score.py`

Responsibilities:

- Implement the deterministic score model.
- Enrich descriptions from UC metadata.
- Load optimization history from plugin outputs and optional GSO tables.
- Return stable JSON output for tests.

### 9.8 `space_update.py`

Responsibilities:

- Validate candidate update field paths.
- Apply approved updates to local configs.
- Render before/after diffs.
- Re-fetch and apply approved updates to Databricks.
- Retry stale config updates when safe.
- Sanitize IDs and revalidate before PATCH.

This module is shared infrastructure for create and optimization workflows. It is not exposed as a standalone readiness-remediation skill.

### 9.9 `benchmark_eval.py`

Responsibilities:

- Read benchmark questions and expected SQL from `serialized_space`.
- Ask Genie benchmark questions.
- Retrieve generated SQL.
- Execute generated SQL and expected SQL.
- Compare result sets using deterministic comparison rules.
- Support optional LLM judging when deterministic comparison is insufficient and the user permits it.

### 9.10 `optimizer.py`

Responsibilities:

- Run lightweight optimization mode.
- Provide interfaces for GSO parity mode.
- Track benchmark-level results.
- Compare expected and generated SQL results.
- Cluster failures and generate candidate changes.
- Enforce gate evaluation before accepting changes.

### 9.11 `gso_bootstrap.py`

Responsibilities:

- Detect whether full GSO mode is installed.
- Deploy or update the GSO Lakeflow job if the user requests full parity mode.
- Create or validate the optimizer state schema.
- Submit optimization runs.
- Poll run status.
- Fetch GSO outputs.

### 9.12 `artifact_store.py` and `reporting.py`

Responsibilities:

- Write JSON, JSONL, Markdown, and compact logs to each output directory.
- Maintain the top-level run index.
- Render human-readable reports for score and optimization outputs.
- Redact sensitive values before writing reports.

### 9.13 `parity.py`

Responsibilities:

- Read and validate `upstream-feature-map.yaml`.
- Compare mapped Workbench source files and docs to plugin skills and shared code.
- Generate parity reports, changelog drafts, and implementation task lists.
- Generate skeleton skill folders when a new Workbench capability meets the criteria for a new skill.

## 10. Artifact and history model

Because this project does not use the Workbench app or Lakebase by default, it must persist useful artifacts in files. Optional Delta persistence may be added for teams.

Default artifact root:

```text
/Workspace/Users/{username}/.genie-workbench-skills/outputs/
```

Local development artifact root:

```text
./outputs/
```

Each run must write machine-readable JSON plus a human-readable Markdown report.

Required top-level index:

```text
outputs/index.jsonl
```

Each record:

```json
{
  "timestamp": "2026-05-04T00:00:00Z",
  "skill": "genie-space-score",
  "space_id": "...",
  "run_id": "...",
  "status": "success",
  "artifact_dir": "outputs/<space-id>/...",
  "summary": "Score 9/12, Ready to Optimize"
}
```

Optional team persistence:

- `catalog.schema.genie_skill_runs`
- `catalog.schema.genie_skill_scores`
- `catalog.schema.genie_skill_optimization_runs`
- `catalog.schema.genie_skill_change_events`

Delta persistence must be opt-in and created only after the user confirms the target catalog and schema.

## 11. Permissions and identity model

### 11.1 Default user-mode identity

For create, score, and lightweight optimization workflows, code runs as the current Genie Code user through Databricks default authentication. This means:

- Unity Catalog discovery respects the user’s permissions.
- SQL validation runs with the user’s warehouse and data permissions.
- Genie Space create and update operations are attributed to the user’s identity.

### 11.2 Optional job identity for optimization

Full GSO parity mode may need a Lakeflow Job. The job can run as:

- The current user.
- A configured service principal.

The bundle must not create or use a service principal silently. If a service principal is configured, the bundle must preflight:

- The service principal can manage the target Genie Space if it will apply changes.
- The service principal can use the SQL warehouse.
- The service principal can read referenced schemas.
- The service principal can write optimizer state tables.

### 11.3 Approval boundaries

The bundle must require explicit approval before:

- Creating a Genie Space.
- Updating a live Genie Space.
- Deploying or updating a GSO job.
- Creating a UC schema or Delta tables.
- Running a long or potentially expensive optimization job.
- Applying optimized config to production spaces.

## 12. Skill authoring standards

Every `SKILL.md` must include:

1. Agent Skills frontmatter:

```yaml
---
name: genie-space-score
description: Score, scan, and assess Databricks Genie Spaces for readiness using the Genie Workbench quality rubric. Use when the user asks to score a Genie Space, check readiness, identify missing metadata, or determine whether a space is ready to optimize.
license: Databricks License
compatibility: Designed for Databricks Genie Code Agent mode. Requires Databricks workspace access and a SQL warehouse for SQL validation workflows.
metadata:
  plugin: databricks-genie-workbench-skills
  workbench_feature: iq-scanner
  workbench_baseline_ref: "<tag-or-commit>"
---
```

2. A concise workflow overview.
3. Exact scripts to run for mechanical tasks.
4. Required inputs.
5. Required outputs.
6. Human approval points.
7. Failure handling.
8. References to bundled files using relative paths from the skill root.
9. Examples of user requests.

Do not overload one skill with all context. Keep each skill focused. Put long schema references, prompts, and examples in `references/` or `assets/`. Put shared implementation in `src/genie_workbench_skills/`.

## 13. Workbench parity and update process

### 13.1 Upstream feature map

The repo must include:

```text
skills/genie-workbench-parity/references/upstream-feature-map.yaml
```

Initial map:

```yaml
workbench_repo: databricks-solutions/databricks-genie-workbench
workbench_baseline_ref: "<tag-or-commit>"
features:
  create_agent:
    workbench_docs:
      - docs/04-create-agent.md
    workbench_sources:
      - backend/services/create_agent.py
      - backend/services/create_agent_tools.py
      - backend/services/plan_builder.py
      - backend/genie_creator.py
      - backend/prompts_create/
    plugin_skills:
      - genie-space-create
    plugin_sources:
      - src/genie_workbench_skills/create_plan.py
      - src/genie_workbench_skills/serialized_space.py
      - src/genie_workbench_skills/uc_metadata.py
      - src/genie_workbench_skills/sql_warehouse.py
  iq_scanner:
    workbench_docs:
      - docs/05-iq-scanner.md
    workbench_sources:
      - backend/services/scanner.py
    plugin_skills:
      - genie-space-score
    plugin_sources:
      - src/genie_workbench_skills/iq_score.py
      - src/genie_workbench_skills/reporting.py
  auto_optimize:
    workbench_docs:
      - docs/07-auto-optimize.md
    workbench_sources:
      - backend/routers/auto_optimize.py
      - backend/services/gso_lakebase.py
      - packages/genie-space-optimizer/
      - databricks.yml
    plugin_skills:
      - genie-space-optimize
    plugin_sources:
      - src/genie_workbench_skills/benchmark_eval.py
      - src/genie_workbench_skills/optimizer.py
      - src/genie_workbench_skills/gso_bootstrap.py
      - src/genie_workbench_skills/space_update.py
excluded_upstream_features:
  deprecated_readiness_remediation:
    reason: "Expected to be deprecated upstream; not exposed as a standalone skill. Shared update helpers remain available for approved optimization changes."
```

### 13.2 Update workflow

When Workbench adds or changes a feature:

1. Run `scripts/sync_from_workbench.py --workbench-repo <path-or-url> --ref <tag-or-commit>`.
2. Run `@genie-workbench-parity` or `scripts/check_workbench_parity.py`.
3. Review generated parity report.
4. Decide one of:
   - Update existing skill instructions.
   - Update shared code.
   - Add a new skill.
   - Mark feature as app-only.
   - Mark feature as excluded.
5. Add or update tests.
6. Update `plugin.json` version and `upstream-feature-map.yaml`.
7. Run validation and package build.

### 13.3 Feature addition criteria

Add a new skill when the feature:

- Has a distinct user intent that Genie Code can recognize.
- Needs a different workflow or approval boundary.
- Would make an existing skill too broad.
- Uses a different set of scripts or references.

Update an existing skill when the feature is a small enhancement to an existing workflow.

Update shared code when the feature affects multiple skills or is a reusable mechanism rather than a user-facing workflow.

Mark a Workbench feature as app-only when it depends on UI state, dashboards, continuous polling views, app-specific persistence, or Lakebase-backed collaboration views that are not useful in a Genie Code workflow.

## 14. Testing requirements

### 14.1 Static validation

- Validate all `SKILL.md` files against the Agent Skills spec.
- Validate plugin manifest schema.
- Validate no skill description exceeds frontmatter limits.
- Validate all referenced files exist.
- Validate all scripts have CLI help and actionable error messages.
- Validate no deprecated standalone remediation skill folder exists.

### 14.2 Unit tests

Required coverage:

- ID generation.
- Config cleaning and sorting.
- Serialized space validation.
- IQ scoring on fixture configs.
- UC enrichment merge behavior.
- Candidate update field path parsing.
- Update apply/diff behavior.
- SQL parameter substitution.
- Benchmark result comparison.
- Artifact store writes.

### 14.3 Golden tests against Workbench fixtures

For each fixture space:

1. Run Workbench scanner or use recorded Workbench scanner output.
2. Run plugin scorer.
3. Assert score, maturity, checks, findings, and warnings match or document intentional divergence.

### 14.4 Integration tests

Integration tests run against a real Databricks workspace and must be opt-in.

Required tests:

- Install bundle to user skills path.
- Create a test Genie Space from a small known schema.
- Score the created space.
- Run lightweight benchmark evaluation.
- Stage an optimization change without applying it.
- Apply a harmless approved optimization change to a disposable test space.
- Optionally bootstrap and trigger full GSO mode.

### 14.5 Safety tests

- Create refuses to run without approval.
- Live updates refuse to run without approval.
- PII columns are flagged in create workflow.
- Invalid serialized configs are not submitted to the API.
- Optimizer does not apply accuracy-regressing changes.
- Service principal configuration cannot be silently inferred or created.

## 15. Operational requirements

### 15.1 Logging

All scripts must log to stderr for console visibility and write structured JSON logs to each artifact directory.

### 15.2 Error handling

Errors must include:

- What failed.
- Which Databricks object was involved.
- Whether retry is safe.
- Which permission or configuration is likely missing.
- The next concrete command or action.

### 15.3 Dependency management

- Use Python 3.11+.
- Use `uv` for local development and lockfile management.
- Pin exact runtime dependencies.
- Keep generated wheels small enough for workspace import.
- Do not require Node.js.

Minimum Python dependencies:

- `databricks-sdk`
- `pydantic`
- `pandas`
- `sqlglot` for SQL normalization/comparison where useful
- `mlflow` optional for optimization tracing

### 15.4 Security

- Do not store tokens in plugin artifacts.
- Do not print full query results by default.
- Redact likely secrets and sensitive values from reports.
- Keep data profiling samples small and purpose-specific.
- Require explicit approval for live changes.
- Prefer user identity for interactive operations.
- Treat service principal setup as an explicit advanced configuration.
- Treat bundled executable scripts as privileged assets; validate source provenance before installation.

## 16. Milestones

### Milestone 1 — Skill shell and installer

Deliverables:

- Repo layout.
- `plugin.json`.
- Four skill folders with valid `SKILL.md` files.
- Installer for user and workspace scopes.
- Skill validation tests.

Acceptance criteria:

- Bundle installs to a user skills folder.
- Genie Code can discover the skill descriptions in Agent mode after install.
- `scripts/validate_plugin.py` passes.

### Milestone 2 — Shared core package

Deliverables:

- `auth.py`, `genie_api.py`, `serialized_space.py`, `artifact_store.py`, `reporting.py`, and `space_update.py`.
- Thin wrapper scripts for each skill.
- Shared import path strategy for workspace execution.

Acceptance criteria:

- Skill scripts can import and run shared code from the installed support directory.
- Serialized space validation works on fixture configs.
- Artifact writes are deterministic and indexed.

### Milestone 3 — Score parity

Deliverables:

- `src/genie_workbench_skills/iq_score.py`.
- `genie-space-score` scripts and reports.
- Fixture tests against Workbench scanner outputs.

Acceptance criteria:

- Score output matches Workbench scanner for fixtures or documents intentional divergences.
- A real workspace integration test can score an existing space.

### Milestone 4 — Create workflow

Deliverables:

- `create_plan.py`, `uc_metadata.py`, `sql_warehouse.py`, and create skill templates.
- SQL validation and config validation.

Acceptance criteria:

- A user can create a valid Genie Space from selected UC tables without deploying an app.
- The generated config passes validation before create.
- Output artifacts are written.

### Milestone 5 — Lightweight optimization

Deliverables:

- `benchmark_eval.py`.
- `optimizer.py` lightweight mode.
- Baseline benchmark run.
- Failure clustering.
- Candidate change generation.
- Gate evaluation.
- Optimization report.

Acceptance criteria:

- A user can measure baseline accuracy and receive an optimization change plan.
- Regression gates prevent harmful changes.
- Live application of changes requires approval.

### Milestone 6 — Full GSO parity mode

Deliverables:

- `gso_bootstrap.py`.
- Vendored, submoduled, or dependency-based GSO engine integration.
- Job bootstrap and trigger scripts.
- GSO result ingestion.

Acceptance criteria:

- A user can bootstrap and trigger the Workbench-style optimization job without deploying the Workbench app.
- The optimization report shows baseline, final accuracy, accepted changes, and rejected changes.

### Milestone 7 — Workbench update workflow

Deliverables:

- `genie-workbench-parity` working skill.
- Feature map.
- Parity diff script.
- Generated skill-stub workflow.

Acceptance criteria:

- Maintainers can compare against a new Workbench release and generate a clear update report.
- Deprecated or excluded upstream capabilities are not reintroduced accidentally.

## 17. Open decisions

1. Full GSO parity mode should either vendor the Workbench GSO package, use it as a git submodule, or declare it as an external dependency. Recommendation: use a git submodule or vendored snapshot with explicit Workbench baseline metadata so the bundle can be installed without cloning Workbench separately.
2. Workspace install path normalization needs validation in target Databricks environments because Databricks docs describe workspace skills as `Workspace/.assistant/skills/`, while CLI workspace APIs may represent paths differently.
3. Decide whether optional Delta persistence should be in MVP or deferred until after score, create, and lightweight optimization are stable.
4. Decide how much of Workbench’s MLflow tracing should be ported. Recommendation: optional in MVP, required for full GSO parity.
5. Decide whether native Genie evaluation APIs should remain inside `genie-space-optimize` or become a separate skill if the API supports a distinct user workflow.
6. Decide whether to add a `genie-space-workbench` coordinator skill after MVP. Recommendation: do not add it initially; add it only if user testing shows that skill selection is confusing.

## 18. Reference documents to read before implementation

- Databricks Genie Code Agent Skills: https://docs.databricks.com/aws/en/genie-code/skills
- Agent Skills specification: https://agentskills.io/specification
- Databricks Genie API and `serialized_space` schema: https://docs.databricks.com/aws/en/genie/conversation-api
- Databricks Genie best practices: https://docs.databricks.com/aws/en/genie/best-practices
- Databricks CLI Genie command group: https://docs.databricks.com/aws/en/dev-tools/cli/reference/genie-commands
- Genie Workbench repo: https://github.com/databricks-solutions/databricks-genie-workbench
- Genie Workbench create agent docs: `docs/04-create-agent.md`
- Genie Workbench IQ scanner docs: `docs/05-iq-scanner.md`
- Genie Workbench Auto-Optimize docs: `docs/07-auto-optimize.md`
- Genie Workbench authentication and permissions docs: `docs/03-authentication-and-permissions.md`
