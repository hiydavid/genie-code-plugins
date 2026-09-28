# Readiness Model

Use this model only after defining the domain, workflow, rollout target, personas, and
critical business concepts. Readiness is scoped: an organization can be ready for a
Sales ARR pilot without being ready across every business domain.

A persona is **materially different** when its effective access to in-scope sources
differs — through group membership, grants, row filters, column masks, or
attribute-based policies — such that it would retrieve different rows, columns, or
answers. Compare effective access, not job titles.

## Evidence and layer statuses

Record each material finding with one evidence state:

- `verified`: observed directly by you in a current workspace object, query result,
  policy, CLI output, evaluation, or other authoritative artifact. A Genie One response
  the user pastes verbatim, including its cited sources, counts as `verified` for that
  question; a summary of what the user saw does not.
- `user-declared`: asserted by an accountable user or owner but not independently
  observed during this assessment.
- `unknown`: unavailable, conflicting, stale, or lacking an accountable confirmation.

Mandatory criteria are of two kinds, and `user-declared` means something different for
each:

- **Intent criteria** state what the organization wants or who is accountable: the
  workflow, personas, expected facts, acceptance criteria, the business meaning of a
  term, owners, and review cadence. An accountable user's declaration, recorded in the
  card with their name or role, is the terminal state for these criteria and satisfies
  them.
- **Observation criteria** state how data, metadata, semantic assets, access, or answers
  actually behave. For these, `user-declared` is provisional: it is usable evidence, but
  the criterion is not met until you or an artifact confirms it. It yields a `partial`
  layer status and caps the verdict at `Ready with conditions`, with a condition naming
  who will verify it and what triggers the review.

Use these layer statuses:

- `established`: the critical-path practices are evidenced for this scope.
- `partial`: usable evidence exists, but a named gap constrains trust or expansion.
- `missing`: a critical capability or artifact is absent.
- `not assessed`: access or evidence was insufficient.

Decide each layer status from criterion evidence using this table, not by counting:

| Evidence situation | Layer status |
|---|---|
| Every mandatory observation criterion is `verified` and every intent criterion is declared by an accountable owner | `established` |
| Every mandatory criterion is met through a verified route that is not the preferred one (for example a canonical view instead of a Metric View), and the remaining gap is named and non-blocking | `partial` |
| A mandatory observation criterion rests on `user-declared` evidence, and no criterion is absent or `unknown` | `partial` |
| A mandatory criterion is verified absent for this scope | `missing` |
| A criterion's evidence is inaccessible or unsearched, so it is neither verified nor confirmed absent | `not assessed` |

A `partial` layer must record its named gap as a condition or an expansion-backlog
item. Layer status summarizes evidence; it does not determine the verdict by simple
counting.

## Six-layer checklist

The "For the pilot path" bullets in each layer are the mandatory pilot criteria for the
declared scope. A bullet carrying an applicability qualifier — "where practical",
"when required", "when relevant", "when available and useful", "when more than one" —
is mandatory only when the qualifier's condition holds for the declared scope or
organizational policy. Record each applicability decision and its reason. A criterion
judged not applicable is neither met nor missing; it is reported as such with the reason.

### Layer 0: Physical data foundation

For the pilot path, establish that:

- Sources are curated around the selected business process rather than a raw data dump.
- Facts have a documented, consistent grain and reusable dimensions.
- Critical entities have stable identities or an explicit, validated reconciliation rule.
- The agent-facing surface avoids mixed grains and duplicate versions of the same concept.
- Data quality is sufficient for the representative questions.

Before expanding, strengthen reusable conformed dimensions, automated quality monitoring,
and purpose-built or pre-joined consumption surfaces where they reduce ambiguity.

### Layer 1: Metadata

For the pilot path, establish that:

- Every critical source explains its business purpose, grain, freshness, and caveats.
- Fields used by critical questions have meaningful comments, units, and time semantics.
- Business and technical owners are identifiable.
- Sensitive fields are classified, and the relevant domain or business function is clear.

Broader coverage, governed tag consistency, and automated metadata generation are
expansion strengths. Machine-generated metadata remains unverified until reviewed.

### Layer 2: Business semantics

For the pilot path, establish that:

- Critical join paths are declared or otherwise documented and validated; informational
  primary and foreign keys reflect reality.
- Each critical KPI has one governed definition. Prefer a Unity Catalog Metric View for
  measures, dimensions, filters, and relationships that must remain consistent.
- Critical metrics expose useful agent metadata such as display names, synonyms, formats,
  and example queries when relevant.
- Ambiguous terms have owner-reviewed definitions and authoritative sources. Prefer
  published Unity Catalog Pages for shared concepts.
- Assets are grouped into an appropriate Domain or subdomain when the feature is
  available and useful for scoping discovery.

For a constrained pilot, a verified canonical definition outside a Metric View may be a
condition rather than a blocker, but only with minimum evidence: a named owner, a dated
artifact holding the definition, logic tested against representative questions, and a
retrieval guardrail preventing a competing answer from reaching pilot users. Without
any of these, treat the gap as a blocker when competing logic exists, the metric is high
stakes, or the rollout target is `expand`. A missing Page or Domain is not automatically
a blocker when the scoped terms and sources are already unambiguous.

### Layer 3: Context-rich assets

