# Optimization Protocol

Use this protocol for a `/goal`-driven, multi-round Genie Agent optimization. The
append-only UC artifact ledger is authoritative; keep a smaller conversation checkpoint
current only so an automatic continuation can locate and validate that ledger.

## Contents

- Run checkpoint
- Canonical configuration identity
- Benchmark QC and evaluation
- Safe full-replacement mutation
- Round disposition
- Failure handling
- Final audit

## Run checkpoint

Maintain this cache in the conversation. Reconstruct and verify it from the approved UC
artifact table at the start of every resumed turn and before every mutation.

```text
{
  run_id,
  artifact_table,
  last_event_seq,
  space_id,
  evaluation_target,
  target_accuracy,
  max_rounds,
  benchmark_policy,
  enabled_levers,
  approved_benchmark_ids,
  human_authored_benchmark_ids,
  generated_benchmark_ids,
  excluded_benchmarks: [{id, reasons}],
  starting_config_hash,
  accepted_config_hash,
  accepted_config_event_id,
  accepted_eval,
  accuracy_by_round,
  changes_by_round,
  rollback_events,
  current_round,
  stop_reason
}
```

The complete accepted configuration lives in a verified `config_snapshot` artifact;
`accepted_config_event_id` points to it for rollback. Do not print the full configuration
in conversation updates. Do not put benchmark question text, gold SQL, expected results,
secrets, or raw sensitive data in the conversation checkpoint. IDs, hashes, summarized
evidence, and the exact configuration paths and values changed by the optimizer are
sufficient.

After each round, emit a concise checkpoint summary: prior and new score/count, fixed
and regressed IDs, candidate disposition, accepted hash, rounds remaining, and next
action.

Read [uc-artifacts.md](uc-artifacts.md) for the table schema, required artifact chain,
write verification, and resume rules. A live mutation is forbidden until the initial
artifact chain has been written and read back successfully.

## Canonical configuration identity

`update-space` replaces the complete serialized configuration. Always retain a parsed
copy of the accepted configuration and identify it with lowercase SHA-256 over the UTF-8
bytes produced by the equivalent of:

```python
json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
```

Do not hash the outer JSON string returned by an API; parse `serialized_space` first.
Use the same canonicalization before every comparison.

There are three important hashes in a candidate round:

- `accepted_hash`: the configuration evaluated and accepted before the round.
- `staged_hash`: the complete candidate configuration intended for the update.
- `observed_hash`: the configuration fetched after an update or rollback.

A hash mismatch is evidence, not an inconvenience. Never bypass it with a second blind
write.

## Benchmark QC and evaluation

### Freeze the corpus

Build the approved ID list only after benchmark QC. Preserve order for reporting but
compare result coverage as a set. Require nonempty unique IDs.

For `validate_only`, do not update benchmark definitions. Exclusion affects only the run
corpus and leaves the Agent unchanged. For a mutation-capable policy, stage benchmark
changes separately, preserve every non-benchmark field, apply the safe mutation protocol,
then restart the baseline from the newly accepted configuration.

When benchmark generation is authorized, add only coverage that is supported by
governed metadata and independently validated ground truth. Preserve provenance across
runs when durable history makes it available. Do not let generated items overwhelm a
weak human-authored corpus.

### Chat evaluation

Prefer the native benchmark API for Chat items. In a current CLI runtime the command
family is:

```bash
databricks genie genie-create-eval-run SPACE_ID \
  --json '{"benchmark_question_ids":["<id>"]}' --profile PROFILE
databricks genie genie-get-eval-run SPACE_ID EVAL_RUN_ID --profile PROFILE
databricks genie genie-list-eval-results SPACE_ID EVAL_RUN_ID --profile PROFILE
databricks genie genie-get-eval-result-details \
  SPACE_ID EVAL_RUN_ID RESULT_ID --profile PROFILE
```

Check current help rather than assuming Beta commands are unchanged. The request field
must be exactly `benchmark_question_ids`; an empty body or misspelled field can evaluate
all benchmarks. Poll to a successful terminal state and follow pagination.

Validate the run independently:

- reported question count equals the approved Chat ID count;
- each approved ID occurs exactly once and no other ID occurs;
- counts reconcile and accuracy is `num_correct / num_questions`;
- `GOOD`, `BAD`, and `NEEDS_REVIEW` remain distinct in the raw checkpoint even if the
  declared score treats only `GOOD` as passing.

### Agent evaluation

Native eval runs are Chat-only. For Agent or document questions, execute the frozen
questions through the Agent-mode Responses API using the original execution mode. Grade
each terminal answer against its independent `evaluation_note`. Retain the rubric result,
evidence summary, execution status, and citations or tool evidence needed by the rubric.

Use a consistent evaluator for baseline and every round. If grading cannot be made
deterministic enough to compare rounds, stop and report the limitation rather than
manufacturing an accuracy.

