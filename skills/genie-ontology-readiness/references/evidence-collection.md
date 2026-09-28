# Evidence Collection

Collect enough evidence to judge the declared scope without turning the assessment into
an estate-wide catalog project. Prefer current, authoritative artifacts over prose claims.

## Runtime and routing

Detect the runtime before planning evidence collection:

- **Genie Code Agent mode.** You act with the invoking user's Unity Catalog permissions
  through Genie Code's tools: running SQL, reading Unity Catalog metadata, reading
  notebooks and workspace files, and any managed MCP servers the user added. A terminal
  and the databricks CLI are not guaranteed, and the managed MCP catalog offers Genie
  Agents but not Genie One. If no shell or CLI tool is available, the user runs Genie One
  questions in the browser and pastes the responses. Do not load `databricks-core` here;
  its profile-selection flow applies only to CLI runtimes.
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
| Genie One question validation from the CLI | `databricks-data-discovery` (`databricks genie ask`) |
| Genie Agent configuration, benchmarks, eval runs, monitoring | `databricks-genie-agents` |
| Metric View definitions, generated SQL | `databricks-metric-views` |
| Grants, tags, classification, row filters, column masks, system tables | `databricks-unity-catalog` |
| Bounded read-only SQL for grain, freshness, keys, tags, and access | [inspection-queries.md](inspection-queries.md) |

A skill that is not installed cannot be routed to; fall back to the workspace UI and say
so in the card.

Keep the assessment read-only in every runtime. Genie Code's approval mode may be
Auto-approve, which lets a classifier approve tool calls without a prompt; that does not
change what you are allowed to run during an assessment.

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

## Layer 2: Business semantics

Inspect:

- Primary keys, foreign keys, and the data evidence supporting them
- Metric View sources, joins, measures, dimensions, filters, formats, synonyms, and
  example queries
- Competing definitions for the critical concepts, in the dashboards, queries, views,
  and Genie Agents surfaced by a workspace search scoped to those concepts. Report
  "no conflict found within the searched scope"; never report search absence as proof
  that one governed definition exists
- Domain or subdomain membership and ownership. Domains are built on governed tags: a
  domain maps to a governed tag of the same name and a subdomain to
  `<domain>/<subdomain>`, so membership for catalog objects is visible in the
  `TABLE_TAGS`, `SCHEMA_TAGS`, and `CATALOG_TAGS` views, and for dashboards, Genie
  Agents, and Metric Views on the domain page in Discover. Domains and the Discover page
  are a Public Preview gated by the account setting "Domains and Discover Page" and the
  workspace setting "Discover Page"; if they are off, mark the Domain criterion not
  applicable with that reason
- Page state, owner review, term definitions, Synonyms, Sources, and Related assets

Draft Pages are available only in the Page owner's own Genie One conversations.
Published Pages are available in every Genie One conversation and are cited in answers.
Only the Page owner or a curator with `MANAGE DISCOVERY` on the domain can publish.
Record whether a Page is draft or published and whether its intended audience can
therefore retrieve it. Record preview or permission limitations separately from content
gaps.

## Layer 3: Context-rich assets

Inventory only assets relevant to the scoped workflow: commonly used dashboards and
queries, notebooks, documentation, and Genie Agents. For each authoritative candidate,
inspect freshness, use, description quality, owner, certification, and conflicting stale
alternatives. Absence of a large asset corpus is evidence of limited inferred context,
not automatic evidence that the modeled head is wrong.

Certification and deprecation are the governed tag `system.certification_status` with
the values `certified` and `deprecated`. For catalog objects, read it from `TABLE_TAGS`
or the other tag views. For dashboards, Genie Agents, and apps, which search cannot
filter by tag, read the badge on the asset or its Discover entry. Absence of the tag
means uncertified, not deprecated.

## Layer 4: Governance

Inspect effective access for each materially different persona, preferably through group
membership and current Unity Catalog grants. Record relevant row filters, column masks,
governed tags, attribute-based policies, and any Unity AI Gateway controls that apply to
custom agents or endpoints in scope.

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
| Answer path | Whether Genie One answered from a matching Genie Agent or from data-asset search |
| Result and citations | Observed answer, executed SQL, pass/fail, and the sources cited in the Genie One UI |
| Evidence state | `verified`, `user-declared`, or `unknown` for this result |
| Owner | Person accountable for validation and follow-up |

Genie One searches available Genie Agents first and answers from a matching Agent before
it searches data assets, and it prioritizes human-modeled context in Pages over inferred
context. Record the path for every question: a pass that depends on an Agent is evidence
about that Agent, not about the Ontology's modeled head, and belongs in Layer 3.

Capture results this way:

- CLI: `databricks genie ask --include-sql --output json` returns status, answer text,
  and the executed SQL. It carries no citations. Use it for answer correctness and SQL
  review.
- Genie One UI: click the citation icons on the response to see the knowledge sources
  used. This is the only surface for citation review. A response pasted verbatim with
  its sources is `verified`; a description of it is `user-declared`.
- Genie One memories and the assessor's own conversation history can shape answers. Run
  validation questions in a fresh conversation.

Exercise critical metrics, synonyms, time logic, join paths, entity resolution, source
selection, and permission boundaries. Inspect citations rather than judging answer
fluency alone. If a Genie Agent supplies domain context, use its monitoring and
benchmarks as supporting evidence, not as a substitute for the Ontology-level question
set.

## Useful inspection surfaces

Depending on available capabilities and permissions, evidence may come from:

- Unity Catalog and `INFORMATION_SCHEMA` metadata for tables, columns, constraints,
  tags, and fine-grained controls (`TABLES`, `VIEWS`, `COLUMNS`, `SCHEMATA`,
  `TABLE_CONSTRAINTS`, `KEY_COLUMN_USAGE`, `REFERENTIAL_CONSTRAINTS`, `TABLE_TAGS`,
  `COLUMN_TAGS`, `SCHEMA_TAGS`, `ROW_FILTERS`, `COLUMN_MASKS`, `TABLE_PRIVILEGES`);
  templates in [inspection-queries.md](inspection-queries.md), deeper detail through
  `databricks-unity-catalog`
- Catalog Explorer definitions for Metric Views and other governed assets
- Discover for Domains, Pages, ownership, lifecycle, and certification badges
- Workspace search and object metadata for dashboards, queries, notebooks, and Agents
- Genie One answers and, in the UI only, their source citations
- Genie Agent Monitor and benchmark results for contributing Agents
- Query history, audit logs, lineage, and quality monitoring
  (`system.query.history`, `system.access.audit`, `system.access.table_lineage`)
- Organization policies and owner-reviewed business documentation

Use only surfaces available in the current environment. Do not claim a check was
automated when it was manually confirmed, or claim workspace-wide completeness from a
partial search. State the scope you actually searched for every "no conflict found"
conclusion, and copy it into the card's "Evidence scope searched" section.