For the pilot path, identify the dashboards, queries, notebooks, documentation, and
Genie Agents that the ontology may learn from. Confirm that authoritative assets are
current, understandable, and distinguishable from stale or experimental alternatives.
Certification and deprecation are the governed tag `system.certification_status`; an
asset without it is uncertified, which is a weaker signal than certified but not the
same as deprecated.

Certification of trusted assets, deprecation of stale assets, rich documentation, usage
signals, classification, and quality monitoring become increasingly important before
expansion. Sparse long-tail context alone does not block a narrow pilot with a strong
modeled head. When it limits the breadth of supported questions, return `Ready with
conditions` and name that boundary; when it does not affect the declared narrow scope,
record it in the expansion backlog.

### Layer 4: Governance

For the pilot path, establish that:

- Intended personas can access the required sources through maintainable group-based
  grants where practical.
- Personas cannot retrieve sources or rows and columns they are not authorized to see.
- Row filters, column masks, or attribute-based policies protect sensitive data when
  required.
- When more than one materially different persona is in scope, the effect of
  permissions on answers and citations is tested for each of them.

Unity AI Gateway controls (model access, guardrails, logging, rate and cost limits)
govern model serving endpoints and MCP or agent traffic, not Genie One itself. They are
in scope only when custom agents, Agent Bricks, or serving endpoints contribute to the
pilot and organizational policy requires them.

### Layer 5: Evaluation and improvement

For the pilot path, establish that:

- Representative questions cover the critical metrics, terms, relationships, and access
  boundaries in scope.
- Each question has expected facts or an answer, an authoritative source, acceptance
  criteria, and an owner.
- Each question's Genie One answer and executed SQL have been reviewed against its
  acceptance criteria, and the answer path (Genie Agent or data-asset search) is
  recorded.
- Each question's citations have been reviewed in the Genie One UI and point to the
  authoritative sources. The CLI does not expose citations, so this is a separate check
  from answer correctness.
- Failed questions are traced to their owning layer instead of patched with unrelated
  prose.
- Feedback ownership and a review cadence exist for the pilot.

Before expansion, add ongoing monitoring, usage review, source-quality signals, drift
checks, and Genie Agent benchmarks where domain Agents contribute to answers.

## Critical modeled head

Maintain a compact inventory of the concepts that must not be inferred incorrectly:

| Item | Kind | Governed definition or source | Owner | Evidence state | Conflict? |
|---|---|---|---|---|---|
| Example: ARR | metric | `<metric view or canonical asset>` | `<owner>` | verified | no |

Kinds normally include entity, metric, dimension, relationship, business term, policy,
and authoritative source. An unresolved conflict in this inventory is more important than
high checklist coverage elsewhere.

## Verdict rules

### Not ready

Return `Not ready` when any of these affects the declared scope:

- Critical grain, entity identity, freshness, or data-quality integrity is unresolved.
- A critical metric, term, relationship, or authoritative source is conflicting or has no
  accountable definition.
- An intended persona lacks necessary access, or sensitive data lacks required controls.
- Representative ground truth is absent, a critical question fails acceptance criteria,
  or an answer relies on an inappropriate source.
- A mandatory criterion is `unknown` or `not assessed`. Explain the evidence needed to
  clear it rather than presenting the unknown itself as a product defect.

### Ready with conditions

Return `Ready with conditions` when every mandatory criterion is evidenced, but either a
specific constraint must limit the questions, audience, sources, or rollout duration, or
a mandatory observation criterion rests on `user-declared` evidence. Examples include a
verified definition that has not yet been promoted to a Metric View, manual monitoring
for the first pilot, incomplete deprecation of non-authoritative assets that cannot
enter the pilot users' retrieval context, or a persona-access test that a representative
ran and summarized but did not paste verbatim.

Every condition must state the guardrail, owner, and event or date that triggers review.
A condition created for `user-declared` evidence names who will verify it and how.

### Ready for pilot

Return `Ready for pilot` when every mandatory observation criterion is `verified` for
the declared scope and personas, every intent criterion is declared by an accountable
owner, representative questions meet their acceptance criteria using appropriate sources
with authoritative citations, and owners and a review cadence are named. Maturity gaps
outside the declared scope remain a post-pilot backlog and do not silently broaden the
verdict.

For an `expand` target, use the same labels but evaluate the broader declared audience,
question set, asset authority, monitoring, and drift controls, and require expansion
evidence: representative questions tested under each expanded persona's effective
access, monitoring or drift checks observed over a stated window, and a defined failure
tolerance for launch. Do not reuse a narrow pilot verdict as proof of organization-wide
readiness.

## Fix ownership

Route a failed answer to the layer that owns the meaning:

| Failure | Correct destination |
|---|---|
| Mixed grain, duplicate entity, unreliable source data | Upstream data model or pipeline |
| Business definition or synonym | Unity Catalog Page |
| Measure, dimension, filter, calculation, or relationship | Metric View |
| Source description, classification, lifecycle, or access | Unity Catalog metadata or policy |
| Stale or misleading inferred context | Source dashboard, query, notebook, documentation, or Agent |
| Answer came from a Genie Agent with stale or conflicting context, or an Agent matched a question it should not own | That Agent's instructions, trusted assets, scope, or benchmarks via `databricks-genie-agents` |
