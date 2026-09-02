---
name: genie-ontology-readiness
description: "Assess whether one business domain's data and semantic layer are ready for a trustworthy Genie Ontology pilot, produce an evidence-backed verdict across six layers, and guide the next approved remediation. Use when asked whether data or the semantic layer is ready for Genie ('is our data ready for Genie', 'should we pilot Genie Ontology for sales'), to audit or assess Genie Ontology or semantic-layer readiness, to prepare a domain for a Genie One pilot or launch, or to act on the blockers and conditions such an assessment found. Not for isolated Genie Agent benchmark, instruction, or latency tuning (use the Genie Agent workflows in the Databricks workspace, not this repo's skills), estate-wide data-quality audits, or building semantic assets without a readiness question (use databricks-metric-views or databricks-unity-catalog)."
compatibility: Runs in Genie Code inside the Databricks workspace with the invoking user's Unity Catalog permissions; Genie One question validation requires databricks CLI with the experimental genie command (see databricks-data-discovery)
metadata:
  version: "0.1.0"
parent: databricks-core
---

# Genie Ontology Readiness

Assess readiness at the level Genie Ontology can improve safely: one business domain,
one valuable workflow, and the critical definitions and sources that must be right.
Use the six layers from [Operationalizing Genie Ontology in Your Data
Stack](https://www.databricks.com/blog/operationalizing-genie-ontology-your-data-stack)
as a progressive trust model, not as an all-or-nothing certification.

This skill runs in Genie Code inside the Databricks workspace, acting with the
invoking user's Unity Catalog permissions. Inspect natively first — Unity Catalog
metadata, Catalog Explorer, workspace search, and approved read-only SQL execution — and
follow the sibling-skill routing in
[evidence-collection.md](references/evidence-collection.md) rather than asking the user
for facts the workspace can show.

## Operating principles

- Model the important "head" deliberately and let the ontology infer the long tail.
- Audit the declared domain and audience, not the entire data estate.
- Inspect before asking. Ask the user only for intent or business evidence that cannot
  be discovered from available assets.
- Label evidence as `verified`, `user-declared`, or `unknown`. Never turn missing access
  or missing evidence into a pass.
- Keep the initial assessment read-only. Creating or changing data, semantic assets,
  permissions, certification, Pages, or Genie Agents requires a separate, explicit
  user approval for the proposed action.
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

1. Read [evidence-collection.md](references/evidence-collection.md), inventory the
   accessible evidence, and identify what must be supplied or confirmed by a human.
2. Assess the domain in dependency order:
   1. Layer 0: Physical data foundation
   2. Layer 1: Metadata
   3. Layer 2: Business semantics
   4. Layer 3: Context-rich assets
   5. Layer 4: Governance
   6. Layer 5: Evaluation and improvement
3. Read [readiness-model.md](references/readiness-model.md) before assigning layer
   statuses, blockers, conditions, and the overall verdict. The "For the pilot path"
   bullets there are the mandatory pilot criteria; apply its status decision table and
   verdict rules exactly so two assessments of the same scope reach the same verdict.
4. Validate representative questions in Genie One when the surface and required access
   are available. Use the databricks-data-discovery skill
   (`databricks experimental genie ask`) to run each question and capture the answer,
   SQL, and citations. Review answer correctness, source citations, and differences
   between intended personas. If the surface you used does not expose citations, record
   citation correctness as `unknown` rather than inferring it.
5. Return the readiness card below. State the evidence behind every blocker and
   condition; avoid generic advice.

```markdown
# Genie Ontology Readiness Card

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

## Unknowns requiring validation
<Missing evidence, who can validate it, and why it matters.>

## Prioritized actions
1. Before pilot
2. Before expansion
3. Continuous improvement

## Recommended next action
<One smallest, highest-impact action and how success will be verified.>
```

## Guide improvement only after the assessment

When the user asks to address a finding, read
[remediation-playbook.md](references/remediation-playbook.md). Propose one action with
its target objects, expected effect, side effects, required privileges, and verification
step. Wait for explicit approval before making the change. Reassess the affected
criteria after the action and then stop or propose the next action.

Route isolated Genie Agent benchmark, instruction, or latency tuning to the Genie Agent
workflow in the workspace (no skill in this repo covers it) unless it is evidence for
this domain-level Ontology assessment.
