from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SEVERITY = {"compatible": 0, "review": 1, "breaking": 2}


@dataclass(frozen=True)
class Change:
    severity: str
    kind: str
    tool: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "kind": self.kind, "tool": self.tool, "detail": self.detail}


def load_tools(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        value = value.get("tools")
    if not isinstance(value, list):
        raise ValueError("manifest must be a JSON array or an object containing 'tools'")
    tools: list[dict[str, Any]] = []
    for index, tool in enumerate(value):
        if not isinstance(tool, dict) or not isinstance(tool.get("name"), str) or not tool["name"]:
            raise ValueError(f"tool at index {index} must be an object with a non-empty string name")
        schema = tool.get("inputSchema", {})
        if not isinstance(schema, dict):
            raise ValueError(f"tool {tool['name']!r} inputSchema must be an object")
        tools.append(tool)
    return tools


def _properties(schema: dict[str, Any]) -> dict[str, Any]:
    value = schema.get("properties", {})
    return value if isinstance(value, dict) else {}


def _required(schema: dict[str, Any]) -> set[str]:
    value = schema.get("required", [])
    if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
        raise ValueError("schema required must be an array of strings")
    return set(value)


def _tool_id(tool: dict[str, Any]) -> str | None:
    value = tool.get("x-changeguard-id")
    return value if isinstance(value, str) and value else None


def _schema_changes(old: dict[str, Any], new: dict[str, Any], tool: str) -> list[Change]:
    changes: list[Change] = []
    old_props, new_props = _properties(old), _properties(new)
    old_req, new_req = _required(old), _required(new)

    for name in sorted(new_req - old_req):
        changes.append(Change("breaking", "required-added", tool, f"required property added: {name}"))
    for name in sorted(old_req - new_req):
        changes.append(Change("compatible", "required-removed", tool, f"required property removed: {name}"))

    for name in sorted(old_props.keys() - new_props.keys()):
        sev = "breaking" if name in old_req else "review"
        changes.append(Change(sev, "property-removed", tool, f"property removed: {name}"))
    for name in sorted(new_props.keys() - old_props.keys()):
        sev = "breaking" if name in new_req else "compatible"
        changes.append(Change(sev, "property-added", tool, f"property added: {name}"))

    for name in sorted(old_props.keys() & new_props.keys()):
        before, after = old_props[name], new_props[name]
        if not isinstance(before, dict) or not isinstance(after, dict):
            if before != after:
                changes.append(Change("breaking", "property-schema", tool, f"property schema changed: {name}"))
            continue
        if before.get("type") != after.get("type"):
            changes.append(Change("breaking", "type-changed", tool, f"property type changed: {name}"))
        old_enum, new_enum = before.get("enum"), after.get("enum")
        if isinstance(old_enum, list) and isinstance(new_enum, list) and old_enum != new_enum:
            old_set, new_set = set(old_enum), set(new_enum)
            sev = "breaking" if not old_set <= new_set else "compatible"
            changes.append(Change(sev, "enum-changed", tool, f"enum changed: {name}"))

    old_add, new_add = old.get("additionalProperties"), new.get("additionalProperties")
    if old_add != new_add and (old_add is not None or new_add is not None):
        sev = "breaking" if new_add is False else "review"
        changes.append(Change(sev, "additional-properties", tool, "additionalProperties policy changed"))
    return changes


def compare(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[Change]:
    old_by_id = {_tool_id(t): t for t in before if _tool_id(t)}
    new_by_id = {_tool_id(t): t for t in after if _tool_id(t)}
    old_by_name = {t["name"]: t for t in before}
    new_by_name = {t["name"]: t for t in after}
    changes: list[Change] = []

    matched_old: set[str] = set()
    matched_new: set[str] = set()
    for ident in sorted(old_by_id.keys() & new_by_id.keys()):
        old, new = old_by_id[ident], new_by_id[ident]
        matched_old.add(old["name"]); matched_new.add(new["name"])
        if old["name"] != new["name"]:
            changes.append(Change("review", "renamed", new["name"], f"tool renamed from {old['name']!r}"))
        if old.get("description") != new.get("description"):
            changes.append(Change("review", "description-changed", new["name"], "description changed"))
        changes.extend(_schema_changes(old.get("inputSchema", {}), new.get("inputSchema", {}), new["name"]))

    for name in sorted((old_by_name.keys() - matched_old) - new_by_name.keys()):
        changes.append(Change("breaking", "tool-removed", name, "tool removed"))
    for name in sorted((new_by_name.keys() - matched_new) - old_by_name.keys()):
        changes.append(Change("review", "tool-added", name, "tool added"))

    for name in sorted(old_by_name.keys() & new_by_name.keys()):
        if name in matched_old or name in matched_new:
            continue
        old, new = old_by_name[name], new_by_name[name]
        if old.get("description") != new.get("description"):
            changes.append(Change("review", "description-changed", name, "description changed"))
        changes.extend(_schema_changes(old.get("inputSchema", {}), new.get("inputSchema", {}), name))
    return changes
