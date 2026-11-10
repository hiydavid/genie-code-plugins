# 4. Agent Build, Migration & Portability

**Plugin:** `genie-agent-build` (Genie Code workspace skill — not an MCP)

DABs already supports Genie Agent resources, so Agent definitions can be declared as code and
deployed across environments. The original open question was: what migration scenarios are
still painful enough that Genie Code + a plugin would meaningfully help?

**Answer, after checking current platform coverage and working reference implementations:**
the export/deploy/drift loop is now well covered natively. The remaining gap is narrower
and sharper — **building a valid, environment-specific `serialized_space` payload from a
reviewable source file** — and it is a compiler/linter problem, not an API problem. So
this idea is a workspace skill with an executable script rather than a standalone MCP.

## Genie Code's operating model (design constraints)

Genie Code is a **workspace-resident** agent, not a local CLI agent on a laptop. From the
[agent skills docs](https://docs.databricks.com/aws/en/genie-code/skills):

- Skills live as workspace files: `Workspace/.assistant/skills/` (workspace-wide) or
  `/Users/{username}/.assistant/skills/` (personal). Installation is copying a folder —
  there is no `pip install` step on the consumer side.
- Skills may ship **executable scripts** (`scripts/*.py`, `*.sh`) that Genie Code runs on
  demand, plus reference docs.
- Everything Genie Code touches is a workspace file: the bundle lives in a **workspace Git
  folder** (repo), and Genie Code drives Databricks CLI workflows through its built-in
  `databricks-core` / `databricks-dabs` skills.

Consequences for this design: the utility must be a dependency-light script inside the
skill folder (not a packaged CLI), all paths are repo-relative workspace files, and the
in-chat review artifact must be a printed change report — not a local `git diff`.

## What the platform already covers (research findings)

| Capability | Native coverage | Source |
|---|---|---|
| Define Agent as code | `resources.genie_spaces` in bundles: `title`, `description`, `warehouse_id` (required), `serialized_space` or `file_path`, `parent_path`, `permissions`, `lifecycle`. Requires the direct deployment engine, CLI ≥ 1.3.0. | [DABs resources](https://docs.databricks.com/aws/en/dev-tools/bundles/resources) |
| Live → DABs export | `databricks bundle generate genie-space --existing-id <id>` emits the resource YAML + a `*.geniespace.json` file. | [Bundle commands](https://docs.databricks.com/aws/en/dev-tools/cli/bundle-commands) |
| Continuous live → file sync | `bundle generate genie-space --resource <key> --watch --force` polls UI edits back into the file. | [Bundle commands](https://docs.databricks.com/aws/en/dev-tools/cli/bundle-commands) |
| Adopt an existing Agent | `databricks bundle deployment bind <key> <space-id>` links a bundle resource to the live Agent. | [Bundle commands](https://docs.databricks.com/aws/en/dev-tools/cli/bundle-commands) |
| Deploy preview / drift to deploy | `bundle plan` shows the actions a deploy would take. | [Bundle commands](https://docs.databricks.com/aws/en/dev-tools/cli/bundle-commands) |
| Cross-workspace promotion call | The Genie API explicitly supports Create/Update with `serialized_space` "to promote Genie Agents across workspaces or create backups" (`GET .../{space_id}?include_serialized_space=true` → Create/Update). | [Genie Agents API](https://docs.databricks.com/aws/en/genie-agents/conversation-api) |
| Per-environment YAML values | DABs substitutions (`${var.warehouse_id}`, `${bundle.target}`, …) parameterize bundle YAML per target. | [Bundles variables](https://docs.databricks.com/aws/en/dev-tools/bundles/variables) |

## Prior art: `databricks-blogposts/2026-08-genie-agent-cicd`

The Databricks Solutions
[`2026-08-genie-agent-cicd`](https://github.com/databricks-solutions/databricks-blogposts/tree/main/2026-08-genie-agent-cicd)
project independently validates the core pattern:

1. Keep a Git-managed `*.geniespace.json` source file.
2. Put explicit `${catalog}` / `${schema}` placeholders inside the JSON.
3. Run a prebuild script that writes an environment-specific file under `build/`.
4. Point the DABs `genie_space.file_path` at the generated file.

It is a useful reference implementation, not the reusable plugin proposed here. Its
prebuild uses blind string replacement, parses `databricks.yml` with regular expressions,
does not validate or repair the serialized payload, and verifies only a target marker —
not whether the generated file still matches its source. It also leaves the recurring
UI-export problem unsolved: a fresh `bundle generate genie-space` writes concrete
identifiers back out, so placeholders must be restored safely before the file can remain
the target-neutral source of truth.

That establishes the differentiation for this skill: **turn the reference pattern into a
safe, deterministic Agent configuration compiler with a supported import/re-sync path.**

### Verdict on the three original directions

- **Live-to-DABs export: drop.** `bundle generate genie-space` (plus `--watch`) does it
  natively, including the keep-the-file-in-sync-with-UI-edits case.
- **Cross-workspace import: narrow it.** The create-or-update call is not the hard part
  (DABs deploys to any target; the API supports promotion). The hard part is turning an
  exported, environment-bound payload into a safe target-neutral source and then building
  a valid payload for each target.
- **DABs drift detection: mostly drop.** `--watch` and `bundle plan` cover the per-Agent
  cases. What remains is a workspace-level *adoption audit* ("which of our 50 Agents are
  managed by any bundle at all?") — that is a v2 candidate tied to the shared Agent index
  in [idea 5](./05-impact-analysis.md), not this plugin.

## The real gap: `serialized_space` needs a build step

DABs substitutions apply to bundle YAML, not to file contents. Dashboards got
`dataset_catalog` / `dataset_schema` resource fields (CLI 0.281.0) precisely so
environment values don't have to live inside the `.lvdash.json`. `genie_space` has **no
equivalent**: every catalog/schema reference is baked into the `*.geniespace.json`.

References hide in both structured fields and SQL text bodies:

| Location in `serialized_space` | Form |
|---|---|
| `data_sources.tables[].identifier` | structured, three-part |
| `data_sources.metric_views[].identifier` | structured, three-part |
| `instructions.sql_functions[].identifier` | structured, three-part |
| `instructions.join_specs[].left/right.identifier` | structured, three-part |
| `instructions.example_question_sqls[].sql` | SQL text |
| `instructions.sql_snippets.{filters,expressions,measures}[].sql` | SQL text |
| `benchmarks.questions[].answer[].content` | SQL text |
| `data_sources.volumes[].path` | structured `/Volumes/<catalog>/<schema>/<volume>` path |
| `text_instructions[].content`, table/metric-view `description` | prose |

Three traps make a naive find-and-replace or marker-only prebuild fail:

1. **Sort invariants.** The API rejects unsorted input: `tables` and `metric_views` must
   be sorted by `identifier`, `sql_functions` by the `(id, identifier)` tuple. Remapping a
   catalog prefix changes lexicographic order (multi-catalog mappings can reorder), so a
   remap that doesn't re-sort produces a payload the API refuses.
2. **Strict validation rules.** The API requires `version: 2`, 32-char lowercase-hex IDs,
   uniqueness across ID namespaces, sorted ID-keyed arrays, sorted column configs,
   two-element join-spec `sql` with a relationship annotation, arrays for text fields,
   and documented count and size limits. Hand-edited or remapped payloads surface these as
   opaque API parsing errors.
3. **Stale artifacts look valid.** A file can have been rendered for the right target but
   no longer match the current source or mapping file. A target-name marker cannot prove
   freshness; the build must be reproducible and byte-compared with expected output.

Plus the context-size concern this repo already cares about: an Agent with hundreds of
data sources has a payload that should not be manually edited through model context.

## Decision: a configuration compiler in a workspace skill

- **The build is a pure function over workspace files.** No Genie API call, no auth, no
  OBO, no UC. An MCP server would mean a deployed App, scopes, and OBO plumbing — all
  overhead for a file transformation that Genie Code can execute directly from a skill
  script. Zero server deployment: drop the folder in `.assistant/skills/`.
- **Same "keep payloads out of model context" philosophy** as
  [`mcp-genie-agent-versioning`](../mcp/mcp-genie-agent-versioning/): Genie Code orchestrates
  and executes the script; `serialized_space` never round-trips through the model. The
  script prints a compact change report instead of the payload. The skill's core job is
  to stop Genie Code from attempting this edit by hand — the re-sort and invariant rules
  must not be improvised by an LLM per run.
- **Cross-workspace promotion is file-mediated anyway.** Export → Git → deploy needs no
  cross-workspace identity; OBO tokens are workspace-scoped, so an App is the wrong shape
  for that hop regardless.
- Mirrors the reasoning behind `diff_agent_versions` in
  [`mcp-genie-agent-versioning`](../mcp/mcp-genie-agent-versioning/README.md) (formerly idea 3,
  since shipped): don't build server plumbing for work that is already local to where the
  agent lives.

## v1 design

### Two supported source modes

The skill supports both common authoring paths without making them equally magical:

1. **Template mode (preferred for Git-first/greenfield Agents).** The committed source is
   target-neutral and contains explicit named placeholders such as
   `${analytics_catalog}` and `${sales_schema}`. Rendering is intentionally boring: replace
   declared placeholders, repair sort order, validate, and emit the target file.
2. **Imported mode (for existing/UI-authored Agents).** A native export contains concrete
   source-workspace identifiers. `templatize` converts only declared source values and
   confidently matched identifiers into explicit placeholders. Ambiguous matches fail for
   review rather than becoming permanent rendering heuristics.

After import, both modes converge on the same target-neutral template. Normal `render`
never guesses what an arbitrary SQL token means.

### Build spec (per bundle, one dependency-free JSON file)

Use JSON rather than assuming PyYAML exists in Genie Code's script execution environment.
`genie-agent-build.json` declares named values for the preferred template path and retains
exact mapping escape hatches for unusual brownfield migrations:

```json
{
  "source_target": "dev",
  "targets": {
    "dev": {
      "values": {
        "analytics_catalog": "dev_analytics",
        "sales_schema": "scratch"
      }
    },
    "staging": {
      "values": {
        "analytics_catalog": "stg_analytics",
        "sales_schema": "staging"
      },
      "table_map": {
        "dev_analytics.crm.orders": "stg_analytics.crm.orders"
      }
    },
    "prod": {
      "values": {
        "analytics_catalog": "prod_analytics",
        "sales_schema": "sales"
      }
    }
  }
}
```

For imported mode, precedence remains exact `table_map` (three-part) > `schema_map`
(`catalog.schema`) > `catalog_map` (catalog). `warehouse_id`, title, description,
permissions, and workspace paths stay in bundle YAML with per-target substitutions; only
the JSON payload is built here. The script never parses `databricks.yml` with regular
expressions.

### Safe templatization and text handling

`templatize` applies conservative rules once, at the source boundary:

1. Replace declared values in structured identifiers and volume paths.
2. Replace exact registered data-source identifiers in SQL, whether backticked or
   unquoted.
3. Replace three-part SQL tokens only when they match a declared mapping key; report them
   as `unregistered_rewrites` when they are not registered data sources.
4. Never infer two-part or bare table names when more than one source could match.
5. Replace explicit placeholders anywhere during render, including prose; flag remaining
   source-environment names in prose and SQL with their JSON locations.

This creates a reviewable template and keeps heuristic rewriting out of every subsequent
promotion.

### Invariant repair and validation

After templatization or rendering, the script:

- Re-sorts `tables` and `metric_views` by `identifier`, each `column_configs` array by
  `column_name`, and every ID-keyed array by `id`.
- Leaves IDs unchanged and requires `version: 2`.
- Validates 32-character lowercase-hex IDs, uniqueness across the documented namespaces,
  array-valued text fields, join-spec shape, and current limits — including at most 30
  tables, 10 volumes, and one text-instruction item; 25,000 characters per string; and
  3.5 MB total serialized size.
- Rejects unresolved placeholders, undeclared placeholders, stale source identifiers in a
  target build, and duplicate rendered identifiers.
- Keeps documented constraints in one versioned validator module so platform rule changes
  require one explicit update and test fixture.

Failures surface as local JSON paths and readable messages rather than API parsing errors.

### Multi-target build pattern

The committed source is `src/genie/templates/sales.geniespace.json` and the default output
is `build/genie/<target>/sales.geniespace.json`:

```yaml
# databricks.yml
sync:
  include:
    - build/genie/**

# resources/sales.genie_space.yml
resources:
  genie_spaces:
    sales:
      warehouse_id: ${var.warehouse_id}
      file_path: ../build/genie/${bundle.target}/sales.geniespace.json
```

Generated files are deterministic and **gitignored by default**. The canonical template,
build spec, compact build report, and CI result are the review artifacts; this avoids
stale target files and merge noise. Teams that require reviewed deploy artifacts may opt
into committed lockfile mode, where `check` enforces an exact byte-for-byte match.

`check --target <t>` recomputes expected output and compares the actual build file; a
target-name marker is never treated as proof of freshness.

### End-to-end promotion and re-sync flow

```
1. EXPORT (native)      databricks bundle generate genie-space --existing-id <dev-id> --key sales
2. TEMPLATIZE (import)  python scripts/genie_agent_build.py templatize \
                          --source-target dev --input <exported-file> \
                          --output src/genie/templates/sales.geniespace.json
3. RENDER               python scripts/genie_agent_build.py render --target staging
4. CHECK                python scripts/genie_agent_build.py check --target staging
5. REVIEW               read the compact identifier/token/change report; never print the payload
6. VALIDATE (native)    databricks bundle validate --strict --target staging
7. PLAN (native)        databricks bundle plan --target staging
8. DEPLOY (native)      databricks bundle deploy --target staging
9. BIND (first time)    databricks bundle deployment bind sales <staging-space-id> --target staging
```

Steps 1–2 are needed only for initial import or when pulling UI changes back into Git.
Native `--watch` must write to a concrete staging/export file, never directly over the
canonical template, because it would replace placeholders with live identifiers. The
skill can later wrap this as `pull`, but v1 should keep the native export visible.

Before first Agent deployment, referenced tables, metric views, functions, and volumes
must already exist in the target. A companion job that creates a metric view after Agent
deployment is not a safe first-deploy dependency order.

### Packaging & execution model

The utility ships **inside the skill folder** as a self-contained executable script:

```
Workspace/.assistant/skills/genie-agent-build/
├── SKILL.md
├── reference.md
└── scripts/
    └── genie_agent_build.py    # Python standard library only
```

Genie Code runs the script against the bundle repo (a workspace Git folder); all paths are
repo-relative workspace files. The `SKILL.md` encodes the safety rules: render and check
before deploy, never hand-edit generated target files, never overwrite the canonical
template with a live export, and review warnings before promoting.

| Command | Purpose |
|---|---|
| `genie_agent_build.py templatize ...` | Convert a declared source-target export into a target-neutral template; stop on ambiguity |
| `genie_agent_build.py render --target <t>` | Emit a substituted, re-sorted, validated target payload plus a compact report |
| `genie_agent_build.py check --target <t>` | Recompute expected output and byte-compare it with the current build artifact |
| `genie_agent_build.py validate <file>` | Validate documented `serialized_space` rules with JSON-path errors |
| `genie_agent_build.py report <file>` | Summarize sources, placeholders, warnings, and mapping coverage without printing payload content |

In this plugins repo, the skill has its own directory and unit tests. The installed script
uses only the Python standard library so copying the folder into `.assistant/skills/` is
the complete consumer installation; there is no `pip install` step or runtime dependency
assumption.

## v2 candidate: workspace adoption & drift audit

The one direction with real remaining value needs API access and server-side payload
handling, which is MCP territory: crawl all Agents in a workspace and report, per Agent,
`{managed: bool, bundle_key, drift: in_sync | live_ahead | unknown}` — i.e. which Agents
are unmanaged by any bundle, and which bundled Agents have live UI edits not yet in their
`.geniespace.json`. `--watch` only covers one Agent at a time in a polling loop.

Natural home: a tool in the existing `mcp-genie-agent-versioning` (it already has the OBO
plumbing and per-Agent read path) or the shared Agent index proposed in
[idea 5](./05-impact-analysis.md). Defer until v1 proves the promotion workflow.

## Open questions

- **Verify Genie Code's execution surface before building.** Genie Code ships built-in
  `databricks-core` / `databricks-dabs` skills, which implies bundle CLI commands
  (`generate`, `validate`, `deploy`, `bind`) are runnable from Genie Code — but confirm
  the mechanics on a real workspace: shell availability, working directory against a Git
  folder, auth passthrough, and whether skill scripts can read/write repo files from that
  same surface. If the CLI surface turns out to be restricted, the skill degrades
  gracefully (script still runs; CLI steps become instructions for the user).
- Does `bundle plan` diff `serialized_space` for bound `genie_spaces` under the direct
  engine? If yes, the v2 audit only needs the unmanaged-Agents half. Verify against a
  real bound Agent before building anything.
- Can native `bundle generate genie-space --watch` be directed to a dedicated concrete
  staging file cleanly, or should the skill add a `pull` wrapper after v1?
- Which teams require committed deploy artifacts? Default to gitignored builds; keep
  lockfile mode optional until a compliance-driven use case requires it.
- How often do untemplated prose references matter in real Agents? Explicit placeholders
  render everywhere, but undeclared environment names remain flag-only until evidence
  supports more inference.
- Terraform-engine shops must run `bundle deployment migrate` first, since `genie_spaces`
  requires the direct engine — worth a callout in the skill, nothing more.
