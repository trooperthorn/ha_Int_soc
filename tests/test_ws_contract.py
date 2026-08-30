"""Client/server WebSocket contract test (Decision D-17 safe default).

Every `type: "ha_soc/..."` payload object the frontend sends (extracted
straight from `frontend/src/data/ha-soc-ws.ts`) must carry every
`vol.Required` key of the matching server handler's voluptuous schema.
This is exactly the class of bug that shipped as UI-1 (work plan item
0.4): `ws_entity_remap_apply` required `backup_acknowledged`, the client
never sent it, so every apply failed schema validation before the handler
ever ran and the whole feature was unreachable from the panel.

The extraction is a small character-level walk over the TypeScript source
rather than a real parser: it brace-matches the object literal that starts
with a `type: "ha_soc/..."` property and collects the top-level property
names, tracking string literals and nesting so multi-line payloads and
nested values are handled. Spread properties (`...params`) and other
dynamic keys are deliberately NOT resolved; a required key must be written
out explicitly in the payload for this test to accept it, which is the
safe direction (a false failure here is fixed by writing the key
explicitly, while resolving spreads could hide a genuinely missing key).

Server schemas are discovered by importing the integration's
`websocket_api` module and reading the `_ws_command` / `_ws_schema`
attributes that `homeassistant.components.websocket_api.decorators
.websocket_command` stores on each handler (verified against the
installed core: `_ws_schema` is `False` for a type-only schema, otherwise
the dict schema extended with `BASE_COMMAND_MESSAGE_SCHEMA`, which adds
only the required `id` key that `hass.callWS` injects itself).
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import voluptuous as vol

from custom_components.ha_soc import websocket_api as ha_soc_ws

CLIENT_TS_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "ha_soc"
    / "frontend"
    / "src"
    / "data"
    / "ha-soc-ws.ts"
)

# Keys the client does not have to spell out: `id` is injected by
# hass.callWS on every message, and `type` is the anchor the extraction
# below matches on, so it is present by construction.
_IMPLICIT_KEYS = {"id", "type"}

_IDENTIFIER = r"[A-Za-z_$][A-Za-z0-9_$]*"


def _parse_object_keys(source: str, open_brace: int) -> tuple[set[str], bool]:
    """Collect the top-level property names of the object literal starting
    at `open_brace`, plus whether it contains a spread (`...`) property.

    Walks characters, tracking (), [], {} nesting and ', ", ` string
    literals (with backslash escapes), and splits top-level properties on
    commas at depth 1. Values may be arbitrarily nested; only the leading
    identifier of each property is taken. `${...}` interpolation inside
    template literals is not modeled because no payload in ha-soc-ws.ts
    uses one; an unparseable property fails the test loudly below rather
    than being dropped silently.
    """
    assert source[open_brace] == "{"
    depth = 0
    in_string: str | None = None
    escaped = False
    segments: list[str] = []
    current: list[str] = []
    index = open_brace
    end = len(source)
    while index < end:
        char = source[index]
        if in_string is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            current.append(char)
        elif char in "\"'`":
            in_string = char
            current.append(char)
        elif char in "([{":
            depth += 1
            if not (char == "{" and depth == 1):
                current.append(char)
        elif char in ")]}":
            depth -= 1
            if char == "}" and depth == 0:
                segments.append("".join(current))
                break
            current.append(char)
        elif char == "," and depth == 1:
            segments.append("".join(current))
            current = []
        else:
            current.append(char)
        index += 1
    else:
        raise AssertionError(
            f"unterminated object literal at offset {open_brace} in {CLIENT_TS_PATH.name}"
        )

    keys: set[str] = set()
    has_spread = False
    for raw in segments:
        segment = raw.strip()
        if not segment:
            continue
        if segment.startswith("..."):
            has_spread = True
            continue
        explicit = re.match(rf"^({_IDENTIFIER})\s*:", segment)
        if explicit:
            keys.add(explicit.group(1))
            continue
        if re.fullmatch(_IDENTIFIER, segment):
            # Shorthand property, e.g. `{ topic }` sends the key "topic".
            keys.add(segment)
            continue
        raise AssertionError(
            f"unrecognized payload property {segment!r} in {CLIENT_TS_PATH.name}; "
            "teach _parse_object_keys about this shape instead of skipping it"
        )
    return keys, has_spread


def _extract_client_payloads(source: str) -> list[dict[str, Any]]:
    """Every object literal in the client source whose first property is
    `type: "ha_soc/..."`. The `type` property is always written first in
    ha-soc-ws.ts, so the brace immediately before it opens the payload."""
    payloads: list[dict[str, Any]] = []
    for match in re.finditer(r"\{\s*type:\s*\"(ha_soc/[^\"]+)\"", source):
        keys, has_spread = _parse_object_keys(source, match.start())
        payloads.append(
            {"command": match.group(1), "keys": keys, "has_spread": has_spread}
        )
    return payloads


def _server_required_keys() -> dict[str, set[str]]:
    """Map each registered ha_soc/* command to the vol.Required keys of its
    schema, found via the attributes the websocket_command decorator stores
    on every handler in the integration's websocket_api module."""
    required_by_command: dict[str, set[str]] = {}
    for handler in vars(ha_soc_ws).values():
        command = getattr(handler, "_ws_command", None)
        if not isinstance(command, str):
            continue
        schema = getattr(handler, "_ws_schema", None)
        if schema is False or schema is None:
            # A type-only schema; nothing beyond the implicit keys.
            required_by_command[command] = set()
            continue
        if isinstance(schema, vol.All):
            schema = schema.validators[0]
        mapping = schema.schema
        assert isinstance(mapping, dict), f"unexpected schema shape for {command}"
        required = {
            str(marker.schema)
            for marker in mapping
            if isinstance(marker, vol.Required)
        }
        required_by_command[command] = required - _IMPLICIT_KEYS
    return required_by_command


def test_client_payloads_satisfy_server_required_keys() -> None:
    source = CLIENT_TS_PATH.read_text(encoding="utf-8")
    payloads = _extract_client_payloads(source)
    server = _server_required_keys()

    # Guard the guards: if either extraction quietly finds nothing, the
    # test would pass while checking nothing.
    assert payloads, f"no ha_soc/* payloads extracted from {CLIENT_TS_PATH}"
    assert server, "no ha_soc/* handler schemas discovered on the server module"
    apply_payloads = [p for p in payloads if p["command"] == "ha_soc/entity_remap/apply"]
    assert apply_payloads, "the entity_remap/apply payload (the shipped UI-1 bug) was not extracted"
    assert "ha_soc/entity_remap/apply" in server

    problems: list[str] = []
    for payload in payloads:
        required = server.get(payload["command"])
        if required is None:
            problems.append(
                f"{payload['command']}: the client sends this command but no server "
                "handler in websocket_api.py registers it"
            )
            continue
        for key in sorted(required - payload["keys"]):
            problems.append(
                f"{payload['command']}: server schema requires \"{key}\" but the "
                f"client payload only sends {sorted(payload['keys']) or '{}'} "
                "(a spread never satisfies a required key here; write it explicitly)"
            )
    assert not problems, (
        "client payloads in ha-soc-ws.ts violate the server's voluptuous schemas:\n"
        + "\n".join(problems)
    )


def test_entity_remap_client_payload_matches_schema() -> None:
    """The named regression for work plan item 0.4 (UI-1): the apply payload
    must carry every required key, most notably backup_acknowledged."""
    source = CLIENT_TS_PATH.read_text(encoding="utf-8")
    payloads = [
        p
        for p in _extract_client_payloads(source)
        if p["command"] == "ha_soc/entity_remap/apply"
    ]
    assert payloads, "applyEntityRemap payload not found in ha-soc-ws.ts"
    required = _server_required_keys()["ha_soc/entity_remap/apply"]
    assert "backup_acknowledged" in required, (
        "the server no longer requires backup_acknowledged; keep the server-side "
        "gate (work plan item 0.4) rather than weakening it"
    )
    for payload in payloads:
        missing = required - payload["keys"]
        assert not missing, (
            f"ha_soc/entity_remap/apply payload is missing required keys {sorted(missing)}"
        )
