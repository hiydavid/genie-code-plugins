# 4. Agent Migration & Portability

**Plugin:** `genie-agent-migrate` (Genie Code skill + deterministic CLI utility — not an MCP)

DABs already supports Genie Agent resources, so Agent definitions can be declared as code and
deployed across environments. The original open question was: what migration scenarios are
still painful enough that Genie Code + a plugin would meaningfully help?

**Answer, after checking current platform coverage:** the export/deploy/drift loop is now
well covered natively. The remaining gap is narrower and sharper — **environment
parameterization of the `serialized_space` payload** — and it is a file-transformation
problem, not an API problem. So this idea stops being a standalone MCP and becomes a skill
plus a deterministic utility.

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

### Verdict on the three original directions

- **Live-to-DABs export: drop.** `bundle generate genie-space` (plus `--watch`) does it
  natively, including the keep-the-file-in-sync-with-UI-edits case.
- **Cross-workspace import: narrow it.** The create-or-update call is not the hard part
  (DABs deploys to any target; the API supports promotion). The hard part is that the
  payload itself is environment-specific.
- **DABs drift detection: mostly drop.** `--watch` and `bundle plan` cover the per-Agent
  cases. What remains is a workspace-level *adoption audit* ("which of our 50 Agents are
  managed by any bundle at all?") — that is a v2 candidate tied to the shared Agent index
  in [idea 5](./05-impact-analysis.md), not this plugin.

## The real gap: `serialized_space` is not environment-portable

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
| `text_instructions[].content`, table/metric-view `description` | prose |

Two traps make a naive find-and-replace fail:

1. **Sort invariants.** The API rejects unsorted input: `tables` and `metric_views` must
   be sorted by `identifier`, `sql_functions` by the `(id, identifier)` tuple. Remapping a
   catalog prefix changes lexicographic order (multi-catalog mappings can reorder), so a
   remap that doesn't re-sort produces a payload the API refuses.
2. **Strict validation rules.** 32-char lowercase-hex IDs, uniqueness across collections,
   `version: 2`, two-element join-spec `sql` with relationship annotation, 25k/10k size
   limits. Hand-edited or remapped payloads surface these as opaque API parsing errors.

Plus the context-size concern this repo already cares about: an Agent with hundreds of
data sources has a payload that should not be manually edited through model context.

## Decision: a skill + deterministic utility, not an MCP

Mirrors the reasoning in [idea 3](./03-agent-diff.md):

- **The transformation is offline and deterministic.** No Genie API call, no auth, no OBO,
  no UC. It runs in any Git checkout (local or workspace repo) and is unit-testable.
- **A standalone MCP would re-create plumbing for nothing.** Its only value-add over the
  CLI is a file rewrite it could reach less conveniently than Genie Code itself can.
- **Same "keep payloads out of model context" philosophy.** Genie Code orchestrates and
  runs the utility; the `serialized_space` never round-trips through the model. The
  utility prints a compact report instead of the payload.
- **Cross-workspace promotion is file-mediated anyway.** Export → Git → deploy needs no
  cross-workspace identity; OBO tokens are workspace-scoped, so an App is the wrong shape
  for that hop regardless.

## v1 design

### Mapping spec (per bundle, one file)

```yaml
# genie-migrate.yml
targets:
  staging:
    catalog_map:  { dev_analytics: stg_analytics }
    schema_map:   { scratch: staging }
    table_map:    { dev_analytics.crm.orders: stg_analytics.crm.orders }
  prod:
    catalog_map:  { dev_analytics: prod_analytics }
```

Precedence: exact `table_map` (three-part) > `schema_map` (catalog.schema) >
`catalog_map` (catalog). `warehouse_id`, `title`, and permissions stay in bundle YAML with
per-target `${var.*}` substitutions — only the JSON payload is rendered.

### SQL text remap rules (conservative by design)

1. Rewrite tokens that exactly match a **registered data-source identifier** under the old
   mapping (backticked or unquoted three-part form). Highest confidence.
2. Rewrite three-part tokens matching a mapping key even when unregistered (e.g.
   benchmark SQL referencing an unregistered table) — reported as `unregistered_rewrites`.
3. Never rewrite two-part or bare table names unless unambiguous against the registered
   set; report ambiguity instead of guessing.
4. Prose mentions (instructions, descriptions) are flagged with locations; rewriting them
   is opt-in (`--remap-prose`).

### Invariant repair after remap

- Re-sort `tables` / `metric_views` by `identifier` and `sql_functions` by
  `(id, identifier)` — mandatory, see trap #1 above.
- IDs are untouched (identifier remaps don't affect ID constraints), `version` stays `2`.
- Full local validation of documented rules so failures surface as readable local errors,
  not API parsing rejections.

### Multi-target render pattern

The committed `src/genie/sales.geniespace.json` is the **source-environment** canonical
file. `genie-agent-migrate render --target prod` writes
`src/genie/targets/prod/sales.geniespace.json`, and per-target YAML overrides pick the
right `file_path`:

```yaml
# databricks.yml
targets:
  prod:
    resources:
      genie_spaces:
        sales:
          warehouse_id: ${var.prod_warehouse_id}
          file_path: ../src/genie/targets/prod/sales.geniespace.json
```

Rendered files are deterministic, so teams can either commit them (lockfile style,
reviewable diffs) or gitignore them (always fresh). Committing is recommended: the git
diff of a promotion then shows *exactly* which identifiers changed and nothing else.

### End-to-end promotion flow

```
1. EXPORT (native)   databricks bundle generate genie-space --existing-id <dev-id> --key sales
2. RENDER            genie-agent-migrate render --target staging
3. REVIEW            git diff of the rendered file (identifiers only; ids/structure unchanged)
4. VALIDATE (native) databricks bundle validate --strict --target staging
5. DEPLOY (native)   databricks bundle deploy --target staging
6. BIND (first time) databricks bundle deployment bind sales <staging-space-id>
```

Genie Code drives steps 1–6; the utility owns step 2.

### Utility commands

| Command | Purpose |
|---|---|
| `genie-agent-migrate render --target <t>` | Emit the remapped, re-sorted, validated `*.geniespace.json` + a compact change report (never the payload) |
| `genie-agent-migrate validate <file>` | Full local check of documented `serialized_space` rules |
| `genie-agent-migrate report <file>` | Compact summary: tables / metric views / functions, prose flags, mapping coverage |

Ship as a self-contained plugin directory (script + `pyproject.toml` + tests, mirroring
the repo layout) plus a `SKILL.md` that tells Genie Code when to run the flow and the
safety rules: always validate before deploy, never hand-edit identifiers in the JSON, and
review prose flags before promoting.

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

- Does `bundle plan` diff `serialized_space` for bound `genie_spaces` under the direct
  engine? If yes, the v2 audit only needs the unmanaged-Agents half. Verify against a
  real bound Agent before building anything.
- Commit rendered files (reviewable, lockfile-like) vs gitignore (always fresh)? Start
  with committing; revisit if teams churn targets.
- How often do prose references (instructions mentioning catalog names) actually matter?
  Default flag-only; measure on real Agents before investing in `--remap-prose`.
- Terraform-engine shops must run `bundle deployment migrate` first, since `genie_spaces`
  requires the direct engine — worth a callout in the skill, nothing more.
