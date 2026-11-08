# Evidence Collection

Collect enough evidence to judge the declared scope without turning the assessment into
an estate-wide catalog project. Prefer current, authoritative artifacts over prose claims.

## Runtime and routing

Detect the runtime before planning evidence collection:

- **Genie Code Agent mode.** You act with the invoking user's Unity Catalog permissions
  through Genie Code's tools: running SQL, reading Unity Catalog metadata, reading
  notebooks and workspace files, and any managed MCP servers the user added. A terminal
  and the databricks CLI are not guaranteed. Prefer the Databricks-provided Genie One MCP
  when it is available; otherwise use the Genie One UI. Do not load `databricks-core`
  here unless you are actually using the CLI; its profile-selection flow applies only to
  CLI runtimes.
- **Claude Code, Cursor, or another CLI runtime.** Load `databricks-core` first for CLI,
  auth, and profile selection, then the product skill that owns each surface. Confirm
  `databricks genie ask --help` works before promising CLI validation; it needs CLI
  v1.9.0 or newer.

Inspect natively before asking: Unity Catalog and `INFORMATION_SCHEMA` metadata, Catalog
Explorer definitions, workspace search, and read-only SQL. Route deeper inspection to
the sibling skill that owns the surface:

| Evidence need | Route |
|---|---|
| CLI availability, auth, profiles, warehouse discovery (CLI runtimes only) | `databricks-core` |
| Genie One validation through MCP | Genie One MCP (`system.ai.genie_one_mcp`); `databricks-unity-gateway` for setup or permissions |
| Genie One question validation from the CLI | `databricks-data-discovery` (`databricks genie ask`) |
| Genie Agent configuration, benchmarks, eval runs, monitoring | `databricks-genie-agents` |
| Metric View definitions, generated SQL | `databricks-metric-views` |
| Grants, tags, classification, row filters, column masks, system tables | `databricks-unity-catalog` |
| Bounded read-only SQL for grain, freshness, keys, tags, and access | [inspection-queries.md](inspection-queries.md) |

A skill that is not installed cannot be routed to; fall back to the workspace UI and say
so in the card.

Keep the assessment non-mutating for data and configuration in every runtime. Genie One
tests necessarily create conversation, query-history, and audit records and consume the
selected warehouse; keep them bounded and identify their session labels as assessment
artifacts. Host auto-approval does not expand the assessment scope.

## Collection order

1. Inspect assets and evaluation artifacts already named by the user.
2. Discover adjacent objects needed to understand grain, joins, authority, and access.
3. Run read-only metadata or aggregate queries when they materially resolve a criterion.
4. Ask the accountable user or owner for business intent that cannot be inferred.
5. Mark anything still unresolved as `unknown` with a concrete validation request.

When artifacts disagree, prefer the asset that owns that kind of meaning: validated
source data for facts, a governed Metric View for KPI logic, a published Page for a
cross-asset business concept, owner-reviewed table metadata or a published Wiki for
table-specific documentation, and grants or policies for access. Certification is a
strong authority signal, not proof that an asset is correct; popularity is a relevance
signal, not an approval. Staleness is itself a finding. Record a stale or conflicting
authoritative candidate as a conflict to resolve rather than as supporting evidence.

Do not sample raw sensitive values merely to prove that a column exists. Prefer metadata,
aggregates, null and uniqueness summaries, and masked or synthetic examples. Respect the
current user's permissions; do not ask to bypass them for the audit.

## Scope evidence

The workflow, users, critical questions, expected answers, and business owners are intent,
not schema facts. Confirm them with the user. Candidate source names, schemas, existing
semantic assets, and current grants are discoverable facts; inspect them before asking.

If several domains are plausible, present the discovered candidates and recommend the
smallest one whose correctness can be evaluated.

## Layer 0: Physical data foundation

Inspect table and view definitions, lineage where available, declared constraints, and
aggregate data profiles. Determine:

- Row meaning and grain for each critical source
- Key uniqueness, null behavior, freshness, and duplication at the required grain
- Whether critical dimensions are reused consistently
- How cross-system entity identifiers are reconciled
- Whether a purpose-built view or Metric View shields users from mixed-grain internals

Use bounded read-only queries for claims such as uniqueness or freshness. Bounded
means: aggregate or summary output, predicates scoped to the critical sources and a
recent time window, and an explicit row limit on any preview. Templates are in
[inspection-queries.md](inspection-queries.md). A table name, column name, or declared
key is not proof that the underlying data satisfies the claim.

