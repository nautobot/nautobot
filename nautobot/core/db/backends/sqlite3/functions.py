"""Python implementations of SQL functions that SQLite lacks but Nautobot's query code emits."""

import json

import netaddr

from nautobot.ipam.constants import IPV4_BYTE_LENGTH


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _json_contains(target, candidate):
    """Return whether `candidate` is contained in `target` using PostgreSQL `@>` / MySQL `JSON_CONTAINS` semantics."""
    if isinstance(target, dict):
        if not isinstance(candidate, dict):
            return False
        return all(key in target and _json_contains(target[key], value) for key, value in candidate.items())
    if isinstance(target, list):
        if isinstance(candidate, list):
            return all(any(_json_contains(item, value) for item in target) for value in candidate)
        return any(_json_contains(item, candidate) for item in target)
    if _is_number(target) and _is_number(candidate):
        return target == candidate
    return type(target) is type(candidate) and target == candidate


def _extract_path(document, path):
    """Resolve a JSON path of the form `$`, `$.key` or `$."key"` against a parsed document."""
    if path in (None, "$"):
        return document
    if not path.startswith("$."):
        raise ValueError(f"Unsupported JSON path {path!r}")
    key = path[2:]
    if key.startswith('"') and key.endswith('"'):
        key = key[1:-1]
    if not isinstance(document, dict):
        return None
    return document.get(key)


def _load_json(value):
    """Parse JSON text; a value that is not JSON text is taken as an already-extracted SQL scalar."""
    if not isinstance(value, (str, bytes)):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return value if isinstance(value, str) else value.decode()


def json_contains(target, candidate, path="$"):
    """SQL `JSON_CONTAINS(target, candidate[, path])`, as used by Django's JSONField `contains` lookup."""
    if target is None or candidate is None:
        return None
    target = _load_json(target)
    candidate = _load_json(candidate)
    target = _extract_path(target, path)
    if target is None:
        return 0
    return 1 if _json_contains(target, candidate) else 0


def inet6_ntoa(value):
    """SQL `INET6_NTOA(blob)`: render a packed IPv4 or IPv6 address as a string."""
    if value is None:
        return None
    version = 4 if len(value) == IPV4_BYTE_LENGTH else 6
    return str(netaddr.IPAddress(int.from_bytes(value, "big"), version=version))


def register_functions(connection):
    """Register Nautobot's SQL functions on a new `sqlite3` connection."""
    connection.create_function("JSON_CONTAINS", -1, json_contains, deterministic=True)
    connection.create_function("INET6_NTOA", 1, inet6_ntoa, deterministic=True)
