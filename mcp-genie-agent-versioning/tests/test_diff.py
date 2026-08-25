"""Structural diff over realistic v2 and legacy serialized_space fixtures."""

from __future__ import annotations

import json
from collections.abc import Iterator, Mapping
from typing import Any

import pytest

from server.diff import MAX_IDENTIFIER_LIST, diff_agent_configs, empty_diff_sections

# Content that must never leak into a diff response (25k-char-class payloads).
LONG_INSTRUCTION = "instruction-" * 200
LONG_SQL = "SELECT secret FROM catalog.schema.orders WHERE " + "predicate AND " * 100
LONG_DESCRIPTION = "description-" * 200


def table(identifier: str, columns: tuple[str, ...] = (), description: str = "table") -> dict:
    return {
        "identifier": identifier,
        "description": description,
        "column_configs": [{"column_name": name, "type": "string"} for name in columns],
    }


def question(question_id: str, text: str = "question") -> dict:
    return {"id": question_id, "question": text}


def sql_function(function_id: str, identifier: str, description: str = "fn") -> dict:
    return {"id": function_id, "identifier": identifier, "description": description}


def space(
    *,
    version: int = 2,
    tables: tuple | list = (),
    metric_views: tuple | list = (),
    sample_questions: tuple | list = (),
    instructions: dict | None = None,
    benchmarks: tuple | list = (),
    extra: dict | None = None,
) -> dict[str, Any]:
    space_dict: dict[str, Any] = {
        "version": version,
        "data_sources": {"tables": list(tables), "metric_views": list(metric_views)},
        "instructions": {
            "text_instructions": [],
            "example_question_sqls": [],
            "sql_functions": [],
            "join_specs": [],
            "sql_snippets": {"filters": [], "expressions": [], "measures": []},
        },
        "benchmarks": {"questions": list(benchmarks)},
    }
    if sample_questions:
        space_dict["config"] = {"sample_questions": list(sample_questions)}
    if instructions:
        space_dict["instructions"].update(instructions)
    if extra:
        space_dict.update(extra)
    return space_dict


def envelope(serialized: dict[str, Any], **overrides: Any) -> dict[str, Any]:
    config = {
        "serialized_space": json.dumps(serialized),
        "title": "Revenue analyst",
        "description": "Answers revenue questions",
        "warehouse_id": "warehouse-1",
        "parent_path": "/Shared/Genie",
    }
    config.update(overrides)
    return config


