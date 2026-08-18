# 1. Agent Testing & QA — Multi-Turn Conversation Evaluation

**MCP name:** `mcp-genie-agent-multiturn-eval`

Genie Code already supports evaluation through benchmarking, but only at the single-question
level. A gap exists around **multi-turn evaluation**: evaluating an entire conversation
end-to-end.

## Genie Conversation API findings

The [Genie Conversation API](https://docs.databricks.com/aws/en/genie-agents/conversation-api)
captures all the primitives needed to group messages into multi-turn conversations:

| Endpoint | Purpose |
|---|---|
| `GET /api/2.0/genie/spaces/{space_id}/conversations` | List all conversation threads in a Genie Agent |
| `GET /api/2.0/genie/spaces/{space_id}/conversations/{conversation_id}/messages` | List all messages in one conversation |
| `GET .../conversations/{conversation_id}/messages/{message_id}` | Get a single message (status, SQL, query result) |
| `POST .../start-conversation` | Start a new conversation |
| `POST .../conversations/{conversation_id}/messages` | Send a follow-up message |
| `DELETE .../conversations/{conversation_id}` | Delete a conversation |

**Each message object contains:**

| Field | Notes |
|---|---|
| `id` | Unique message ID |
| `conversation_id` | **Groups messages into multi-turn threads** |
| `space_id` | Which Genie Agent |
| `user_id` | **Who sent the message** |
| `content` | The user's question |
| `status` | `IN_PROGRESS` / `COMPLETED` / etc. |
| `attachments` | Contains query results, SQL, visualizations when present |
| `query_result` | Populated when generation completes |
| `error` | Error info if generation failed |
| `created_timestamp` | Unix epoch |
| `last_updated_timestamp` | Unix epoch |

The conversation object itself also has `id`, `title`, `space_id`, and `user_id`.

## Design

An MCP that clones a Genie Agent, replays curated multi-turn conversation scenarios against
the clone, and runs MLflow multi-turn evaluation with LLM-as-judge scoring. Genie Code
orchestrates the top-level workflow; the MCP owns the Genie API simulation and MLflow eval.

### Architecture decisions

1. **Clone-before-eval:** The MCP clones the target Genie Agent via the management API
   before running evaluation. Eval runs against the clone in isolation — real users are
   never exposed to the change under test. The clone is deleted after eval completes (or
   kept for inspection on failure).

2. **MLflow 3.10 multi-turn eval:** The MCP wraps the Genie Conversation API as an MLflow
   `predict_fn` and drives it through the
   [`mlflow.genai.evaluate`](https://mlflow.org/blog/multiturn-evaluation/) pipeline with
   built-in multi-turn scorers and custom judges.

3. **Scenario storage:** Multi-turn test cases live as workspace JSON files (one file per
   Agent or per scenario suite), making them human-editable, version-controllable, and
   DABs-compatible.

4. **LLM-as-judge via MLflow:** The MCP configures MLflow's `make_judge`, `ConversationalGuidelines`,
   and built-in scorers (`ConversationCompleteness`, `UserFrustration`) — all pointing at a
   Databricks Model Serving endpoint or external model. MLflow runs the judges, not the MCP.

5. **Cost is expected:** Each eval run creates real conversations against the cloned Agent,
   which means real warehouse queries. The MCP reports warehouse usage per run.

### Scenario schema (workspace JSON file)

```jsonc
{
  "space_id": "3c409c00b54a44c79f79da06b82460e2",
  "scenarios": [
    {
      "name": "sales_follow_up",
      "goal": "Get top sales for last month, then drill into a specific region",
      "persona": "A business analyst preparing for a quarterly review",
      "turns": [
        {
          "content": "Give me top sales by region for last month",
          "expectations": {
            "expected_response_type": "table",
            "expected_columns": ["region", "total_sales"],
            "expected_row_count_range": [3, 10]
          }
        },
        {
          "content": "Now drill into the highest-performing region and break it down by product category",
          "expectations": {
            "expected_response_type": "table",
            "expected_columns": ["product_category", "total_sales"],
            "references_previous_turn": true
          }
        },
        {
          "content": "What was the top-selling product in that breakdown?",
          "expectations": {
            "expected_response_type": "text",
            "references_previous_turn": true
          }
        }
      ],
      "simulation_guidelines": [
        "Accept the agent's answer at face value; don't challenge data accuracy",
        "Ask natural follow-ups that drill deeper into the data"
      ],
      "conversation_scorers": {
        "ConversationCompleteness": {},
        "UserFrustration": {},
        "genie_sql_validity": {
          "instructions": "Review the {{ conversation }}. Each agent response that includes SQL should have valid, runnable SQL that matches the user's question. Score 'pass' if all SQL is valid and relevant, 'fail' otherwise."
        },
        "genie_context_retention": {
          "instructions": "Review the {{ conversation }}. The agent should retain context from earlier turns (e.g. filters, regions, time periods mentioned) without the user having to repeat them. Score 'pass' if context is correctly retained across all turns, 'partial' if some context is dropped, 'fail' if the agent treats each turn as independent."
        }
      }
    }
  ]
}
```

### MCP tools

| Tool | Purpose |
|---|---|
| `list_eval_scenarios(space_id)` | List available scenario files for an Agent from the workspace |
| `run_multi_turn_eval(space_id, scenario_names?, baseline_run_id?)` | Clone the Agent, replay scenarios, run MLflow eval, return run IDs |
| `get_eval_results(run_id)` | Return the MLflow eval scorecard (per-turn + conversation-level) |
| `compare_eval_runs(run_id_a, run_id_b)` | Compare two eval runs and return the delta |
| `cleanup_clone(space_id)` | Delete the cloned Agent after eval |

### End-to-end flow

```
1. CURATE (human, one-time)
   Create a workspace JSON file with multi-turn scenarios and scoring criteria.

2. PRE-EDIT BASELINE (Genie Code + MCP)
   Genie Code calls save_agent_config_version()        ← versioning MCP (existing)
   Genie Code calls run_multi_turn_eval()              ← this MCP
     ├─ MCP clones the Agent (POST /api/2.0/genie/spaces with serialized_space)
     ├─ MCP wraps the clone as an MLflow predict_fn
     ├─ MLflow ConversationSimulator replays each scenario against the clone
     ├─ MLflow runs built-in + custom multi-turn scorers
     └─ MCP returns baseline_run_id, deletes clone
   Result: baseline scorecard stored in MLflow

3. EDIT (Genie Code)
   Genie Code edits the live Agent with native tools.

4. POST-EDIT EVAL (Genie Code + MCP)
   Genie Code calls run_multi_turn_eval(baseline_run_id=baseline_run_id)  ← this MCP
     ├─ MCP clones the updated Agent
     ├─ Same scenarios, same scorers, different Agent config
     └─ MCP returns new_run_id, deletes clone

5. COMPARE (Genie Code)
   Genie Code calls compare_eval_runs(baseline_run_id, new_run_id)
   → structured delta: which scenarios improved, which regressed, by how much

6. DECIDE
   If regressions → call restore_agent_config_version()  ← versioning MCP
   If improvements → keep the edit
```

### MLflow integration points

| MLflow 3.10 API | How the MCP uses it |
|---|---|
| `ConversationSimulator(test_cases, max_turns)` | Drives each scenario's turns against the cloned Genie Agent via the Genie Conversation API |
| `predict_fn` | The MCP provides a function that calls `POST start-conversation` → `POST messages` → polls for `COMPLETED` → returns the response |
| `ConversationCompleteness` | Built-in scorer: did the conversation reach a natural conclusion? |
| `UserFrustration` | Built-in scorer: did the user appear frustrated during the conversation? |
| `ConversationalGuidelines` | Custom assertions e.g. "Agent never asks the user to write SQL" |
| `make_judge({{ conversation }})` | Custom Genie-specific judges: SQL validity, context retention, answer groundedness in the data |
| `mlflow.genai.evaluate()` | Orchestrates the simulation + scoring pipeline |
| `mlflow.search_sessions()` | Retrieves past eval traces for comparison |
| `generate_test_cases(sessions)` | Auto-generate scenarios from real Genie conversations (stretch goal) |

### Resolved design decisions

- **Clone API:** `GET /api/2.0/genie/spaces/{space_id}?include_serialized_space=true` to
  read the live config, then `POST /api/2.0/genie/spaces` with the `serialized_space` to
  create the clone. Same pattern DABs uses.
- **Judge model endpoint:** Configurable via `app.yaml` env var (e.g. `JUDGE_MODEL_ENDPOINT`).
  Set to a Databricks Model Serving endpoint or external model URI.
- **Warehouse for eval clone:** Same warehouse as the original Agent. No separate warehouse
  needed — the clone is a short-lived copy so warehouse usage is attributable and expected.
- **Clone lifecycle:** Delete the clone immediately after eval completes (success or
  failure). The MCP's `run_multi_turn_eval` tool handles create → eval → delete atomically.
  A separate `cleanup_clone` tool is available if Genie Code needs to abort mid-eval.