## Layer 1: Metadata

Inspect Unity Catalog table descriptions, column comments, owners, tags, and relevant
classification results. Judge usefulness, not presence alone: placeholder comments and
restatements of a column name do not explain business meaning.

For critical fields, look for units, timezone or calendar meaning, valid population,
freshness, caveats, and sensitivity. Report coverage for the scoped assets without
inventing a universal percentage threshold.

Where available, inspect the published Unity Catalog Wiki for each critical table for
its purpose, intended use, sources, and caveats. A Wiki documents one table; use a Page
instead for a concept that spans assets. A Wiki is optional supporting evidence when
owner-reviewed comments or other scoped documentation already establish the same facts.
Wikis are Beta. Published Wiki visibility follows access to the table's metadata, and a
Wiki and the table comment do not stay synchronized after the Wiki is created, so check
both for conflicts. Wiki data does not support customer-managed-key encryption; do not
put sensitive content in it.

## Layer 2: Business semantics

Inspect:

- Primary keys, foreign keys, and the data evidence supporting them
- Metric View sources, joins, measures, fields (also called dimensions), filters, and
  agent metadata (`comment`, `display_name`, `synonyms`, and `format`)
- Competing definitions for the critical concepts, in the dashboards, queries, views,
  and Genie Agents surfaced by a workspace search scoped to those concepts. Report
  "no conflict found within the searched scope"; never report search absence as proof
  that one governed definition exists
- Domain or subdomain membership and ownership. Domains are account-level organization
  layers built on governed tags; subdomain tag keys use the
  `<domain-tag>/<subdomain>` convention. Membership for catalog objects is visible in
  `TABLE_TAGS`, `SCHEMA_TAGS`, and `CATALOG_TAGS`, and workspace and catalog assets can
  be inspected on their domain page in Discover. Do not label Domains or Discover as a
  preview unless the current workspace says so. On compliance-security-profile
  workspaces, Discover is disabled by default; if the required surface is unavailable,
  record the setting or access limitation and the resulting evidence gap
- Page state, owner review, term definitions, Synonyms, Sources, and Related assets

Draft Pages are available only in the Page owner's own Genie One conversations.
Published Pages are available in every Genie One conversation and are cited in answers.
Pages are Beta. Only the Page owner or a curator can edit or publish a draft; curator
access is `MANAGE DISCOVER` at account scope or `MANAGE` on a domain or subdomain.
Record whether a Page is draft or published and whether its intended audience can
therefore retrieve it. Record preview or permission limitations separately from content
gaps.

## Layer 3: Context-rich assets

Inventory only assets relevant to the scoped workflow: commonly used dashboards and
queries, notebooks, documentation including published table Wikis, and Genie Agents.
For each authoritative candidate, inspect freshness, use, description quality, owner,
certification, and conflicting stale alternatives. Absence of a large asset corpus is
evidence of limited inferred context, not automatic evidence that the modeled head is
wrong.

Certification and deprecation are the governed tag `system.certification_status` with
the values `certified` and `deprecated`. For catalog objects, read it from `TABLE_TAGS`
or the other tag views. For dashboards, Genie Agents, and apps, which search cannot
filter by tag, read the badge on the asset or its Discover entry. Absence of the tag
means uncertified, not deprecated.

## Layer 4: Governance

Inspect effective access for each materially different persona, preferably through group
membership and current Unity Catalog grants. Record relevant row filters, column masks,
governed tags, attribute-based policies, Unity Gateway policies on MCP services, and any
legacy AI Gateway controls on Model Serving endpoints in scope.

Confirm that each persona can use Genie One: Consumer access or a higher qualifying
entitlement, `CAN USE` on at least one SQL warehouse, and access to the required data and
semantic assets. When validation uses the Genie One MCP, also confirm `EXECUTE` on
`system.ai.genie_one_mcp` and use on-behalf-of user authentication for persona evidence.

Do not assume that the assessor's access represents a consumer. No runtime here can
impersonate another persona. A negative-access check that was not executed stays
`unknown` and leaves the mandatory governance criterion `unknown`; it is never a
`user-declared` pass. When more than one materially different persona is in scope, ask
an authorized representative of each to run the same questions in Genie One and paste
the full responses. A verbatim response is `verified` for that persona; a summary is
`user-declared` and caps the verdict as described in readiness-model.md.

## Layer 5: Evaluation and improvement

Represent each test case with:

