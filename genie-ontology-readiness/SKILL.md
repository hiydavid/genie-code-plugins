---
name: genie-ontology-readiness
description: "Assess whether one business domain's data and semantic layer are ready for a trustworthy Genie Ontology pilot, produce an evidence-backed verdict across six layers, and guide the next approved remediation. Use when asked whether data or the semantic layer is ready for Genie ('is our data ready for Genie', 'should we pilot Genie Ontology for sales'), to audit or assess Genie Ontology or semantic-layer readiness, to prepare a domain for a Genie One pilot or launch, or to act on the blockers and conditions such an assessment found. Not for isolated Genie Agent benchmark, instruction, or latency tuning (use databricks-genie-agents), estate-wide data-quality audits, or building semantic assets without a readiness question (use databricks-metric-views or databricks-unity-catalog)."
compatibility: Designed for Genie Code Agent mode in the Databricks workspace; also runs from Claude Code or Cursor with the Databricks agent skills installed. Acts with the invoking user's Unity Catalog permissions. Genie One validation from the CLI needs databricks CLI >= v1.9.0 (databricks genie ask); without a CLI, validate in the Genie One UI as described in references/evidence-collection.md.
metadata:
  version: "0.2.0"
  parent: databricks-core
---

# Genie Ontology Readiness

