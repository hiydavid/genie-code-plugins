# 7. Persistent Agent Memory — MemCurrent Implementation Kit

**Working name:** MemCurrent implementation kit  
**Proposed shape:** Target-dependent: Genie Code CLI skill + MCP, or custom-agent workspace skill + reference template  
**Status:** Shaping — the target below is a recommendation, not a final design  
**Source:** [MemCurrent: Designing Persistent Memory for Production Agents](https://www.databricks.com/blog/memcurrent-designing-persistent-memory-production-agents)

## Research conclusion: implement the pattern, not the platform

The article's architecture is compelling, but the product boundary matters:

- Genie already uses MemCurrent internally.
- **Genie Code in the Databricks workspace** has native cross-session memory. It autonomously
  remembers and recalls durable user preferences, workspace knowledge, and project context;
  users can ask it what it remembers or tell it to update and forget memories.
- **Genie Code CLI is a separate experience.** Its documentation says that it does not share
  tools, skills, or instructions with workspace Genie Code. It supports resuming a previous
  conversation, but does not document MemCurrent-style durable memory across conversations.
- Agent Bricks exposes the MemCurrent primitives for custom agents as managed, Lakebase-backed
  **session stores**, **memory stores**, and **memory pipelines**, through AgentKit and REST.

Therefore this idea should **not** build another memory database, vector index, or dreamer.
It should adapt the managed primitives to a surface that lacks them. If the target is Genie Code
CLI, a memory skill + MCP is a real gap. If the target is custom-agent development from workspace
Genie Code, the useful gap is an opinionated integration and evaluation kit. Workspace Genie
Code itself only needs a plugin if the desired memory is explicitly shared or governed beyond
its native personal memory.

The first product decision is still open:

1. **Genie Code CLI memory adapter.** A local skill plus MCP adds managed, durable memory to
   terminal conversations. This is closest to “implement MemCurrent for Genie Code,” but the
   documented CLI extension surface lacks automatic session-start and raw-trace hooks.
2. **Custom-agent implementation kit.** Workspace Genie Code wires managed Agent Memory into
   an existing LangGraph, OpenAI Agents SDK, or other custom agent and adds a repeatable
   evaluation harness.
3. **Shared project-memory MCP for workspace Genie Code.** Add explicit team/project memory
   alongside Genie Code's native personal memory. This is genuinely additive, but cannot fully
   reproduce MemCurrent unless Genie Code extensions gain reliable session-start and raw-trace
   hooks.

## What the article says to preserve

MemCurrent combines two memory types and three access patterns:

| Concern | MemCurrent design | Managed Databricks primitive |
|---|---|---|
| Episodic memory | Append-only raw session traces | Agent session store |
| Derived memory | Mutable, hierarchical files containing distilled facts and workflows | Agent memory store entries organized by `path` |
| Automatic online behavior | Log session steps and inject a memory index at session start | Agent/framework callbacks plus a generated index from memory paths and descriptions |
| Agent-directed behavior | `search_memory`, `fetch_memory`, `add_memory`, `update_memory`, `delete_memory` | Thin tools around memory-store list, search, put, and delete operations |
| Offline consolidation | A “dreaming” pipeline extracts durable learning, merges duplicates, splits oversized files, and resolves conflicts | Managed memory pipeline connecting a session store to a memory store |

The important design lesson is the combination, not any one component:

- Derived memory did most of the work in the article's ablation: 66.1% pass rate versus
  35.8% for episodic memory alone; together they reached 68.4%.
- Offline dreaming outperformed online tools alone (63.5% versus 53.9%), while combining
  them performed best (66.1% for derived memory).
- On the internal enterprise benchmark, memory raised pass rate from 22.3% to 68.4% while
  reducing both tokens and latency. The benchmark required applying remembered workflows and
  domain knowledge, not merely recalling a string.

Those findings imply that a useful kit must include session capture, derived memory, online
tools, offline consolidation, and evaluation. Shipping only `search_memory` is not the idea.

## Candidate shape: Genie Code CLI memory adapter

The CLI can load local skills and connect to local or remote MCP servers, but its public docs do
not expose the automatic hooks used by the article's plugin path. A realistic v1 would use:

- a local Genie Code skill that instructs the agent when to search, fetch, save, update, and
  forget memory;
- an MCP backed by managed Agent Memory, with trusted server-side actor and project identity;
- an explicit `record_episode` tool that saves a compact task trace or summary for later
  dreaming, because the MCP cannot independently read the full CLI conversation;
- a generated memory index that the skill asks for at the beginning of relevant tasks;
- the same memory-dependent evaluation harness proposed below.

This is a useful memory system, but not yet faithful MemCurrent parity. Tool routing is
agent-directed rather than an unconditional session-start plugin, and episodic memory contains
only what the CLI passes to `record_episode`. A full implementation needs a future CLI lifecycle
hook or a supported conversation-export API.

Resuming a prior CLI conversation is not equivalent: resume restores one conversation, while
persistent memory extracts durable knowledge and applies it to later, unrelated conversations.

## Candidate shape: `memcurrent-agent-builder`

A Genie Code workspace skill that inspects an existing custom-agent project and implements
persistent memory using the managed Agent Memory APIs. The skill owns the workflow and design
rules; generated runtime code stays in the user's agent repository.

### Why a skill, not an MCP

The agent itself needs to read and write memory at runtime. Putting memory behind a separate
MCP merely adds another hop around APIs that AgentKit and REST already expose. Genie Code's
missing job is to correctly integrate those APIs into arbitrary agent code, establish safe
identity and retention policies, and generate an evaluation suite. That is a code-generation
and review workflow, which fits a workspace skill.

### Guided implementation flow

1. **Inspect:** Detect the agent framework, authentication model, deployed identity, existing
   conversation persistence, MLflow tracing, and evaluation setup.
2. **Choose boundaries:** Decide whether memory is per-user, team, project, or tenant. Bind
   `actor_id` from trusted application identity; never accept it from the model.
3. **Provision:** Declare or create one session store, one memory store, and one memory pipeline.
   Prefer Agent Bricks configuration where the project already uses it; otherwise generate
   AgentKit or REST setup code.
4. **Capture episodes:** Persist the full framework session state or transcript, including tool
   calls and results needed to reconstruct the task. Keep secrets and live lookup values out.
5. **Add derived-memory tools:** Give the agent search, fetch, remember/update, list-index, and
   forget tools. Explicit user corrections should take effect immediately.
6. **Load an index:** At session start, inject a compact index of paths and descriptions rather
   than all memory contents. Fetch full entries only when relevant.
7. **Enable dreaming:** Connect the stores with a managed memory pipeline. Start with manual
   runs during development; optionally move to the managed roughly-daily schedule.
8. **Evaluate:** Run memory-dependent cases with no-memory, episodic-only, derived-only, and
   combined configurations. Compare pass rate, input tokens, latency, retrieval precision, and
   harmful-memory rate in MLflow.
9. **Deploy safely:** Grant the deployed identity store access, verify delete/forget behavior,
   and document retention, security boundaries, and operating cost.

### Generated runtime contract

The exact adapter varies by framework, but the kit should converge on this interface:

| Operation | Behavior |
|---|---|
| `start_session(actor_id, session_id)` | Restore session state and load the compact derived-memory index |
| `append_session_event(event)` | Persist messages, tool calls, and results to episodic memory |
| `search_memory(query, limit)` | Search the caller's derived memory using semantic + full-text retrieval |
| `fetch_memory(path_or_id)` | Fetch a full memory entry after discovery |
| `remember(path, content, description)` | Create or replace an explicit durable memory |
| `forget(path_or_id)` | Delete a memory when asked or when policy requires it |
| `end_session()` | Flush the final session state and trace metadata |

The application binds `actor_id`; the model never supplies or changes it. Paths are model-visible
organization, not authorization boundaries.

### Memory policy defaults

The implementation kit should generate a reviewable policy alongside code:

- **Keep:** explicit preferences, corrections, authoritative sources, metric definitions,
  terminology, durable project decisions, and reusable workflows.
- **Skip:** secrets, credentials, transient query results, values available from live tools,
  unsupported inferences about the user, and one-off task details.
- **Resolve:** prefer explicit user corrections over inferred memory; retain provenance and
  timestamps; surface conflicts rather than silently choosing when confidence is low.
- **Forget:** make delete requests immediate and testable; document how derived memory relates
  to retained sessions because deleting a session does not delete already-distilled memory.

### Evaluation contract

The article's strongest contribution is its evaluation shape. Each case should contain:

- prior sessions with one or more memory-worthy signals;
- filler sessions that make retrieval non-trivial;
- a later task whose successful completion requires applying the memory;
- rubrics split into memory-dependent and task-intrinsic requirements;
- an adversarial validation pass that checks the memory is present, necessary, specific,
  natural, and objectively scorable.

The harness should report:

- task pass rate and per-rubric pass rate;
- retrieval recall and precision for gold memories;
- harmful-memory rate: stale, conflicting, cross-actor, or irrelevant memory used;
- input/output tokens, tool calls, latency, and model-serving cost;
- deltas across no-memory, episodic-only, derived-only, and combined runs.

An implementation is not done merely because memories can be saved. It is done when the
combined configuration beats the no-memory baseline without unacceptable leakage, latency,
or token growth.

## Candidate shape: shared project memory for workspace Genie Code

Native Genie Code memory is automatic and user-oriented. A narrower plugin could expose an
explicit, governed memory space shared by a team or project and portable to other agents:

- a Databricks App MCP backed by a managed memory store;
- tools such as `search_project_memory`, `fetch_project_memory`, `remember_for_project`,
  `forget_project_memory`, and `list_project_memory_index`;
- a companion skill that defines when Genie Code should consult or update the shared store;
- fixed server-side project/team identity, never a model-selected `actor_id`;
- store-per-security-boundary deployment because `actor_id` partitions data but is not access
  control.

This option should not claim full MemCurrent parity in v1. Genie Code already owns its internal
session trace, and current public extension surfaces do not provide an automatic raw-trace feed
or a guaranteed session-start injection hook. Without those, the plugin can offer explicit
derived memory but not faithful episodic capture and offline dreaming over complete sessions.

## Explicit non-goals

- Replacing Genie Code's native personal memory.
- Reimplementing Lakebase-backed session and memory stores.
- Building a custom vector-search backend or consolidation scheduler before a managed limitation
  is demonstrated.
- Dumping all historical conversations into every prompt.
- Letting the model choose another user's or tenant's `actor_id`.
- Treating `actor_id` as an authorization boundary.

## Candidate repository shape

If the recommended direction wins, the implementation could eventually look like:

```text
skills/memcurrent-agent-builder/
├── SKILL.md
├── references/
│   ├── architecture.md
│   ├── memory-policy.md
│   ├── framework-adapters.md
│   ├── security-and-retention.md
│   └── evaluation.md
├── templates/
│   ├── agentkit-memory.py
│   ├── memory-tools.py
│   └── memory-eval.py
└── scripts/
    └── inspect_agent_memory_readiness.py
```

The templates are starting points, not a framework abstraction layer. The skill should edit the
agent's existing patterns rather than introduce a new runtime framework.

## Open decisions to make together

1. **Primary target:** Genie Code CLI memory, custom-agent implementation kit, or explicit shared
   memory for workspace Genie Code?
2. **Portability:** require managed Agent Memory, or also offer a self-hosted Lakebase/UC
   implementation? The latter is substantially more scope and currently duplicates native APIs.
3. **First artifact:** begin with the integration skill, or with the evaluation harness so every
   later implementation has a measurable quality bar?
4. **Memory boundary:** default to per-user memory, project memory, or generate both patterns?
5. **Framework depth:** support one reference framework end to end first, or generate thinner
   adapters for LangGraph and OpenAI Agents SDK together?
6. **Provenance:** is source session, timestamp, confidence, and supersession metadata required
   in v1 even though managed memory entries expose a simpler content/path model?

