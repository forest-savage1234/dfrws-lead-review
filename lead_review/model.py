"""Validation and deterministic representations for the standalone prototype."""
from __future__ import annotations
import hashlib
import json
import re
from datetime import datetime, UTC
from typing import Any

ID = re.compile(r"^[a-z][a-z0-9_.-]{1,100}$")
MAX_SOURCE_BYTES = 65536

class ReviewError(ValueError):
    pass

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)

def digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()

def identifier(value: str) -> str:
    if not isinstance(value, str) or ID.fullmatch(value) is None:
        raise ReviewError("Identifiers must be bounded lowercase tokens.")
    return value

def text(value: str, name: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ReviewError(f"{name} must be nonempty and at most {maximum} characters.")
    if any(ord(c) < 32 for c in value):
        raise ReviewError(f"{name} contains control characters.")
    return value.strip()

def utc_time(value: str) -> str:
    if not isinstance(value, str):
        raise ReviewError("Event time must be an ISO timestamp with a timezone.")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReviewError("Event time must be an ISO timestamp with a timezone.") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ReviewError("Event time has no timezone; it cannot be compared reliably.")
    return dt.astimezone(UTC).isoformat().replace("+00:00", "Z")

def load_source(raw: bytes) -> tuple[str, dict]:
    if not isinstance(raw, bytes) or len(raw) > MAX_SOURCE_BYTES:
        raise ReviewError("Sources must be UTF-8 JSON, at most 64 KiB.")
    def pairs(items):
        out = {}
        for k, v in items:
            if k in out:
                raise ReviewError("Duplicate JSON keys are ambiguous.")
            out[k] = v
        return out
    def constant(value):
        raise ReviewError(f"Invalid JSON numeric constant: {value}")
    try:
        source_text = raw.decode("utf-8")
        value = json.loads(source_text, object_pairs_hook=pairs, parse_constant=constant)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReviewError("Sources must be unambiguous UTF-8 JSON objects.") from exc
    if not isinstance(value, dict):
        raise ReviewError("Source JSON must be an object.")
    return source_text, value

def input_refs(refs: list[dict]) -> list[dict]:
    if not isinstance(refs, list) or len(refs) > 100:
        raise ReviewError("Inputs must be a list of at most 100 dependency references.")
    out = []
    for ref in refs:
        if not isinstance(ref, dict) or set(ref) != {"node_id", "fields"}:
            raise ReviewError("Each input requires node_id and fields.")
        fields = ref["fields"]
        if not isinstance(fields, list) or not fields or len(fields) != len(set(fields)):
            raise ReviewError("Dependency fields must be a nonempty, unique list.")
        for field in fields:
            if field != "*":
                identifier(field)
        if "*" in fields and len(fields) != 1:
            raise ReviewError("A wildcard must be the entire field scope.")
        out.append({"node_id": identifier(ref["node_id"]), "fields": sorted(fields)})
    if len({r["node_id"] for r in out}) != len(out):
        raise ReviewError("Duplicate input nodes are not permitted.")
    return out

def descendants(roots: dict[str, set[str]], edges: list[dict]) -> dict[str, list[str]]:
    """A -> B means B depends on A; scopes apply to the changed input fields.

    Return one deterministic witness path per reachable dependent. A derived
    node's possible impact propagates conservatively as '*'. This is dependency
    traversal, not a conclusion that a hypothesis is factually correct.
    """
    adjacent = {}
    for edge in edges:
        adjacent.setdefault(edge["input_id"], []).append(edge)
    queue = [(node, set(fields), [node]) for node, fields in sorted(roots.items())]
    reached = {}
    visited = set()
    while queue:
        node, changed, path = queue.pop(0)
        marker = (node, tuple(sorted(changed)))
        if marker in visited:
            continue
        visited.add(marker)
        for edge in sorted(adjacent.get(node, []), key=lambda x: x["owner_id"]):
            scope = set(edge["fields"])
            if "*" not in scope and "*" not in changed and not (scope & changed):
                continue
            owner = edge["owner_id"]
            if owner in roots or owner in path:
                continue
            new_path = path + [owner]
            reached.setdefault(owner, new_path)
            queue.append((owner, {"*"}, new_path))
    return reached