Assess readiness at the level Genie Ontology can improve safely: one business domain,
one valuable workflow, and the critical definitions and sources that must be right.
Use the six layers from [Operationalizing Genie Ontology in Your Data
Stack](https://www.databricks.com/blog/operationalizing-genie-ontology-your-data-stack)
as a progressive trust model, not as an all-or-nothing certification.

## Runtime

This skill is designed for Genie Code Agent mode inside the Databricks workspace and
also works from Claude Code or Cursor with the Databricks agent skills and CLI. In every
runtime you act with the invoking user's Unity Catalog permissions. Inspect natively
first: Unity Catalog and `INFORMATION_SCHEMA` metadata, Catalog Explorer, workspace
search, and read-only SQL. Follow the runtime detection and sibling-skill routing in
[evidence-collection.md](references/evidence-collection.md) rather than asking the user
for facts the workspace can show.

Genie Code does not guarantee a terminal or the databricks CLI, and its managed MCP
servers include Genie Agents but not Genie One. Check whether `databricks genie ask` is
available before planning CLI validation. Otherwise the user runs representative
questions in the Genie One UI and pastes the responses.

## Operating principles

- Model the important "head" deliberately and let the ontology infer the long tail.
- Audit the declared domain and audience, not the entire data estate.
- Inspect before asking. Ask the user only for intent or business evidence that cannot
  be discovered from available assets.
- Label evidence as `verified`, `user-declared`, or `unknown`. Never turn missing access
  or missing evidence into a pass.
- Keep the initial assessment read-only regardless of the host's tool-approval mode:
  issue only `SELECT`, `SHOW`, and `DESCRIBE` statements and read-only API or CLI calls.
  Genie Code's Auto-approve classifier is not a substitute for this rule.
- Creating or changing data, semantic assets, permissions, certification, Pages, or
  Genie Agents requires a separate, explicit in-chat approval from the user for the
  proposed action, even when the host would auto-approve the tool call.
- Do not use a numeric readiness score. It hides critical blockers and implies precision
  the evidence does not support.

## Establish the assessment scope

Record the following before assigning a verdict:

- Business domain and recurring workflow or decision to support
- Rollout target: `pilot` by default, or `expand` for a broader audience
- Intended user personas and any materially different permission profiles (as defined in
  [readiness-model.md](references/readiness-model.md))
- Critical entities, metrics, dimensions, relationships, and business terms
- Candidate authoritative sources and owners
- Representative questions, expected facts or answers, authoritative sources, and
  acceptance criteria

If the user has not chosen a domain, help select one recurring, high-friction workflow
where the organization already knows what a correct answer looks like. Keep the initial
scope narrow.

## Run the audit

1. Read [evidence-collection.md](references/evidence-collection.md), detect the runtime
   and available surfaces, inventory the accessible evidence, and identify what must be
   supplied or confirmed by a human.
2. Assess the domain in dependency order:
   1. Layer 0: Physical data foundation
   2. Layer 1: Metadata
   3. Layer 2: Business semantics
   4. Layer 3: Context-rich assets
   5. Layer 4: Governance
   6. Layer 5: Evaluation and improvement

   Use [inspection-queries.md](references/inspection-queries.md) for the bounded
   read-only queries behind Layer 0 to Layer 4 claims.
3. Read [readiness-model.md](references/readiness-model.md) before assigning layer
   statuses, blockers, conditions, and the overall verdict. The "For the pilot path"
   bullets there are the mandatory pilot criteria; apply its status decision table and
   verdict rules exactly so two assessments of the same scope reach the same verdict.
4. Validate representative questions in Genie One. Judge two things separately:
   - Answer correctness. Run each question through `databricks genie ask` via the
     databricks-data-discovery skill when the CLI is available, or have the user run it
     in the Genie One UI and paste the full response. Compare the answer and executed
     SQL against the expected facts and acceptance criteria.
   - Citation appropriateness. The CLI output has no citation field. Citations are
     visible only through the citation icons in the Genie One UI, so this check happens
     there, by the assessor or an owner. Record the sources cited and whether they are
     the authoritative ones.

   For every question record the answer path: Genie One searches Genie Agents first and
   answers from a matching Agent before searching data assets, so a pass may belong to
   an Agent rather than to the Ontology. Test materially different personas when more
   than one is in scope. Label each result `verified` or `user-declared` per the rules
   in readiness-model.md; a check that did not run stays `unknown`.
5. Return the readiness card below. State the evidence behind every blocker and
   condition; avoid generic advice.

```markdown
# Genie Ontology Readiness Card

**Assessed:** <date> by <assessor>, running in <Genie Code | Claude Code | Cursor>
**Scope:** <domain, workflow, target, personas>
**Verdict:** Ready for pilot | Ready with conditions | Not ready
**Owners and review cadence:** <pilot feedback owner(s) and review cadence; required for
a `Ready for pilot` verdict>

## Blockers
<Finding, evidence state, impact, and responsible layer. Say "None" if empty.>

## Conditions
<Guardrail limiting the questions, audience, sources, or rollout duration. Each
condition states the guardrail, its owner, and the event or date that triggers review.
Say "None" if empty.>

## Layer maturity
| Layer | Status | Strongest evidence | Critical gap |
|---|---|---|---|

## Critical modeled head
<Critical entities, metrics, dimensions, terms, relationships, policies, and
authoritative sources with state.>

## Representative questions
| Question | Persona | Answer path | Result | Citations | Evidence state | Owner |
|---|---|---|---|---|---|---|

## Evidence scope searched
<Catalogs, schemas, workspace folders, search terms, and surfaces actually inspected.
Every "no conflict found" finding refers to this scope.>

## Unknowns requiring validation
<Missing evidence, who can validate it, and why it matters.>

## Prioritized actions
1. Before pilot
2. Before expansion
3. Continuous improvement

## Recommended next action
<One smallest, highest-impact action and how success will be verified.>
```

### Example entries

A well-formed blocker names the object, the observation, its evidence state, and the
owning layer:

> **Blocker (Layer 2):** `sales.gold.arr_metrics` and the "ARR Overview" dashboard
> compute ARR with different churn treatment; the dashboard excludes downgrades.
> `verified` from the Metric View YAML and the dashboard dataset SQL. Impact: the pilot
> question "What is ARR this quarter?" can return two answers. Definition owner:
> `unknown`; the Finance analytics lead is to confirm.

A well-formed condition names the guardrail, the owner, and the review trigger:

> **Condition:** Pilot questions are limited to the ARR, NRR, and pipeline measures in
> `sales.gold.arr_metrics`; regional headcount questions are out of scope until the HR
> join path is validated. Owner: sales analytics lead. Review when the `dim_region`
> reconciliation lands or on 2026-10-15, whichever comes first.

## Guide improvement only after the assessment

When the user asks to address a finding, read
[remediation-playbook.md](references/remediation-playbook.md). Propose one action with
its target objects, expected effect, side effects, required privileges, and verification
step. Wait for the user's explicit in-chat approval before making the change; a host
tool-approval prompt or an Auto-approve decision is not that approval. Reassess the
affected criteria after the action and then stop or propose the next action.

Route isolated Genie Agent benchmark, instruction, or latency tuning to the
databricks-genie-agents skill when it is installed, otherwise to the Genie Agent editor
in the workspace, unless the result is evidence for this domain-level Ontology
assessment.