| Field | Purpose |
|---|---|
| Question | Natural wording the intended persona will use |
| Persona | Permission context being tested |
| Expected facts or answer | Ground truth needed to judge correctness |
| Authoritative source | Asset that should support the answer |
| Acceptance criteria | Required facts, tolerances, format, and prohibited leakage |
| Answer path | Genie Agent, data-asset search, connected source, or personal context |
| Result and citations | Observed answer, any executed SQL, pass/fail, and cited sources or deep links |
| Evidence state | `verified`, `user-declared`, or `unknown` for this result |
| Owner | Person accountable for validation and follow-up |

Genie One searches available Genie Agents first and answers from a matching Agent before
it searches data assets and connected sources, and it prioritizes human-modeled context
in Pages over inferred context. Record the path for every question. When an Agent answers,
attribute the primary result to that Agent and inspect its citations or configuration
before also crediting an underlying Page, Metric View, or source.

Capture results this way:

- Genie One MCP: `genie_poll_response` returns the final answer and deep links to cited
  Databricks sources; MCP Apps can render Ontology citations inline. Prefer on-behalf-of
  user authentication for persona testing and confirm the caller has `EXECUTE` on
  `system.ai.genie_one_mcp`. A service principal test represents only that principal.
- CLI: `databricks genie ask --output json` returns status, answer text, and SQL tool
  calls when SQL ran. It has no structured citation field, but current responses can
  include Databricks source links in the answer text. Review those links when present;
  use the MCP or UI when they are absent or incomplete.
- Inline MCP and CLI query results can be truncated. When acceptance depends on complete
  rows rather than an aggregate answer, use `genie_get_query_result` through MCP or run
  the captured read-only SQL on a warehouse and validate the full result.
- Genie One UI: click the citation icons on the response to see the knowledge sources
  used. A complete response supplied with its source list can support verification; a
  summary of what the user saw is `user-declared`.
- Start each test in a fresh conversation, but do not assume that removes all personal
  context. Genie One can use saved memories, prior conversations, installed skills,
  workspace instructions, and connected sources. Prefer a dedicated clean pilot user;
  otherwise inspect citations and record any context that could confound the result.
- If `/Workspace/.genie_workspace_instructions.md` exists, inspect both its relevant
  content and file ACL. Genie One reads it with the chatting user's permissions and does
  not warn users who cannot view it, so inconsistent sharing can create silent persona
  differences.

Exercise critical metrics, synonyms, time logic, join paths, entity resolution, source
selection, and permission boundaries. Inspect citations rather than judging answer
fluency alone. If a Genie Agent supplies domain context, use its monitoring and
benchmarks as supporting evidence, not as a substitute for the Ontology-level question
set.

## Useful inspection surfaces

Depending on available capabilities and permissions, evidence may come from:

- Unity Catalog and `INFORMATION_SCHEMA` metadata for tables, columns, constraints,
  tags, and fine-grained controls (`TABLES`, `VIEWS`, `COLUMNS`, `SCHEMATA`,
  `TABLE_CONSTRAINTS`, `KEY_COLUMN_USAGE`, `REFERENTIAL_CONSTRAINTS`, `CATALOG_TAGS`,
  `TABLE_TAGS`, `COLUMN_TAGS`, `SCHEMA_TAGS`, `ROW_FILTERS`, `COLUMN_MASKS`,
  `ABAC_POLICY_DEFINITIONS`, `TABLE_PRIVILEGES`);
  templates in [inspection-queries.md](inspection-queries.md), deeper detail through
  `databricks-unity-catalog`
- Catalog Explorer definitions for Metric Views and other governed assets, including
  published Wikis on critical tables
- Discover for Domains, Pages, ownership, lifecycle, and certification badges
- Workspace search and object metadata for dashboards, queries, notebooks, and Agents
- Genie One UI answers and source citations, or Genie One MCP answers and source deep
  links
- Genie Agent Monitor and benchmark results for contributing Agents
- Genie One workspace instructions (`/Workspace/.genie_workspace_instructions.md`) and,
  when relevant to a test, user memories, installed skills, prior-chat citations, and
  connected sources
- Query history, audit logs, lineage, and quality monitoring
  (`system.query.history`, `system.access.audit`, `system.access.table_lineage`)
- Organization policies and owner-reviewed business documentation

Use only surfaces available in the current environment. Do not claim a check was
automated when it was manually confirmed, or claim workspace-wide completeness from a
partial search. State the scope you actually searched for every "no conflict found"
conclusion, and copy it into the card's "Evidence scope searched" section.