def _strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from _strings(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _strings(item)


def test_full_v2_diff_reports_every_section():
    space_a = {
        "version": 2,
        "data_sources": {
            "tables": [
                table("cat.schema.orders", ("order_id", "status"), "Orders facts"),
                table("cat.schema.old_table", ("id",)),
            ],
            "metric_views": [table("cat.schema.mv_revenue", ("month",))],
        },
        "config": {"sample_questions": [question("q1"), question("q2", "kept")]},
        "instructions": {
            "text_instructions": [{"id": "t1", "content": LONG_INSTRUCTION}],
            "example_question_sqls": [
                {"id": "e1", "sql": LONG_SQL},
                {"id": "e2", "sql": "SELECT 1"},
                {"id": "e3", "sql": "SELECT 2", "title": "kept"},
            ],
            "sql_functions": [
                sql_function("f1", "cat.schema.fn_old"),
                sql_function("f2", "cat.schema.kept_fn"),
                sql_function("f3", "cat.schema.removed_fn"),
            ],
            "join_specs": [{"id": "j1", "sql": "a JOIN b"}],
            "sql_snippets": {
                "filters": [{"id": "s1", "sql": "region = 'EMEA'"}],
                "expressions": [{"id": "s2", "sql": "SUM(x)"}],
                "measures": [],
            },
        },
        "benchmarks": {"questions": [{"id": "b1", "answer": [{"content": LONG_SQL}]}]},
    }
    space_b = {
        "version": 3,
        "data_sources": {
            "tables": [
                {
                    "identifier": "cat.schema.orders",
                    "description": "Orders facts v2",
                    "column_configs": [
                        {"column_name": "order_id", "type": "string"},
                        {"column_name": "region", "type": "string"},
                        {"column_name": "status", "type": "int"},
                    ],
                },
                table("cat.schema.new_table", ("id",)),
            ],
            "metric_views": [table("cat.schema.mv_revenue", ("month",), "changed")],
        },
        "config": {"sample_questions": [question("q2", "kept"), question("q3")]},
        "instructions": {
            "text_instructions": [{"id": "t1", "content": "rewritten"}],
            "example_question_sqls": [
                {"id": "e1", "sql": LONG_SQL},
                {"id": "e3", "sql": "SELECT 2", "title": "kept"},
                {"id": "e4", "sql": "SELECT 3"},
            ],
            "sql_functions": [
                sql_function("f1", "cat.schema.fn_new"),
                sql_function("f2", "cat.schema.kept_fn", "updated"),
                sql_function("f4", "cat.schema.added_fn"),
            ],
            "join_specs": [],
            "sql_snippets": {
                "filters": [{"id": "s1", "sql": "region = 'APAC'"}],
                "expressions": [{"id": "s2", "sql": "SUM(x)"}],
                "measures": [{"id": "s3", "sql": "COUNT(*)"}],
            },
        },
        "benchmarks": {"questions": [{"id": "b1", "answer": [{"content": "changed"}]}]},
    }

    result = diff_agent_configs(envelope(space_a), envelope(space_b))

    changes = result["serialized_space_changes"]
    assert changes["version"] == {"changed": True, "a": 2, "b": 3}
    assert changes["sample_questions"] == {"added": 1, "removed": 1, "modified": 0}
    assert changes["tables"] == {
        "added": ["cat.schema.new_table"],
        "removed": ["cat.schema.old_table"],
        "modified": [
            {
                "identifier": "cat.schema.orders",
                "description_changed": True,
                "columns_added": ["region"],
                "columns_removed": [],
                "columns_modified": ["status"],
            }
        ],
    }
    assert changes["metric_views"] == {
        "added": [],
        "removed": [],
        "modified": [
            {
                "identifier": "cat.schema.mv_revenue",
                "description_changed": True,
                "columns_added": [],
                "columns_removed": [],
                "columns_modified": [],
            }
        ],
    }
    instructions = changes["instructions"]
    assert instructions["text_instructions"] == {"modified": True}
    assert instructions["example_question_sqls"] == {"added": 1, "removed": 1, "modified": 0}
    assert instructions["sql_functions"] == {
        "added": ["cat.schema.added_fn"],
        "removed": ["cat.schema.removed_fn"],
        "modified": 1,
        "renamed": [{"from": "cat.schema.fn_old", "to": "cat.schema.fn_new"}],
    }
    assert instructions["join_specs"] == {"added": 0, "removed": 1, "modified": 0}
    assert instructions["sql_snippets"] == {
        "filters": {"added": 0, "removed": 0, "modified": 1},
        "expressions": {"added": 0, "removed": 0, "modified": 0},
        "measures": {"added": 1, "removed": 0, "modified": 0},
    }
    assert changes["benchmarks"] == {"questions": {"added": 0, "removed": 0, "modified": 1}}
    assert changes["unknown_fields_changed"] == []
    assert result["envelope_changes"]["description"] == {"changed": False}


def test_legacy_config_only_payload_treats_missing_collections_as_empty():
    legacy = {
        "version": 2,
        "config": {"sample_questions": [question("q1"), question("q2")]},
        "data_sources": {"tables": [table("cat.schema.t1")], "metric_views": []},
    }

    result = diff_agent_configs(envelope(legacy), envelope(space()))

    changes = result["serialized_space_changes"]
    assert changes["sample_questions"] == {"added": 0, "removed": 2, "modified": 0}
    assert changes["tables"] == {
        "added": [],
        "removed": ["cat.schema.t1"],
        "modified": [],
    }
    instructions = changes["instructions"]
    assert instructions["text_instructions"] == {"modified": False}
    assert instructions["sql_functions"] == {
        "added": [],
        "removed": [],
        "modified": 0,
        "renamed": [],
    }
    assert changes["unknown_fields_changed"] == []


def test_sql_function_rename_is_reported_not_add_plus_remove():
    space_a = space(instructions={"sql_functions": [sql_function("f1", "cat.schema.old_fn")]})
    space_b = space(instructions={"sql_functions": [sql_function("f1", "cat.schema.new_fn")]})

    result = diff_agent_configs(envelope(space_a), envelope(space_b))

    assert result["serialized_space_changes"]["instructions"]["sql_functions"] == {
        "added": [],
        "removed": [],
        "modified": 0,
        "renamed": [{"from": "cat.schema.old_fn", "to": "cat.schema.new_fn"}],
    }


def test_unknown_top_level_fields_reported_by_name_only():
    space_a = space(extra={"future_field": {"payload": LONG_INSTRUCTION}})

    changed = diff_agent_configs(
        envelope(space_a), envelope(space(extra={"future_field": "changed"}))
    )
    removed = diff_agent_configs(envelope(space_a), envelope(space()))
    unchanged = diff_agent_configs(envelope(space_a), envelope(space_a))

    assert changed["serialized_space_changes"]["unknown_fields_changed"] == ["future_field"]
    assert removed["serialized_space_changes"]["unknown_fields_changed"] == ["future_field"]
    assert unchanged["serialized_space_changes"]["unknown_fields_changed"] == []


def test_identifier_lists_truncate_with_exact_totals():
    space_a = space()
    space_b = space(tables=[table(f"cat.schema.t{i:03d}") for i in range(MAX_IDENTIFIER_LIST + 10)])

    result = diff_agent_configs(envelope(space_a), envelope(space_b))

    tables = result["serialized_space_changes"]["tables"]
    assert len(tables["added"]) == MAX_IDENTIFIER_LIST
    assert tables["added_truncated"] is True
    assert tables["added_total"] == MAX_IDENTIFIER_LIST + 10
    assert tables["removed"] == []
    assert tables["modified"] == []


def test_diff_never_returns_payload_content():
    config_a = envelope(
        space(
            tables=[table("cat.schema.orders", ("status",), LONG_DESCRIPTION)],
            instructions={
                "text_instructions": [{"id": "t1", "content": LONG_INSTRUCTION}],
                "sql_snippets": {"filters": [{"id": "f1", "sql": LONG_SQL}]},
            },
        ),
        description=LONG_DESCRIPTION,
    )
    config_b = envelope(
        space(
            tables=[table("cat.schema.orders", ("status",), LONG_DESCRIPTION + "2")],
            instructions={
                "text_instructions": [{"id": "t1", "content": "rewritten"}],
                "sql_snippets": {"filters": [{"id": "f1", "sql": LONG_SQL + "2"}]},
            },
        ),
        description=LONG_DESCRIPTION + "2",
    )

    result = diff_agent_configs(config_a, config_b)

    assert all(len(text) <= 200 for text in _strings(result))
    dumped = json.dumps(result)
    assert LONG_DESCRIPTION not in dumped
    assert LONG_INSTRUCTION not in dumped
    assert LONG_SQL not in dumped
    assert result["serialized_space_changes"]["tables"]["modified"][0]["description_changed"]
    assert result["serialized_space_changes"]["instructions"]["text_instructions"] == {
        "modified": True
    }
    assert result["serialized_space_changes"]["instructions"]["sql_snippets"]["filters"] == {
        "added": 0,
        "removed": 0,
        "modified": 1,
    }


def test_identical_configs_produce_no_changes():
    config = envelope(space(tables=[table("cat.schema.t")]))

    result = diff_agent_configs(config, config)

    assert result["envelope_changes"]["title"] == {
        "changed": False,
        "a": "Revenue analyst",
        "b": "Revenue analyst",
    }
    assert result["serialized_space_changes"]["tables"] == {
        "added": [],
        "removed": [],
        "modified": [],
    }
    assert result["serialized_space_changes"]["unknown_fields_changed"] == []


def test_empty_sections_match_the_real_diff_shape():
    real = diff_agent_configs(envelope({}), envelope({}))
    empty = empty_diff_sections()

    # Envelope scalars legitimately carry values in a real diff; every collection key,
    # zeroed, must match the shortcut shape exactly.
    assert real["serialized_space_changes"] == empty["serialized_space_changes"]
    assert set(empty["envelope_changes"]) == {"title", "description", "warehouse_id", "parent_path"}


def test_argument_order_swaps_added_and_removed():
    config_a = envelope(space(tables=[table("cat.schema.only_a")]))
    config_b = envelope(space(tables=[table("cat.schema.only_b")]))

    forward = diff_agent_configs(config_a, config_b)
    reverse = diff_agent_configs(config_b, config_a)

    assert forward["serialized_space_changes"]["tables"]["added"] == ["cat.schema.only_b"]
    assert forward["serialized_space_changes"]["tables"]["removed"] == ["cat.schema.only_a"]
    assert reverse["serialized_space_changes"]["tables"]["added"] == ["cat.schema.only_a"]
    assert reverse["serialized_space_changes"]["tables"]["removed"] == ["cat.schema.only_b"]


def test_invalid_stored_json_raises_runtime_error():
    with pytest.raises(RuntimeError, match="invalid JSON"):
        diff_agent_configs({"serialized_space": "{not-json"}, {"serialized_space": "{}"})
    with pytest.raises(RuntimeError, match="serialized_space"):
        diff_agent_configs({}, {})
    with pytest.raises(RuntimeError, match="not a JSON object"):
        diff_agent_configs({"serialized_space": "[]"}, {"serialized_space": "{}"})