### Mixed evaluation

Evaluate Chat and Agent items separately. Report both scores and counts. Do not invent a
single mixed accuracy unless the goal defines a weighting; if it does, freeze that
weighting before baseline.

### Exact-state rule

The final evaluation must test the frozen corpus against the configuration left on the
Agent. If any mutation occurs after an evaluation, that evaluation cannot be final.

## Safe full-replacement mutation

Apply this sequence for benchmark repair, an optimization candidate, a revision, or a
rollback:

1. Start from the complete accepted parsed configuration.
2. Change only approved paths and validate the version-2 structure, unique IDs, and
   sorted ID-keyed arrays required by the API.
3. Compute `staged_hash`.
4. Immediately fetch the current complete configuration. Proceed only when its hash is
   `accepted_hash`.
5. Submit one full-replacement update.
6. Fetch the complete configuration again. Accept the write only when `observed_hash` is
   `staged_hash` and the intended paths match.
7. If update verification fails, restore the accepted configuration only when the
   current hash still equals `staged_hash`. Re-fetch and require `accepted_hash`.

If the current hash is neither the accepted nor staged hash, another writer may have
changed the Agent. Do not update or roll back. Record the conflict and stop.

For a partial rollback of an optimizer-owned bundle, also require every touched path to
still contain the optimizer's recorded after-value. This prevents a rollback from
overwriting a later edit even when the surrounding configuration was reconstructed
incorrectly.

## Round disposition

Compare the candidate evaluation with the preceding accepted evaluation by benchmark ID:

- `fixed`: non-passing to `GOOD`;
- `regressed`: `GOOD` to non-passing;
- `unchanged`: passing state unchanged;
- `excluded`: outside the valid frozen corpus and never part of score movement.

Keep one coherent bundle when it produces positive valid-item movement without an
unacceptable regression, or fixes the declared target cluster without reducing the
declared overall objective. A score tie is insufficient when the bundle only moves the
failure elsewhere or adds complexity without demonstrated value.

When a candidate is rejected:

1. Conditionally restore the preceding accepted configuration.
2. Verify its hash.
3. Run a complete evaluation of the restored state if the workflow will finish there.
4. Record both the candidate outcome and rollback outcome.

At most one focused revision of the same bundle should occur before moving to the next
round. A revision is a mutation and requires the same verification and evaluation.

## Failure handling

### Evaluation failure

An API error, timeout, non-success terminal status, pagination gap, duplicate result,
extra result, or count mismatch yields no candidate accuracy. If the candidate changed
the Agent, conditionally restore and verify the preceding accepted configuration. Stop
with `evaluation_failed`; do not spend later rounds on an unmeasured state.

### Persistence failure

The UC ledger is required for a live mutation loop. If a required write fails before an
Agent update, stop without updating. If it fails after a candidate update, conditionally
restore the preceding accepted snapshot and verify that rollback. If the final snapshot
or summary cannot be persisted and verified, conditionally restore all optimizer-owned
changes to the starting snapshot when safe, verify the rollback, and write a diagnostic
artifact when possible. Do not describe unaudited live changes as a successful run.

### Authorization boundary

Stop before a mutation outside the durable authorization. Name the proposed target,
change, evidence, expected effect, side effects, and rollback plan. Read-only discovery
may continue when it can materially improve that proposal.

### Upstream defect

Do not hide wrong Metric View logic, bad joins or grain in source data, stale pipelines,
or missing access behind Agent instructions. Record the affected benchmark IDs and the
owning upstream object, then continue only with other independent actionable clusters.

## Final audit

Return a compact report with this structure:

```markdown
# Genie Agent Optimization Audit

**Agent:** <title and immutable Space ID>
**Evaluation target:** <Chat | Agent | mixed>
**Outcome:** <stop reason>; target_met=<true|false>
**Configuration:** <starting hash> -> <final accepted hash>

## Benchmark gate
<Approved/excluded counts, policy, human/generated provenance, important limitations.>

## Accuracy
| Set | Baseline | Final | Correct / total |
|---|---:|---:|---:|
<Overall or separate Chat/Agent rows plus human/generated rows when applicable.>

## Rounds
| Round | Root cause | Lever and targets | Disposition | Fixed | Regressed |
|---:|---|---|---|---|---|

## Remaining failures
<Benchmark ID, assessment, root cause, and disposition. Do not reproduce gold SQL.>

## Rollbacks and conflicts
<Every attempted rollback and hash outcome; say None when empty.>

## Upstream blockers
<Out-of-scope owning objects and recommended next action; say None when empty.>
```

Verify immediately before this report that the live Agent hash equals the final accepted
hash. Name the final eval run or evaluation batch and assert that its result IDs exactly
match the frozen corpus. Read back the final summary and report its run ID and artifact
table. State limitations and a below-target result without softening them.
