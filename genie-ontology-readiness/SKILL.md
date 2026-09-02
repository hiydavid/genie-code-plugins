---
name: genie-ontology-readiness
description: Assess whether one business domain's data and semantic layer are ready for a trustworthy Genie Ontology pilot, produce an evidence-backed six-layer verdict, and guide the next approved remediation. Use for Genie Ontology readiness, semantic-layer readiness, or Genie One launch preparation; not for isolated Genie Agent tuning.
---

# Genie Ontology Readiness

Assess readiness at the level Genie Ontology can improve safely: one business domain,
one valuable workflow, and the critical definitions and sources that must be right.
Use the six layers from [Operationalizing Genie Ontology in Your Data
Stack](https://www.databricks.com/blog/operationalizing-genie-ontology-your-data-stack)
as a progressive trust model, not as an all-or-nothing certification.

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
- Intended user personas and any materially different permission profiles
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
   1. Physical data foundation
   2. Metadata
   3. Business semantics
   4. Context-rich assets
   5. Governance
   6. Evaluation and improvement
3. Read [readiness-model.md](references/readiness-model.md) before assigning layer
   statuses, blockers, conditions, and the overall verdict.
4. Validate representative questions in Genie One when the surface and required access
   are available. Review answer correctness, source citations, and differences between
   intended personas.
5. Return the readiness card below. State the evidence behind every blocker and
   condition; avoid generic advice.

```markdown
# Genie Ontology Readiness Card

**Scope:** <domain, workflow, target, personas>
**Verdict:** Ready for pilot | Ready with conditions | Not ready

## Blockers
<Finding, evidence state, impact, and responsible layer. Say "None" if empty.>

## Conditions
<Constraint that limits questions, audience, or expansion. Say "None" if empty.>

## Layer maturity
| Layer | Status | Strongest evidence | Critical gap |
|---|---|---|---|

## Critical modeled head
<Critical entities, metrics, terms, relationships, and authoritative sources with state.>

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

Route isolated Genie Agent benchmark, instruction, or latency tuning to the relevant
Genie Agent workflow unless it is evidence for this domain-level Ontology assessment.
