# Inspection Queries

Bounded, read-only queries for the claims the readiness model needs. Bounded means:
aggregate or summary output, predicates scoped to the critical sources and a recent
window, and an explicit `LIMIT` on any preview. Replace `<...>` placeholders. Never
paste raw sensitive values into the card. Route anything beyond these templates to
`databricks-unity-catalog` or `databricks-metric-views`.

Identifiers other than column and tag names are stored lowercase in `INFORMATION_SCHEMA`.
Always filter on the catalog and schema; unfiltered `INFORMATION_SCHEMA` scans are slow
and out of scope. Results are privilege-filtered, so an absent row proves absence only
within the objects the assessor can see.

## Layer 0: Physical data foundation

Grain uniqueness at the declared key:

```sql
SELECT count(*) AS rows_in_window,
       count(DISTINCT struct(<key_col_1>, <key_col_2>)) AS distinct_keys,
       count_if(<key_col_1> IS NULL OR <key_col_2> IS NULL) AS null_keys
FROM <catalog>.<schema>.<table>
WHERE <event_ts> >= current_date() - INTERVAL 90 DAYS;
```

Duplicate-key summary, only if the two counts differ. Keep raw key values out of the
result because identifiers can be sensitive:

```sql
SELECT count(*) AS duplicate_key_groups,
       coalesce(sum(n - 1), 0) AS excess_rows
FROM (
  SELECT count(*) AS n
  FROM <catalog>.<schema>.<table>
  WHERE <event_ts> >= current_date() - INTERVAL 90 DAYS
  GROUP BY <key_col_1>, <key_col_2>
  HAVING count(*) > 1
) duplicates;
```

Freshness and recent volume:

```sql
SELECT max(<event_ts>) AS latest_event_in_lookback,
       count_if(<event_ts> >= current_date() - INTERVAL 7 DAYS) AS rows_last_7_days
FROM <catalog>.<schema>.<table>
WHERE <event_ts> >= current_date() - INTERVAL 90 DAYS;
```

Choose the lookback from the source's freshness SLA and use a partition column where
possible. A null `latest_event_in_lookback` proves only that the source has no events in
that bounded window. Align date boundaries to the documented source timezone and business
calendar rather than assuming the SQL session's `current_date()` matches them.

Null and cardinality summary for a critical field:

```sql
SELECT count(*) AS n,
       count_if(<col> IS NULL) AS nulls,
       count(DISTINCT <col>) AS distinct_values
FROM <catalog>.<schema>.<table>
WHERE <event_ts> >= current_date() - INTERVAL 90 DAYS;
```

Declared primary and foreign keys. These are informational in Unity Catalog, so confirm
them with the uniqueness query above:

```sql
SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
       kcu.column_name, rc.unique_constraint_name AS references_constraint
FROM <catalog>.information_schema.table_constraints tc
LEFT JOIN <catalog>.information_schema.key_column_usage kcu
  ON tc.constraint_catalog = kcu.constraint_catalog
 AND tc.constraint_schema = kcu.constraint_schema
 AND tc.constraint_name = kcu.constraint_name
LEFT JOIN <catalog>.information_schema.referential_constraints rc
  ON tc.constraint_catalog = rc.constraint_catalog
 AND tc.constraint_schema = rc.constraint_schema
 AND tc.constraint_name = rc.constraint_name
WHERE tc.table_schema = '<schema>'
  AND tc.table_name IN ('<table_1>', '<table_2>')
ORDER BY tc.table_name, tc.constraint_name;
```

Upstream sources of a critical table, from lineage:

```sql
SELECT DISTINCT source_table_full_name, source_type, entity_type
FROM system.access.table_lineage
WHERE target_table_full_name = '<catalog>.<schema>.<table>'
  AND event_date >= current_date() - INTERVAL 30 DAYS
LIMIT 50;
```

## Layer 1: Metadata

Table descriptions, owners, and last change:

```sql
SELECT table_name, table_type, comment, table_owner, created, last_altered
FROM <catalog>.information_schema.tables
WHERE table_schema = '<schema>'
  AND table_name IN ('<table_1>', '<table_2>');
```

Column comments for the fields critical questions use:

```sql
SELECT table_name, column_name, data_type, comment
FROM <catalog>.information_schema.columns
WHERE table_schema = '<schema>'
  AND table_name IN ('<table_1>', '<table_2>')
ORDER BY table_name, ordinal_position;
```

Tags on scoped tables and columns. Classification, domain, and certification all appear
here:

```sql
SELECT table_name, tag_name, tag_value
FROM <catalog>.information_schema.table_tags
WHERE schema_name = '<schema>'
  AND table_name IN ('<table_1>', '<table_2>');

SELECT table_name, column_name, tag_name, tag_value
FROM <catalog>.information_schema.column_tags
WHERE schema_name = '<schema>'
  AND table_name IN ('<table_1>', '<table_2>');
```

Domain and subdomain governed tags can be attached at catalog, schema, or table scope:

```sql
SELECT catalog_name, tag_name, tag_value
FROM <catalog>.information_schema.catalog_tags
WHERE catalog_name = '<catalog>'
  AND tag_name IN ('<domain_tag>', '<domain_tag>/<subdomain>');

SELECT catalog_name, schema_name, tag_name, tag_value
FROM <catalog>.information_schema.schema_tags
WHERE catalog_name = '<catalog>'
  AND schema_name = '<schema>'
  AND tag_name IN ('<domain_tag>', '<domain_tag>/<subdomain>');

SELECT catalog_name, schema_name, table_name, tag_name, tag_value
FROM <catalog>.information_schema.table_tags
WHERE catalog_name = '<catalog>'
  AND schema_name = '<schema>'
  AND table_name IN ('<table_1>', '<table_2>')
  AND tag_name IN ('<domain_tag>', '<domain_tag>/<subdomain>');
```

