# Evidence Collection

Collect enough evidence to judge the declared scope without turning the assessment into
an estate-wide catalog project. Prefer current, authoritative artifacts over prose claims.

## Runtime and routing

You run inside Genie Code in the Databricks workspace with the invoking user's Unity
Catalog permissions. Inspect natively before asking: Unity Catalog and
`INFORMATION_SCHEMA` metadata, Catalog Explorer definitions, workspace search, and
read-only SQL execution through Genie Code's approved actions. Route deeper inspection
to the sibling skill that owns the surface:

| Evidence need | Route |
|---|---|
| CLI availability, auth, warehouse discovery, query execution | `databricks-core` |
| Genie One question validation | `databricks-data-discovery` (`databricks experimental genie ask`) |
| Metric View definitions, generated SQL | `databricks-metric-views` |
| Grants, tags, classification, row filters, column masks, system tables | `databricks-unity-catalog` |

## Collection order

1. Inspect assets and evaluation artifacts already named by the user.
2. Discover adjacent objects needed to understand grain, joins, authority, and access.
3. Run read-only metadata or aggregate queries when they materially resolve a criterion.
4. Ask the accountable user or owner for business intent that cannot be inferred.
5. Mark anything still unresolved as `unknown` with a concrete validation request.

When artifacts disagree, prefer them in this authority order: an owner-approved
governed asset (Metric View, published Page), then a certified asset, then a documented
owner declaration, then uncertified content. Staleness is itself a finding: prefer
artifacts with recent review or update signals, and record a stale authoritative
candidate as a conflict to resolve rather than as supporting evidence.

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
recent time window, and an explicit row limit on any preview. A table name, column
name, or declared key is not proof that the underlying data satisfies the claim.

## Layer 1: Metadata

Inspect Unity Catalog table descriptions, column comments, owners, tags, and relevant
classification results. Judge usefulness, not presence alone: placeholder comments and
restatements of a column name do not explain business meaning.

For critical fields, look for units, timezone or calendar meaning, valid population,
freshness, caveats, and sensitivity. Report coverage for the scoped assets without
inventing a universal percentage threshold.

## Layer 2: Business semantics

Inspect:

- Primary keys, foreign keys, and the data evidence supporting them
- Metric View sources, joins, measures, dimensions, filters, formats, synonyms, and
  example queries
- Competing definitions for the critical concepts, in the dashboards, queries, views,
  and Genie Agents surfaced by a workspace search scoped to those concepts. Report
  "no conflict found within the searched scope"; never report search absence as proof
  that one governed definition exists
- Domain or subdomain membership and ownership
- Page state, owner review, term definitions, Sources, and Related assets

Draft Pages are not generally retrievable by all Genie One users. Record whether a Page
is draft or published and whether its intended audience can use it. Record preview or
permission limitations separately from content gaps.

## Layer 3: Context-rich assets

Inventory only assets relevant to the scoped workflow: commonly used dashboards and
queries, notebooks, documentation, and Genie Agents. For each authoritative candidate,
inspect freshness, use, description quality, owner, certification, and conflicting stale
alternatives. Absence of a large asset corpus is evidence of limited inferred context,
not automatic evidence that the modeled head is wrong.

## Layer 4: Governance

Inspect effective access for each materially different persona, preferably through group
membership and current Unity Catalog grants. Record relevant row filters, column masks,
governed tags, attribute-based policies, and required AI Gateway controls.

Do not assume that the assessor's access represents a consumer. Genie Code cannot test
another persona's effective access itself: a negative-access check that was not
executed stays `unknown` and leaves the mandatory governance criterion `unknown` — it is
never a `user-declared` pass. When impersonation or a persona-specific test is
unavailable, ask an authorized representative to run the same question and label the
result `user-declared` or `unknown` as appropriate.

## Layer 5: Evaluation and improvement

Represent each test case with:

| Field | Purpose |
|---|---|
| Question | Natural wording the intended persona will use |
| Persona | Permission context being tested |
| Expected facts or answer | Ground truth needed to judge correctness |
| Authoritative source | Asset that should support the answer |
| Acceptance criteria | Required facts, tolerances, format, and prohibited leakage |
| Result and citations | Observed answer, pass/fail, and sources used |
| Owner | Person accountable for validation and follow-up |

Exercise critical metrics, synonyms, time logic, join paths, entity resolution, source
selection, and permission boundaries. In Genie One, inspect citations rather than judging
answer fluency alone. If a Genie Agent supplies domain context, use its monitoring and
benchmarks as supporting evidence, not as a substitute for the Ontology-level question
set.

## Useful inspection surfaces

Depending on available capabilities and permissions, evidence may come from:

- Unity Catalog and `INFORMATION_SCHEMA` metadata for tables, columns, constraints, and
  tags (`TABLES`, `VIEWS`, `COLUMNS`, `SCHEMATA`, `TABLE_CONSTRAINTS`, `TABLE_TAGS`,
  `COLUMN_TAGS`); route detail queries through `databricks-unity-catalog`
- Catalog Explorer definitions for Metric Views and other governed assets
- Discover for Domains, Pages, ownership, lifecycle, and certification signals
- Workspace search and object metadata for dashboards, queries, notebooks, and Agents
- Genie One answers and source citations
- Genie Agent Monitor and benchmark results for contributing Agents
- Query history, audit logs, lineage, and quality monitoring
  (`system.query.history`, `system.access.audit`, `system.access.table_lineage`)
- Organization policies and owner-reviewed business documentation

Use only surfaces available in the current environment. Do not claim a check was
automated when it was manually confirmed, or claim workspace-wide completeness from a
partial search. State the scope you actually searched for every "no conflict found"
conclusion.

