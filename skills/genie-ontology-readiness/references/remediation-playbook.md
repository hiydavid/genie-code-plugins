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

Wait for the user's explicit in-chat approval of that action. Approval to assess
readiness is not approval to edit objects, publish Pages or Wikis, change grants, certify
assets, or alter an Agent. Do not batch unrelated fixes into the approved action.

A host tool-approval prompt is not this approval. An automatically approved tool call
authorizes execution in the host but does not supply the user's decision to change the
named Databricks objects. Ask in the chat, wait for a yes that names the action and its
target objects, and only then run the tool call.

After an approved action:

1. Execute with the capability that owns the surface, routing to sibling skills where
   one is installed:
   - Upstream pipeline or table change for grain, entity, and source logic:
     `databricks-pipelines` or `databricks-jobs`.
   - Metadata, tags, certification, grants, and fine-grained controls:
     `databricks-unity-catalog`.
   - Metric View logic: `databricks-metric-views`.
   - Business definitions: Pages in the workspace. Genie Code can draft a Page, and can
     bulk-draft Pages extracted from attached documents. Drafts are visible only in the
     owner's Genie One conversations until the owner or a curator publishes them.
     Curator access is `MANAGE DISCOVER` at account scope or `MANAGE` on the domain or
     subdomain. Confirm owner, Sources, and Related assets before publication.
   - Rich documentation about one table: its Unity Catalog Wiki when the Beta feature is
     available and the table is eligible; otherwise use table and column comments or
     another owner-reviewed source. Review the Wiki separately from the table comment.
   - Genie One validation: the Genie One MCP when configured,
     `databricks-data-discovery` from a CLI runtime, or the Genie One UI.
   - Genie Agent instructions, trusted assets, scope, or benchmarks:
     `databricks-genie-agents`, only for behavior truly owned by that Agent.
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
ownership, domain, and sensitivity tags. Certification and deprecation set the governed
tag `system.certification_status` to `certified` or `deprecated`; applying it always
needs `ASSIGN` on the tag. For a Unity Catalog securable, it also requires ownership or
`APPLY TAG`, `USE SCHEMA`, and `USE CATALOG`; workspace objects use their own object
permissions. Certify only under the organization's approval standard, and deprecate stale
assets only after confirming downstream impact.

### Metric View

Place governed measures, dimensions, filters, and relationships in a Metric View when
the gap concerns numeric business logic. Add reviewed comments, display names, synonyms,
and formats where they help agents and users. Validate the generated SQL and
representative results before clearing the gap.

### Page, Wiki, or Domain

Use a Page for a business definition, synonym, or concept-to-source mapping that spans
assets. Confirm its owner, Sources, Related assets, and domain before publication.
Publishing changes which users can retrieve the Page, so draft creation and publication
are separate review points, each with its own approval. Pages are an account-level Beta
feature; their data can be replicated globally and does not support customer-managed-key
encryption. Do not put PII, regulated data, or other sensitive content in Page names,
descriptions, synonyms, or body text.

Use a Unity Catalog Wiki for richer documentation about one table, such as its purpose,
intended use, sources, and caveats. A Wiki is not a replacement for a Page that defines a
concept across assets, and it is not mandatory when existing table metadata is adequate.
Publishing makes the Wiki visible to users who can view that table's metadata. Because
the Wiki and table comment are independent after creation, review both and resolve any
conflict before relying on the Wiki. Wikis are Beta, and Wiki data does not support
customer-managed-key encryption; do not put sensitive content in a Wiki.

Assigning an asset to a Domain applies that domain's governed tag, so it follows governed
tag permissions. Tag and domain metadata can be replicated globally and tag data is
stored as plain text; never put sensitive data in names, values, descriptions, or other
tag metadata.

### Governance

Prefer maintainable group-based grants. For consistent row filtering or column masking
across many tables, prefer ABAC policies over repeated table-level UDF assignments. Test
fine-grained controls with affected personas. Never broaden access merely to make an
evaluation pass; correct either the permission design or the declared audience.

### Evaluation and context

Add or correct ground truth, authoritative-source expectations, and acceptance criteria.
When a failure comes from a stale dashboard, query, notebook, or Agent, update or
deprecate that source and verify citations through CLI source links, Genie One MCP source
deep links, or the Genie One UI. When a question was answered by a Genie Agent that
should not own it, correct that Agent's scope or description rather than the Ontology
assets. Use Agent instructions or benchmarks only for behavior truly owned by that Agent.
