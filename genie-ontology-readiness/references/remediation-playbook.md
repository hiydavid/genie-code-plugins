# Remediation Playbook

Read this only after completing the readiness card and when the user wants help addressing
a finding. The goal is to remove one material gap and verify the result, not to perform a
broad cleanup.

## Choose the next action

Prioritize in this order:

1. Safety, permission, and sensitive-data blockers
2. Physical grain, entity identity, freshness, or data-quality blockers
3. Conflicting critical metrics, terms, sources, or join paths
4. Missing evidence and representative evaluation failures
5. Metadata, authority, and context improvements that constrain expansion
6. Continuous monitoring and maintenance

Within the same priority, harden the critical modeled head before enriching long-tail
assets. Fix meaning at its authoritative layer; do not compensate for broken data or
metric logic with general Genie Agent instructions.

## Approval contract

Before any mutation, present:

- Finding and supporting evidence
- Proposed action and exact target objects
- Why this is the owning layer
- Expected improvement and explicit non-goals
- Required privileges, side effects, and affected users
- Verification method and recovery approach when relevant

Wait for explicit approval of that action. Approval to assess readiness is not approval
to edit objects, publish Pages, change grants, certify assets, or alter an Agent. Do not
batch unrelated fixes into the approved action. In Genie Code, the platform's tool-approval
prompt satisfies this only for the exact action and target objects presented above;
confirm the approval covers them before proceeding.

After an approved action:

1. Execute with the capability that owns the surface, routing to sibling skills where
   one exists: upstream pipeline or table change (for example `databricks-pipelines` or
   `databricks-jobs`) for grain, entity, and source logic; `databricks-unity-catalog` for
   metadata, tags, certification, grants, and fine-grained controls;
   `databricks-metric-views` for Metric View logic; workspace Page authoring for business
   definitions (a manual surface — confirm owner and Sources before publishing);
   `databricks-data-discovery` for Genie One validation. Use Genie Agent instructions or
   benchmarks only for behavior truly owned by that Agent.
2. Show the observed result or proposed diff when the surface supports review.
3. Re-run only the affected checks and representative questions first.
4. Update the readiness card's evidence labels (`verified`/`user-declared`/`unknown`),
   statuses, conditions, and verdict.
5. Stop after the approved action. Offer the next action separately if a material gap
   remains.

Stop without further mutation if permissions are insufficient, validation fails, the
result affects objects outside the declared scope, or the user declines the change.

## Correction patterns

### Physical model

Clarify or repair grain, deduplication, entity reconciliation, freshness, or source logic
upstream. When upstream work cannot happen within the pilot timeline, narrow the supported
questions explicitly; do not label the original scope ready.

### Metadata and lifecycle

Improve descriptions and comments where they affect scoped questions. Apply reviewed
ownership, domain, and sensitivity tags. Certify assets only under the organization's
approval standard, and deprecate stale assets only after confirming downstream impact.

### Metric View

Place governed measures, dimensions, filters, and relationships in a Metric View when
the gap concerns numeric business logic. Add agent metadata that reflects owner-approved
language. Validate the generated SQL and representative results before clearing the gap.

### Page or Domain

Use a Page for a business definition, synonym, or concept-to-source mapping. Confirm its
owner, Sources, Related assets, and domain before publication. Publishing changes which
users can retrieve the Page, so draft creation and publication are separate review points.

### Governance

Prefer maintainable group-based grants. Test fine-grained controls with affected personas.
Never broaden access merely to make an evaluation pass; correct either the permission
design or the declared audience.

### Evaluation and context

Add or correct ground truth, authoritative-source expectations, and acceptance criteria.
When a failure comes from a stale dashboard, query, notebook, or Agent, update or
deprecate that source and verify citations. Use Agent instructions or benchmarks only
for behavior truly owned by that Agent.

