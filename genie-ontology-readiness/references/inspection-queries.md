# Inspection Queries

Bounded, read-only queries for the claims the readiness model needs. Bounded means:
aggregate or summary output, predicates scoped to the critical sources and a recent
window, and an explicit `LIMIT` on any preview. Replace `<...>` placeholders. Never
paste raw sensitive values into the card. Route anything beyond these templates to
`databricks-unity-catalog` or `databricks-metric-views`.

Identifiers other than column and tag names are stored lowercase in `INFORMATION_SCHEMA`.
Always filter on the catalog and schema; unfiltered `INFORMATION_SCHEMA` scans are slow
and out of scope.

## Layer 0: Physical data foundation

Grain uniqueness at the declared key:

```sql
SELECT count(*) AS rows_in_window,
       count(DISTINCT <key_col_1>, <key_col_2>) AS distinct_keys
FROM <catalog>.<schema>.<table>
WHERE <event_ts> >= current_date() - INTERVAL 90 DAYS;
```

Duplicate keys, only if the two counts differ:

```sql
SELECT <key_col_1>, <key_col_2>, count(*) AS n
FROM <catalog>.<schema>.<table>
WHERE <event_ts> >= current_date() - INTERVAL 90 DAYS
GROUP BY 1, 2
HAVING n > 1
LIMIT 20;
```

Freshness and recent volume:

```sql
SELECT max(<event_ts>) AS latest_event,
       count(*) AS rows_last_7_days
FROM <catalog>.<schema>.<table>
WHERE <event_ts> >= current_date() - INTERVAL 7 DAYS;
```

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
  AND event_time >= current_date() - INTERVAL 30 DAYS
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

## Layer 2: Business semantics

Metric View definition. The YAML appears in the extended output:

```sql
DESCRIBE TABLE EXTENDED <catalog>.<schema>.<metric_view>;
```

Metric View sanity check for a representative question:

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
scope in the card. Usage of a candidate source as an authority signal:

```sql
SELECT count(*) AS statements_last_30_days,
       count(DISTINCT executed_by) AS distinct_users
FROM system.query.history
WHERE start_time >= current_date() - INTERVAL 30 DAYS
  AND statement_text ILIKE '%<schema>.<table>%';
```

## Layer 3: Context-rich assets

Certification status for catalog objects. Absence of a row means uncertified:

```sql
SELECT table_name, tag_value AS certification_status
FROM <catalog>.information_schema.table_tags
WHERE schema_name = '<schema>'
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

Row filters and column masks in the scoped schema:

```sql
SELECT table_name, filter_name, target_columns
FROM <catalog>.information_schema.row_filters
WHERE schema_name = '<schema>';

SELECT table_name, column_name, mask_name, using_columns
FROM <catalog>.information_schema.column_masks
WHERE schema_name = '<schema>';
```

Group membership for a persona's representative user:

```sql
SHOW GROUPS WITH USER `<user@example.com>`;
```

These queries show what is granted, not what a persona experiences in Genie One. A
persona-specific answer test still requires that persona to run the question.

## Layer 5: Evaluation and improvement

Genie One from a CLI runtime. Requires CLI v1.9.0 or newer, and the output has no
citation field:

```bash
databricks genie ask -s <session> "<question>" --include-sql --output json
```

Citations: open the same question in the Genie One UI and click the citation icons on
the response. Record the cited sources in the card's representative-questions table.