## Layer 2: Business semantics

Metric View definition. The YAML appears in the JSON result's `view_text` field:

```sql
DESCRIBE TABLE EXTENDED <catalog>.<schema>.<metric_view> AS JSON;
```

Metric View sanity check for a representative question. Choose a non-sensitive
dimension or aggregate the result further:

```sql
SELECT <dimension>, MEASURE(<measure>) AS <measure>
FROM <catalog>.<schema>.<metric_view>
WHERE <time_dimension> >= current_date() - INTERVAL 90 DAYS
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20;
```

Competing definitions live in dashboards, queries, notebooks, and Genie Agents. Use
workspace search for the metric name and its synonyms, and record the search terms and
scope in the card. Treat usage as a relevance signal, not proof of authority. Recent
reads of a candidate source can be summarized without inspecting potentially sensitive
query text:

```sql
SELECT count(*) AS lineage_events_last_30_days,
       count(DISTINCT statement_id) AS sql_statements_last_30_days,
       count(DISTINCT created_by) AS distinct_principals
FROM system.access.table_lineage
WHERE source_table_full_name = '<catalog>.<schema>.<table>'
  AND event_date >= current_date() - INTERVAL 30 DAYS;
```

## Layer 3: Context-rich assets

Certification status for catalog objects. Absence of a row means uncertified:

```sql
SELECT table_name, tag_value AS certification_status
FROM <catalog>.information_schema.table_tags
WHERE schema_name = '<schema>'
  AND table_name IN ('<table_1>', '<table_2>')
  AND tag_name = 'system.certification_status';
```

Dashboards, Genie Agents, and apps are not tag-searchable. Read the certified or
deprecated badge on the asset or on its Discover entry.

## Layer 4: Governance

Grants on the scoped objects:

```sql
SHOW GRANTS ON TABLE <catalog>.<schema>.<table>;

SELECT grantee, privilege_type, inherited_from
FROM <catalog>.information_schema.table_privileges
WHERE table_schema = '<schema>'
  AND table_name IN ('<table_1>', '<table_2>');
```

`TABLE_PRIVILEGES` is privilege-filtered and can omit other principals' grants for a
user who has `MANAGE`. Use `SHOW GRANTS` or Catalog Explorer when complete grant
visibility is required.

Table-level row filters and column masks in the scoped schema. The information-schema
column names differ across workspace rollout versions, so inspect them before choosing a
query:

```sql
DESCRIBE TABLE <catalog>.information_schema.row_filters;
DESCRIBE TABLE <catalog>.information_schema.column_masks;
```

Current documented schema:

```sql
SELECT table_name, filter_catalog, filter_schema, filter_name, filter_col_usage
FROM <catalog>.information_schema.row_filters
WHERE schema_name = '<schema>';

SELECT table_name, column_name, mask_catalog, mask_schema, mask_name, mask_col_usage
FROM <catalog>.information_schema.column_masks
WHERE schema_name = '<schema>';
```

Legacy schema still present in some workspaces:

```sql
SELECT table_name, filter_name, target_columns
FROM <catalog>.information_schema.row_filters
WHERE table_catalog = '<catalog>'
  AND table_schema = '<schema>';

SELECT table_name, column_name, mask_name, using_columns
FROM <catalog>.information_schema.column_masks
WHERE table_catalog = '<catalog>'
  AND table_schema = '<schema>';
```

Run only the form that matches the preceding `DESCRIBE`; do not treat a column-resolution
error as proof that no filter or mask exists.

ABAC policies attached at catalog, schema, or table scope. The information-schema view
is Public Preview and results require ownership, `MANAGE`, or `READ METADATA` on the
attachment point. If the view is unavailable, inspect policies with `SHOW POLICIES`,
`DESCRIBE POLICY`, or Catalog Explorer instead of concluding that none exist:

```sql
SELECT policy_name, policy_type, on_securable_type, securable_name,
       to_principals, except_principals, when_condition,
       match_columns, governed_tags
FROM <catalog>.information_schema.abac_policy_definitions
WHERE policy_type IN ('ROW_FILTER', 'COLUMN_MASK')
  AND catalog_name = '<catalog>'
  AND (schema_name = '<schema>' OR schema_name IS NULL);
```

Group membership for a persona's representative user:

```sql
SHOW GROUPS WITH USER `<user@example.com>`;
```

`SHOW GROUPS` requires administrator privileges. If it is unavailable, do not infer
membership from a job title or partial grant list; obtain an administrator-confirmed
membership record or keep the check `unknown`.

These queries show what is granted, not what a persona experiences in Genie One. A
persona-specific answer test still requires that persona to run the question.

## Layer 5: Evaluation and improvement

Genie One from a CLI runtime. Requires CLI v1.9.0 or newer. Use a distinct session label
for each independent test case. JSON includes SQL tool calls when SQL ran and can include
source links in the answer text, but has no structured citation field:

```bash
databricks genie ask -s <unique-test-session> "<question>" \
  --output json --profile <PROFILE>
```

Citations: review source links embedded in CLI answer text when present, source deep links
returned by the Genie One MCP, or the response's citation icons in the Genie One UI.
Record the cited sources in the card's representative-questions table. If CLI text omits
or truncates the sources, use MCP or UI to complete citation validation.
