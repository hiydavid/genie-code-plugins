"""Pure structural diff between two stored Genie Agent configuration envelopes.

The comparison is keyed by the identity keys the Genie Agents API itself enforces
(every repeated field is sorted and unique by its key), so a set-diff is well-defined
without positional matching. The result carries identifiers, counts, and booleans —
never configuration content: instruction text, SQL bodies, benchmark questions, and
``description`` values can each approach the API's 25,000-character string limit.

Legacy exports carry ``config`` with no ``instructions``; missing collections are
treated as empty, never as errors. Unknown top-level ``serialized_space`` fields are
reported by name only, which keeps the diff forward-compatible as the schema grows.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

# Identifier lists cap here so even a catalog-wide rename on an Agent with hundreds of
# data sources stays small in model context; exact totals travel beside truncated lists.
MAX_IDENTIFIER_LIST = 50

_KNOWN_SPACE_FIELDS = frozenset({"version", "config", "data_sources", "instructions", "benchmarks"})
_MISSING = object()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _keyed(items: Any, key: str) -> dict[str, Mapping[str, Any]]:
    """Index one API collection by its documented identity key.

    Missing or malformed collections index as empty — the store accepts legacy payloads
    where whole collections are absent, and entries without their identity key cannot be
    matched across versions.
    """
    index: dict[str, Mapping[str, Any]] = {}
    if not isinstance(items, list):
        return index
    for entry in items:
        if isinstance(entry, Mapping) and isinstance(entry.get(key), str) and entry[key]:
            index[entry[key]] = entry
    return index


def _nullable_sort_key(value: Any) -> tuple[bool, str]:
    return (value is None, str(value))


def _capped(entries: list[Any], name: str) -> dict[str, Any]:
    """Emit one identifier list, adding truncation siblings only when actually cut."""
    if len(entries) <= MAX_IDENTIFIER_LIST:
        return {name: entries}
    return {
        name: entries[:MAX_IDENTIFIER_LIST],
        f"{name}_truncated": True,
        f"{name}_total": len(entries),
    }


def _parsed_space(config: Mapping[str, Any]) -> dict[str, Any]:
    raw = config.get("serialized_space")
    if not isinstance(raw, str):
        raise RuntimeError("stored configuration envelope has no serialized_space string")
    try:
        parsed = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError("stored configuration envelope is invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise RuntimeError("stored configuration envelope is not a JSON object")
    return parsed


def _envelope_changes(config_a: Mapping[str, Any], config_b: Mapping[str, Any]) -> dict:
    changes: dict[str, Any] = {}
    for field in ("title", "warehouse_id", "parent_path"):
        value_a, value_b = config_a.get(field), config_b.get(field)
        changes[field] = {"changed": value_a != value_b, "a": value_a, "b": value_b}
    # `description` is free prose that can approach the 25k-char limit: flag only.
    changes["description"] = {"changed": config_a.get("description") != config_b.get("description")}
    return changes


def _count_changes(a_items: Any, b_items: Any, key: str) -> dict[str, int]:
    a_index, b_index = _keyed(a_items, key), _keyed(b_items, key)
    return {
        "added": len(b_index.keys() - a_index.keys()),
        "removed": len(a_index.keys() - b_index.keys()),
        "modified": sum(1 for k in a_index.keys() & b_index.keys() if a_index[k] != b_index[k]),
    }


def _column_changes(a_entry: Mapping[str, Any], b_entry: Mapping[str, Any]) -> dict[str, Any]:
    a_columns = _keyed(a_entry.get("column_configs"), "column_name")
    b_columns = _keyed(b_entry.get("column_configs"), "column_name")
    return {
        "columns_added": sorted(b_columns.keys() - a_columns.keys()),
        "columns_removed": sorted(a_columns.keys() - b_columns.keys()),
        "columns_modified": sorted(
            name
            for name in a_columns.keys() & b_columns.keys()
            if a_columns[name] != b_columns[name]
        ),
    }


def _table_like_changes(a_items: Any, b_items: Any) -> dict[str, Any]:
    """Keyed set-diff for tables and metric views (identity key: three-part identifier)."""
    a_index, b_index = _keyed(a_items, "identifier"), _keyed(b_items, "identifier")
    added = sorted(b_index.keys() - a_index.keys())
    removed = sorted(a_index.keys() - b_index.keys())
    modified: list[dict[str, Any]] = []
    for identifier in sorted(a_index.keys() & b_index.keys()):
        a_entry, b_entry = a_index[identifier], b_index[identifier]
        if a_entry == b_entry:
            continue
        modified.append(
            {
                "identifier": identifier,
                "description_changed": a_entry.get("description") != b_entry.get("description"),
                **_column_changes(a_entry, b_entry),
            }
        )
    changes: dict[str, Any] = {}
    changes.update(_capped(added, "added"))
    changes.update(_capped(removed, "removed"))
    changes.update(_capped(modified, "modified"))
    return changes


def _sql_function_changes(a_items: Any, b_items: Any) -> dict[str, Any]:
    """Same-id/different-identifier pairs are renames, not remove+add."""
    a_index, b_index = _keyed(a_items, "id"), _keyed(b_items, "id")
    added = sorted(
        (b_index[k].get("identifier") for k in b_index.keys() - a_index.keys()),
        key=_nullable_sort_key,
    )
    removed = sorted(
        (a_index[k].get("identifier") for k in a_index.keys() - b_index.keys()),
        key=_nullable_sort_key,
    )
    renamed: list[dict[str, Any]] = []
    modified = 0
    for function_id in sorted(a_index.keys() & b_index.keys()):
        a_entry, b_entry = a_index[function_id], b_index[function_id]
        if a_entry.get("identifier") != b_entry.get("identifier"):
            renamed.append({"from": a_entry.get("identifier"), "to": b_entry.get("identifier")})
        elif a_entry != b_entry:
            modified += 1
    changes: dict[str, Any] = {}
    changes.update(_capped(added, "added"))
    changes.update(_capped(removed, "removed"))
    changes["modified"] = modified
    changes.update(_capped(renamed, "renamed"))
    return changes


def _single_entry_changed(a_items: Any, b_items: Any) -> bool:
    """`text_instructions` holds at most one entry; presence counts as a change too."""
    a_entry = a_items[0] if isinstance(a_items, list) and a_items else None
    b_entry = b_items[0] if isinstance(b_items, list) and b_items else None
    return a_entry != b_entry


def _unknown_field_changes(space_a: Mapping[str, Any], space_b: Mapping[str, Any]) -> list[str]:
    unknown_a = {k: v for k, v in space_a.items() if k not in _KNOWN_SPACE_FIELDS}
    unknown_b = {k: v for k, v in space_b.items() if k not in _KNOWN_SPACE_FIELDS}
    return sorted(
        name
        for name in unknown_a.keys() | unknown_b.keys()
        if unknown_a.get(name, _MISSING) != unknown_b.get(name, _MISSING)
    )


def _serialized_space_changes(
    space_a: Mapping[str, Any], space_b: Mapping[str, Any]
) -> dict[str, Any]:
    # `config` is the legacy body field inside serialized_space (sample_questions home).
    config_body_a, config_body_b = _mapping(space_a.get("config")), _mapping(space_b.get("config"))
    instructions_a, instructions_b = (
        _mapping(space_a.get("instructions")),
        _mapping(space_b.get("instructions")),
    )
    data_sources_a, data_sources_b = (
        _mapping(space_a.get("data_sources")),
        _mapping(space_b.get("data_sources")),
    )
    snippets_a, snippets_b = (
        _mapping(instructions_a.get("sql_snippets")),
        _mapping(instructions_b.get("sql_snippets")),
    )
    benchmarks_a, benchmarks_b = (
        _mapping(space_a.get("benchmarks")),
        _mapping(space_b.get("benchmarks")),
    )
    return {
        "version": {
            "changed": space_a.get("version") != space_b.get("version"),
            "a": space_a.get("version"),
            "b": space_b.get("version"),
        },
        "sample_questions": _count_changes(
            config_body_a.get("sample_questions"),
            config_body_b.get("sample_questions"),
            "id",
        ),
        "tables": _table_like_changes(data_sources_a.get("tables"), data_sources_b.get("tables")),
        "metric_views": _table_like_changes(
            data_sources_a.get("metric_views"), data_sources_b.get("metric_views")
        ),
        "instructions": {
            "text_instructions": {
                "modified": _single_entry_changed(
                    instructions_a.get("text_instructions"),
                    instructions_b.get("text_instructions"),
                )
            },
            "example_question_sqls": _count_changes(
                instructions_a.get("example_question_sqls"),
                instructions_b.get("example_question_sqls"),
                "id",
            ),
            "sql_functions": _sql_function_changes(
                instructions_a.get("sql_functions"), instructions_b.get("sql_functions")
            ),
            "join_specs": _count_changes(
                instructions_a.get("join_specs"), instructions_b.get("join_specs"), "id"
            ),
            "sql_snippets": {
                group: _count_changes(snippets_a.get(group), snippets_b.get(group), "id")
                for group in ("filters", "expressions", "measures")
            },
        },
        "benchmarks": {
            "questions": _count_changes(
                benchmarks_a.get("questions"), benchmarks_b.get("questions"), "id"
            )
        },
        "unknown_fields_changed": _unknown_field_changes(space_a, space_b),
    }


# Zero-value envelope used to derive the all-zero shortcut sections from the real diff
# implementation, so the shortcut shape can never drift from the computed shape.
_EMPTY_ENVELOPE: Mapping[str, Any] = {
    "serialized_space": "{}",
    "title": None,
    "description": None,
    "warehouse_id": None,
    "parent_path": None,
}


def empty_diff_sections() -> dict[str, Any]:
    """All-zero sections for the ``config_hash`` shortcut (no envelopes loaded)."""
    return diff_agent_configs(_EMPTY_ENVELOPE, _EMPTY_ENVELOPE)


def diff_agent_configs(config_a: Mapping[str, Any], config_b: Mapping[str, Any]) -> dict[str, Any]:
    """Structurally diff two parsed restore envelopes.

    ``added`` always means "present in ``config_b`` only"; the tool layer assigns the
    a/b labels from row timestamps before calling this. No I/O, fully unit-testable.
    """
    space_a = _parsed_space(config_a)
    space_b = _parsed_space(config_b)
    return {
        "envelope_changes": _envelope_changes(config_a, config_b),
        "serialized_space_changes": _serialized_space_changes(space_a, space_b),
    }
