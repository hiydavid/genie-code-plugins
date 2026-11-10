# Unity Catalog Artifact Ledger

Use one append-only Delta table as the durable state machine for a `/goal` optimization
run. This deliberately mirrors the reference workflow's artifact table and the built-in
Genie optimization guidance's single-event-table option. It is simpler to resume and
audit than coordinating four analytical tables; downstream reporting can flatten the
JSON later.

## Authorization and governance

Require a user-approved catalog, schema, and table before live Agent mutation. Creating
the table requires `USE CATALOG`, `USE SCHEMA`, and `CREATE TABLE`; using an existing
table requires `USE CATALOG`, `USE SCHEMA`, `SELECT`, and `MODIFY`. Do not grant
privileges, create a catalog or schema, change ownership, or weaken controls as part of
this workflow.

Snapshots contain the full Agent configuration, including instructions, source names,
benchmark questions, and gold SQL. Treat the table as sensitive operational metadata.
Use an appropriately restricted schema and the organization's retention policy. Never
store credentials, tokens, raw query results, or secrets in artifacts.

## Table

Use a user-selected three-part name; the conventional suffix is
`genie_agent_optimization_artifacts`.

```sql
CREATE TABLE IF NOT EXISTS <catalog>.<schema>.genie_agent_optimization_artifacts (
  run_id        STRING NOT NULL,
  event_seq     BIGINT NOT NULL,
  event_id      STRING NOT NULL,
  artifact_type STRING NOT NULL,
  space_id      STRING NOT NULL,
  round_number  INT,
  config_hash   STRING,
  payload_json  STRING NOT NULL,
  created_at    TIMESTAMP NOT NULL,
  created_by    STRING
) USING DELTA
COMMENT 'Append-only state and audit artifacts for bounded Genie Agent optimization';
```

Do not assume `CREATE TABLE IF NOT EXISTS` proves an existing table has this schema.
Describe it and validate every required column and type before writing.

## Write contract

Artifacts are immutable. Allocate a monotonically increasing `event_seq` within a run
and a unique `event_id`. Never update or delete an earlier event to change history; append
a correction, decision, rollback, or final summary event.

Use parameter binding, a DataFrame append, or an equivalent structured write for every
value. Never interpolate `run_id`, JSON, or other values into SQL literals. Three-part
identifiers cannot be value-bound: validate the three nonempty name segments, escape
backticks in each, and quote each segment separately.

After every append, read the row back by `run_id` and `event_id` and require exact
metadata plus parseable `payload_json`. Before a mutation, also require that event
sequences for the run are unique and that the cached `last_event_seq` is still latest.
If a write outcome is ambiguous, read by `event_id`; do not blindly append a duplicate.

## Required artifact chain

Use these artifact types in order. Additional diagnostic events are allowed, but they do
not replace required events.

| Artifact | When | Required payload |
|---|---|---|
| `run_manifest` | First | Goal contract, run/Space IDs, evaluation target, limits, policies, enabled levers, initiator |
| `space_config_snapshot` | Before benchmark QC | Full parsed starting `serialized_space`, canonical hash |
| `benchmark_qc` | After QC | Approved/excluded/generated IDs, provenance, reasons, policy, base/final hashes |
| `baseline_run` | After exact-set baseline | Eval IDs, counts, accuracy, per-question outcomes, benchmark-set hash |
| `round_plan` | Before each candidate update | Root cause, evidence summary, selected lever, targeted IDs, changed paths, leakage check |
| `config_snapshot` | After each candidate or rollback | Full parsed configuration, parent snapshot event, canonical hash, label |
| `candidate_eval` | After each candidate evaluation | Exact result IDs, counts, per-question movement, evaluation identifier |
| `round_decision` | After evaluation | Keep/revise/rollback decision, accepted snapshot/eval IDs, rationale |
| `rollback_event` | After any rollback attempt | Expected/current/restored hashes, paths, outcome, conflict details |
| `optimization_result` | When loop stops | Baseline/final accuracy, rounds, changes, failures, stop reason, hash chain |
| `space_config_post_opt` | Immediately before audit | Full live final configuration and canonical hash |
| `run_summary` | Last | Audit status, target status, required events, final snapshot/eval IDs, errors |

Use `config_hash` only for events tied to one configuration. Put all other structured
content in `payload_json`. Do not reproduce gold SQL in tuning-analysis events; it is
present only inside authorized full snapshots and benchmark-QC evidence when necessary.

## Hash and handoff rules

The artifact chain must prove:

1. `space_config_snapshot.config_hash` equals the configuration observed before QC.
2. `benchmark_qc.final_hash` equals the configuration used for the baseline.
3. Each `round_plan` starts from the preceding accepted snapshot hash.
4. Each `candidate_eval` names the exact `config_snapshot` it evaluated.
5. Each `round_decision` names the snapshot and evaluation accepted for the next round.
6. `optimization_result.final_hash`, `space_config_post_opt.config_hash`, the live Agent
   hash, and the configuration evaluated by the final evaluation all match.

A missing link makes the audit incomplete. Never infer final accuracy from the baseline
or accept a summary whose final evaluation cannot be tied to the final snapshot.

## Resume

Resume only from an explicit `run_id`; never choose a run merely because it targets the
same Space. Load all events ordered by `event_seq`, reject duplicate sequences or event
IDs, parse every required payload, and reconstruct the last accepted snapshot and
evaluation from `round_decision` events.

Before continuing, fetch the live Agent and require its canonical hash to equal the last
accepted snapshot hash. If it differs, append a `run_summary` with an incomplete audit
when safe to do so, report a concurrent edit, and stop without overwriting it.

A run with a valid terminal `run_summary` is closed. Start a new run ID for more rounds;
link it to the prior run in the new manifest rather than reopening history.

## Final audit behavior

Write `run_summary` even when an upstream phase fails, when the ledger remains writable.
Use `audit_complete = false`, `target_met = null`, and explicit errors when required
artifacts, exact benchmark coverage, hash continuity, or the final snapshot are invalid.
A completed bounded loop below target can use `audit_complete = true` and
`target_met = false`.
