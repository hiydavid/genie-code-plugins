# 6. Agent Production Coach — Diagnosis-First Guided Playbooks

**Working name:** Genie Agent production coach
**Type:** Markdown playbooks first; Genie Code workspace skill as the recommended
packaging; thin diagnostic MCP only if measurement proves native inspection insufficient
**Status:** Designed (content-first; vehicle left open)

Genie Code already has the verbs for building a production-quality Genie Agent:
generate or improve instructions (text, example SQL, knowledge-store snippets, joins),
generate or improve benchmarks, and review a benchmark eval run to propose context
changes. Users still get stuck because those verbs are **proactive** — the user has to
know which one to invoke, and in which order, from wherever they actually are.

Typical starting points (non-exhaustive):

1. Tables exist; the user wants to "chat with the data" and does not know the path from
   tables to a trusted agent.
2. The user has been tuning with Genie Code and is not getting great results.
3. Benchmark accuracy looks good, but latency feels slow.
4. The user moved from Chat mode to Agent mode and existing benchmarks no longer work
   well.

This idea is a **diagnosis-first, guided-loop coach**: inspect current state, name one
playbook and the next single stage, execute that stage with a native Genie Code verb,
pause for review, repeat until production gates pass or the user stops.

It does not replace native Genie Code capabilities. It sequences them.

## What the platform already covers (research findings)

