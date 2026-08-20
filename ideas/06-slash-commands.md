# 6. Custom Slash Commands

**Type:** Non-MCP Genie Code extension — resolves to a **Genie Code workspace skill library**

Can Genie Code be extended with custom slash commands (e.g. `/audit-agent`, `/review-sql`,
`/suggest-questions`)? If so, a library of Genie-Agent-specific slash commands would be a
lightweight, non-MCP way to streamline common workflows.

**Answer, after checking current platform coverage:** Genie Code's slash commands are a
built-in product surface — `Enter / to select and run a slash command` — with **no
documented mechanism for user-defined commands**: nothing in the settings pane, no
workspace-file convention, no registration API. But the underlying goal — one-line
invocation of a canned Genie-Agent workflow — is fully achievable with the extension
points that *do* exist: **workspace skills** (invoked by `@` mention or loaded
automatically when relevant) and **scheduled tasks** for the recurring ones. The idea
stays; it re-targets from "slash command library" to "skill library".

## Research findings: Genie Code's extension surfaces

| Surface | What it is | User-extensible? | Source |
|---|---|---|---|
| Slash commands (`/`) | Built-in product commands in the prompt box | **No.** No custom-command mechanism is documented anywhere; the settings pane has no entry for it | [Use Genie Code](https://docs.databricks.com/aws/en/genie-code/use-genie-code) |
| Skills (`@` mention) | Agent Skills folders (`SKILL.md` + optional scripts and reference docs). Auto-loaded when relevant to the request, or manually invoked by `@`-mentioning the skill | **Yes.** Workspace-wide (`Workspace/.assistant/skills/`) or personal (`/Users/{username}/.assistant/skills/`); installation is copying a folder | [Agent skills](https://docs.databricks.com/aws/en/genie-code/skills) |
| MCP servers | Tools via UC functions, AI Search, Genie Agent, external MCP (UC connections), custom MCP (Databricks Apps served at `/mcp`, stateless) | **Yes** | [MCP servers](https://docs.databricks.com/aws/en/genie-code/mcp) |
| Instructions | Global user / workspace instructions (`.assistant_instructions.md`), plus auto-discovered `AGENTS.md` / `CLAUDE.md` | Yes, but global and always-on — wrong shape for on-demand workflows | [Custom instructions](https://docs.databricks.com/aws/en/genie-code/instructions) |
| Scheduled tasks (Beta) | A prompt run as a full Genie Code session on a schedule; each run is a new chat; auto-approve is always on | Yes (prompt-based, no arguments) | [Scheduled tasks](https://docs.databricks.com/aws/en/genie-code/scheduled-tasks) |

The Genie Code settings pane enumerates the same list — Actions, MCP servers, user /
workspace instructions, skills / workspace skills, serverless usage policy — confirming
there is no custom-command slot today.

## Verdict

- **Drop the literal "custom slash commands" framing.** `/` is a closed, built-in surface.
  Designing around a future custom-command API would be speculative; nothing here depends
  on one. (If the product ever opens `/` up — the way other coding agents expose prompt
  templates — the skill library ports over trivially, since a command is just a named
  prompt with arguments.)
- **Skills are the right shape for the invoke-a-workflow use case.** A skill gives us
  everything a slash command would have: a name, a description, a canned workflow, and
  executable scripts — plus two things a slash command wouldn't: automatic loading when a
  request is relevant (users don't need to know the command exists), and `@`-mention
  invocation for the ones that do. This mirrors the resolution of
  [idea 4](./04-agent-migration.md): workspace-resident files, not server plumbing.
- **`@` mention replaces `/command <args>`.** Skills take no formal arguments; the user
  writes `@genie-agent-audit review space 12345` in natural language and the skill's
  instructions parse the target from context. Losing `argument-hint`-style affordances is
  acceptable — skills gain auto-discovery instead.
- **Scheduled tasks replace cron-shaped usage.** `/agent-health <space-id>` run weekly is
  not really a command; it's a prompt on a schedule, which Genie Code now supports natively
  (Beta). The command-style interactive version remains a skill.

## Command → skill mapping

| Proposed command | Becomes | Rationale |
|---|---|---|
| `/audit-agent <space-id>` | Skill `genie-agent-audit` — comprehensive review: instructions, SQL functions, example questions, data source coverage | Core workflow; script does deterministic payload analysis, `SKILL.md` drives the qualitative review |
| `/review-instructions <space-id>` | A focus mode of `genie-agent-audit` (e.g. "audit only the instructions") | Same read path and checklist subset — a separate skill would duplicate the fetch/parse script for one flag |
| `/suggest-questions <space-id>` | Skill `genie-question-suggest` | Distinct workflow and output (generated example questions, not a review report); ships alongside audit, sharing the fetch script verbatim |
| `/agent-health <space-id>` | Defer: scheduled task wrapping a prompt + data from the analytics MCP proposed in [idea 2](./02-workspace-usage-analytics.md) | Health metrics need usage/errors/feedback data Genie Code doesn't hold in-chat; that's MCP + system-table territory (see also [idea 5](./05-impact-analysis.md)). A skill can't be the source of truth for it |

Net v1 scope: **two skills** (`genie-agent-audit`, `genie-question-suggest`), one of which
has a narrow instructions-only mode.

## v1 design

### Packaging

Following the same model as [idea 4](./04-agent-migration.md) and
[`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/): developed in this repo as
self-contained directories with unit tests, deployed by copying the folder into
`Workspace/.assistant/skills/` (workspace skills are admin-created; access is granted via
the skills folder). Back the folder with a Git folder for versioning.

```
Workspace/.assistant/skills/
├── genie-agent-audit/
│   ├── SKILL.md            # when to run an audit, the review checklist, safety rules,
│   │                       #   and the instructions-only focus mode
│   ├── reference.md        # scoring rubric, serialized_space field map, failure playbook
│   └── scripts/
│       └── audit.py        # fetch + static analysis + compact report (never the payload)
└── genie-question-suggest/
    ├── SKILL.md            # when to suggest questions; diversity + realism rules
    ├── reference.md        # question taxonomy (aggregation, filter, join, time-series,
    │                       #   edge-case, ambiguous-phrasing probes)
    └── scripts/
        └── audit.py        # same fetch/model-summary script (kept verbatim in both
                            #   folders — see Maintenance below)
```

### Division of labor (the repo's standing philosophy)

- **Scripts own anything deterministic or payload-shaped.** `audit.py` fetches the Agent's
  `serialized_space` (via the Genie Agents API with `include_serialized_space=true`, or
  `databricks bundle generate genie-space` for bundled Agents), runs static checks —
  instruction count and size, SQL functions vs. registered tables, example-question
  coverage per table, unregistered references in SQL text — and prints a compact report.
  The payload never round-trips through model context, exactly as in
  [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/) and idea 4.
- **`SKILL.md` owns the qualitative workflow**: what to inspect, what good looks like, how
  to sequence findings into an actionable review, and the rule that Genie Code must run the
  script rather than eyeballing raw JSON.
- **Model work happens on the report, not the payload**: judging instruction clarity,
  generating candidate example questions from the script's data-model summary.

### Skill UX

- Automatic loading covers the discoverability case: a user asking "why is my Agent
  answering questions about revenue wrong?" should trigger the audit skill via its
  description.
- `@genie-agent-audit` covers the explicit case; the target space is parsed from the
  mention's surrounding text ("@genie-agent-audit review space 12345").
- Output is a structured in-chat report; for bundled Agents, durable artifacts (the report,
  suggested questions) are written as workspace files next to the bundle so they can be
  reviewed in a PR.

### Maintenance note

Skills install by folder copy, so the two skills can't share a `scripts/` directory —
`audit.py` is duplicated verbatim. Acceptable at two skills; if the family grows, generate
the folders from a single source in this repo (a small build step here, plain folders
there). Consumers still just copy folders.

## Relationship to other ideas

- **[Idea 1](./01-multi-turn-eval.md):** suggested questions should flow into the
  multi-turn eval harness as candidate eval cases — the suggest skill is the supply side.
- **[Idea 2](./02-workspace-usage-analytics.md):** owns the usage/errors/feedback data that
  a future `agent-health` needs; the scheduled-task prompt would query that MCP.
- **[Idea 3](./03-agent-diff.md):** the audit skill's review of a bundled Agent pairs
  naturally with a diff against the last stored version from
  `mcp-genie-agent-versioning` — "what changed since the last clean audit" is the first
  question any reviewer asks.
- **[Idea 4](./04-agent-migration.md):** shares the execution-surface open question below,
  and the same payload-out-of-context discipline.

## Open questions

- **Skill-script execution surface (shared with idea 4).** Can a skill script in Genie
  Code make authenticated API calls (Genie Agents API or the Databricks CLI) from the
  workspace? If auth passthrough isn't available, the skill degrades gracefully: Genie
  Code makes the API call itself and hands the script a local file — still keeping the
  *analysis* out of the model's hands, at the cost of one payload write. Verify on a real
  workspace before building.
- **Fetch path for unbundled Agents.** `bundle generate` only works for bundle-managed
  Agents; the API path (`GET /api/2.0/genie/spaces/{id}?include_serialized_space=true`)
  works for any Agent the user can read. Decide whether v1 requires the API path only.
- **Suggestion quality bar.** How do we evaluate generated example questions before
  recommending them into a production Agent? Minimum bar for v1: script validates that
  every generated question references only registered tables/columns; real evaluation is
  idea 1's job.
- **Product watch item (not a dependency):** if Genie Code ever ships user-defined slash
  commands or prompt templates, port the two skills' `SKILL.md` frontmatter into command
  definitions with argument hints. Cheap to do; nothing in v1 waits on it.