| Capability | Native coverage | Source |
|---|---|---|
| Create an agent from a domain prompt or selected tables | Genie Code launches on create, reads data, suggests descriptions and example queries; user can ask Genie Code to create the agent | [Create and manage a Genie Agent](https://docs.databricks.com/aws/en/genie-agents/set-up) |
| Tune context | Example SQL, UC functions, plain-text instructions, knowledge store (table descriptions, joins, SQL expressions). Caps: 100 instructions, 200 snippets, 30 tables/views | [Tune Genie Agent quality](https://docs.databricks.com/aws/en/genie-agents/tune-quality) |
| Debug a single bad answer | Open Genie Code from the response; it proposes context changes | [Test and monitor](https://docs.databricks.com/aws/en/genie-agents/monitor) |
| Analyze 7-day usage | Monitor → Analyze Space Usage launches Genie Code | [Test and monitor](https://docs.databricks.com/aws/en/genie-agents/monitor) |
| Generate / improve benchmarks | Genie Code can author and refine benchmark questions | Product surface; [Benchmarks](https://docs.databricks.com/aws/en/genie-agents/monitor) |
| Review a whole eval run | After a run, launch Genie Code from the evaluation; it suggests instruction/context improvements | [Analyze a benchmark run with Genie Code](https://docs.databricks.com/aws/en/genie-agents/monitor) |
| Chat vs Agent eval semantics | Chat: result-set comparison to gold SQL. Agent: LLM judge + optional evaluation notes. Mode is chosen **at run time**, not per question | [Test and monitor](https://docs.databricks.com/aws/en/genie-agents/monitor) |
| Agent mode behavior | Multi-step research, multiple SQL queries, structured report — slower by design | [Genie Agents concepts](https://docs.databricks.com/aws/en/genie-agents/concepts) |
| Custom Genie Code skills | Workspace or user `SKILL.md` packages, auto-loaded by description or `@` mention; may include scripts and reference files | [Genie Code skills](https://docs.databricks.com/aws/en/genie-code/skills) |
| Config versioning | Save / list / diff / restore via this repo's MCP | [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/) |

### Verdict

The verbs exist. Nothing native answers:

> "Given this agent (or these tables), what is the *next one thing* I should do, and
> which native Genie Code capability should do it?"

That is a sequencing and diagnosis gap, not a missing mutate-the-agent API. An MCP that
re-implements "generate instructions" would fight the product.

This also does not overlap ideas 1–5: multi-turn eval, workspace analytics, version
diff (shipped), environment remapping, and UC blast radius are different jobs.

## Design principle: content first, vehicle second

The scarce asset is a **diagnosis protocol + playbooks + production gates**. Those files
can be consumed three ways without rewriting the IP:

1. **Markdown playbook (v0).** A human follows it, or Genie Code is `@`-mentioned / pasted
   the file. Fastest test of whether the *content* works. Weak auto-discovery.
2. **Workspace skill (recommended packaging once content works).** Same files plus a
   `description` that matches real utterances. Progressive disclosure: `SKILL.md` routes;
   `references/*.md` are the playbooks; optional `scripts/` emit a structured maturity
   card without dumping `serialized_space` into the model. Matches
   [idea 4](./04-agent-migration.md)'s Genie Code operating model.
3. **Thin diagnostic MCP (v2, only if needed).** `diagnose_agent` / `recommend_next_step`
   that return counts, booleans, and a next-stage id — same pattern as versioning (keep
   large payloads server-side). Worth it if native inspection is noisy, we want
   workspace-wide "which agents aren't ready", or persisted journey state. Not worth it
   to re-implement generate-instructions.

Autonomy for v1 is a **guided loop**: execute one stage, pause for human review/accept,
continue until gates pass or the user stops. Not a fully autonomous tables→production
pipeline.

```
User ask
  → Diagnose current state
  → Maturity card (stage, gaps, one playbook, next stage)
  → User confirms that stage
  → Genie Code runs one native verb
  → User reviews / accepts diffs
  → Optional save_agent_config_version(before_update)
  → Re-diagnose or stop
```

## Diagnosis (the latch — always first)

Before generating anything, inspect the live agent (or the lack of one) and emit a short
**maturity card**. Use native Genie Code tools (read agent, SQL on UC, Benchmarks /
Evaluations UI, Monitor). Do not dump full `serialized_space` into the chat.

### What to inspect

| Signal | Why it matters |
|---|---|
| Agent exists? `space_id` | Distinguishes playbook 1 from 2–4 |
| Product surface: Chat vs Agent mode | Eval semantics and latency expectations differ |
| Attached tables / views / metric views, comments, grain, join keys | Data quality is the first quality lever; 30-object cap |
| Example SQL, text instructions, joins, snippets vs 100 / 200 caps | Context richness and conflict/bloat |
| Benchmark count, SQL gold vs evaluation notes | Eval readiness |
| Last Chat-mode vs Agent-mode eval scores and fail clusters | Which playbook and which lever |
| Monitor thumbs-down / review requests | Real-user gaps that benchmarks miss |
| Warehouse type; over-wide tables | Latency |
| Versioning MCP connected? | Snapshot before edits |

### Maturity stages (draft, not gospel)

| Stage | Meaning |
|---|---|
| 0 | Tables only, no agent |
| 1 | Agent exists, little/no trusted context |
| 2 | Context exists, no (or weak) benchmarks |
| 3 | Chat evals exist, accuracy below bar |
| 4 | Chat accuracy at bar; Agent-mode not ready |
| 5 | Agent-mode evals exist; latency/cost still failing |
| 6 | Production: accuracy + latency + share/certify + monitoring (+ optional versioning) |

The card names **one playbook** and **the next single stage**, not a 12-step dump.

### Draft production gates

Tune later; start here:

- Representative benchmarks exist for the questions users actually ask.
- An eval run exists in the **mode users actually use** (Chat gold-SQL comparison vs
  Agent LLM-judge + evaluation notes).
- Clustered fails have an explicit next lever (not "add more general instructions").
- Warehouse / latency is not obviously broken for that mode.
- Sharing, certification, and monitoring have been considered.

Industry folklore is "~80% Chat accuracy." Treat that as a default bar, not a law. Agent
mode has no equivalent result-set percentage; gates there are judge pass rate plus note
coverage.

## Playbooks

Fix order inside quality playbooks (Genie curation practice):

1. Data engineering or metric views
2. Metadata, comments, synonyms
3. Joins
4. Example SQL, functions, benchmarks
5. General instructions

Do not add more prose when the failure is grain, joins, or gold SQL.

### 1. Tables → agent (`tables_to_agent`)

**When:** stage 0, or a new domain with tables but no trusted agent.
**Goal:** reach stage 3 (Chat evals exist), then optionally continue through 6.

- Curate Gold / semantic objects; refuse Bronze dumps; keep the first surface small.
- Create the agent via Genie Code; review auto-suggested workspace queries.
- Metadata + joins + a handful of example SQLs.
- Write benchmarks **before** lots of instruction churn.
- Run Chat evals; iterate via native "analyze this eval run."
- Only then Agent-mode, share, certify.

### 2. Stuck tuning (`stuck_tuning`)

**When:** the user has been iterating and feels stuck; accuracy not moving, or oscillating.

- Cluster last eval / Monitor failures (wrong table, wrong grain, bad join, date logic,
  extra columns, conflicting instructions).
- Apply the fix order; check instruction / snippet caps.
- Snapshot before edits if [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/)
  is present.
- Stop after **one lever**; re-eval. Do not "keep adding instructions."

### 3. Accuracy good, latency slow (`latency`)

**When:** eval accuracy is at the bar (or users trust answers) but time-to-answer is
unacceptable.

- Confirm the product is Chat vs Agent (Agent mode is slower on purpose).
- Warehouse (prefer serverless), hide / drop unused columns, materialize expensive joins,
  trim snippet bloat, avoid Inspect-on-everything.
- Re-measure with query history / user-felt latency, not just eval accuracy.

### 4. Chat → Agent mode, benchmarks "break" (`chat_to_agent`)

**When:** user switched the conversation or eval toggle to Agent mode and Chat-era
benchmarks look worse.

- Chat evals compare result sets to gold SQL (extra columns = Bad). Agent evals use an
  LLM judge + optional **evaluation notes**.
- Keep gold SQL as *expected facts* in notes; do not expect schema-identical tables.
- Add research-style questions; run **Agent-mode** evals; retune notes, not only Chat gold.

The same router can grow later: empty Monitor (no users yet), 30-table overflow, UC
permission holes, Chat-only unstructured-file questions.

## Guided-loop contract (v1)

1. Diagnose → maturity card (stage, gaps, playbook, next stage).
2. User confirms that one stage.
3. Execute **one** native Genie Code verb (generate context, generate/rewrite benchmarks,
   analyze last eval, etc.).
4. Pause: user accepts or rejects proposed diffs.
5. Optional `save_agent_config_version` with reason `before_update` if the versioning MCP
   is connected. The coach never relays `serialized_space`.
6. Re-diagnose or advance. Stop at gates or on user halt.

If the user names a playbook explicitly ("this is too slow"), still diagnose first — the
card may redirect (for example, Agent mode explaining the latency, not a warehouse swap).

## Vehicle comparison

| Vehicle | What it is | Use when | Don't use when |
|---|---|---|---|
| Markdown playbook | Files in this repo / a workspace folder | Validating content; users who will `@` or paste | You need auto-discovery for "I'm stuck" |
| Workspace skill | Same files under `Workspace/.assistant/skills/genie-agent-production-coach/` | Content works; you want Genie Code to load the router from the description | You need server-side measurement across many agents |
| Thin diagnostic MCP | Databricks App tools: diagnose / recommend next step | Native inspection cannot produce a trustworthy card; workspace-wide readiness; persisted journey state | You want it to mutate agent config (native Genie Code already does) |

**Default recommendation:** write the playbooks as markdown in this repo; promote to a
skill with almost no rewrite; add an MCP only after a measurement gap is proven.

## Draft skill tree (packaging, not v0)

When promoting to a skill, copy the playbooks rather than inventing a second source of
truth:

```
Workspace/.assistant/skills/genie-agent-production-coach/
├── SKILL.md                         # diagnose first, emit card, guided loop, safety
├── references/
│   ├── diagnosis.md                 # inspection checklist + stage rules
│   ├── tables-to-agent.md
│   ├── stuck-tuning.md
│   ├── latency.md
│   └── chat-to-agent.md
└── scripts/
    └── maturity_card.py             # optional: counts/booleans from a live export
```

`SKILL.md` `description` must include trigger terms a real user would say, for example:
productionize a Genie Agent, tables to chat, stuck tuning, benchmark accuracy, Agent
mode benchmarks broke, Genie too slow / latency.

Safety rules for the skill:

- Always diagnose before generating.
- One stage per turn; wait for accept.
- Never dump `serialized_space` into the chat.
- Prefer the fix order over more general instructions.
- If versioning MCP tools are available, save `before_update` before a native edit;
  stop if that save fails (same contract as the versioning plugin's workspace
  instruction).

In this plugins repo the skill would later live as its own directory with tests, same
as [idea 4](./04-agent-migration.md): developed here, installed by copying into
`.assistant/skills/`.

## Maturity card shape

The card is the review surface. Keep it small enough to paste into chat. Example:

```jsonc
{
  "space_id": "3c409c00b54a44c79f79da06b82460e2",  // null if stage 0
  "product_surface": "chat",                       // "chat" | "agent"
  "stage": 3,
  "playbook": "stuck_tuning",                       // tables_to_agent | stuck_tuning | latency | chat_to_agent
  "counts": {
    "tables": 8,
    "example_sql": 4,
    "text_instructions": 1,
    "join_specs": 2,
    "knowledge_store_snippets": 11,
    "benchmarks": 12,
    "benchmarks_with_sql_gold": 12,
    "benchmarks_with_eval_notes": 0
  },
  "caps": {
    "tables_max": 30,
    "instructions_max": 100,
    "snippets_max": 200
  },
  "last_eval": {
    "mode": "chat",
    "eval_run_id": "e1ef34712a29169db030324fd0e1df5f",
    "num_correct": 7,
    "num_questions": 12,
    "fail_clusters": ["wrong_grain", "fiscal_calendar"]
  },
  "versioning_mcp": false,
  "gaps": [
    "Chat accuracy below default bar",
    "No Agent-mode eval notes (ok while product_surface is chat)",
    "Fail cluster: fiscal calendar vs calendar quarters"
  ],
  "next_stage": {
    "id": "fix_fiscal_calendar_instruction",
    "native_verb": "improve_instructions",
    "summary": "Add fiscal-quarter definitions; do not add more example SQL this turn",
    "requires_user_confirm": true
  }
}
```

A v0 markdown coach prints the same fields as a short bullet list. A later
`maturity_card.py` (or diagnostic MCP) should return this object — identifiers, counts,
and booleans, not configuration content.

## Non-goals

- Replacing native generate-instructions / generate-benchmarks / analyze-eval-run.
- Multi-turn conversation evaluation ([idea 1](./01-multi-turn-eval.md)).
- Workspace-wide cost/usage ranking ([idea 2](./02-workspace-usage-analytics.md)).
- Environment remapping of `serialized_space` ([idea 4](./04-agent-migration.md)).
- UC change blast radius ([idea 5](./05-impact-analysis.md)).
- Fully autonomous tables→production with no review (rejected for v1).
- A new slash command (Genie Code slash commands are not user-extensible; a skill's
  description is the discovery surface).

## Relationship to other plugins

| Existing piece | How the coach uses it |
|---|---|
| Native Genie Code | All mutations and eval-run analysis |
| [`mcp-genie-agent-versioning`](../mcp-genie-agent-versioning/) | Optional checkpoint before each accepted stage |
| Idea 1 multi-turn eval | Out of scope for v1; a later stage could recommend it once single-turn gates pass |
| Idea 2 analytics | Could feed latency / error signals into diagnosis if that MCP exists |

## Open questions

- **Does native inspection produce a trustworthy card without a script?** If Genie Code
  can already read table counts, benchmark lists, and last eval summaries, v0 markdown
  (and a skill with no `scripts/`) is enough. If it hallucinates counts or cannot see
  eval-run mode, add `maturity_card.py` or a diagnostic MCP.
- **Where should the default accuracy bar live?** Hard-code ~80% Chat in the playbook,
  make it a skill argument, or leave it qualitative until we have customer data.
- **Can a skill reliably detect that the versioning MCP is connected?** If not, the
  snapshot step becomes "if these tools exist, call them" and degrades gracefully.
- **Eval APIs are Beta** (`POST /api/2.0/genie/spaces/{space_id}/eval-runs`, list/get
  results). A diagnostic MCP would depend on them; a markdown/skill coach can stay on
  the UI + Genie Code's built-in eval review until the APIs stabilize.
- **Latency signal.** `system.query.history` with `query_source.genie_space_id` can
  give p50/p95, but a skill script may not have system-table access. Confirm before
  promising numeric latency on the card.
- **Workspace vs user skill.** Production coaching is a team standard → workspace
  skill. Personal prototypes can live under `/Users/{user}/.assistant/skills/` first.
- **Certification / sharing as a gate.** Stage 6 includes share/certify. Should the
  coach stop at "eval gates met" and only *mention* share/certify, so it never changes
  ACLs without an explicit ask?
