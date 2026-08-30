"""Local, heuristic static-analysis scanner for installed integrations.

This is NOT a vulnerability scanner in the CVE-matching sense (see vulns.py
for that) and it is NOT a substitute for a human security review. Every
finding it produces is a pattern match against source text — an advisory
signal for the instance owner to look at, never a confirmed exploit and
never a verdict on the integration or its author. Nothing here is reported
upstream automatically; there is no disclosure channel, GHSA submission, or
network call anywhere in this module. `export_ghsa()` only *shapes* a
finding into GHSA-like fields for a human to copy-paste if they choose to.

Why this exists: hassfest (core's own integration-quality tool) validates
manifests, docs, and typing — it never executes or pattern-matches an
integration's code, and it never runs against `custom_components` at all.
Nobody upstream reviews third-party custom integration source for security
issues. This module fills exactly that gap, for the local instance owner,
using a small dependency-free rule set (stdlib `ast`/`re` only) so HA SOC
never adds a large, frequently-CVE'd static-analysis dependency to every
install that pulls this integration in. It works identically for core
integrations and custom ones: both are just files on the same filesystem,
in the same trust domain as the rest of `config/`, read here and never
executed.

Explicitly out of scope for this version: any network call (PyPI staleness
checks, typosquat detection against a package index). That is a
`scanner_network_checks_enabled` feature for a future version and is not
stubbed here — half-implementing it would be worse than omitting it.

Coverage honesty (work plan item 4.8): every rule here matches unobfuscated
instances only - string-built calls, computed names, and encoded literals
are invisible by design, and the Scanner tab must say so. Each completed
scan stores a per-domain coverage record ({scanned_files, skipped_oversize,
skipped_over_cap, parse_failures, scanned_at}) alongside the findings, and
`listing_payload` exposes it so a domain with no record renders as "not
scanned", never as an implied-clean zero findings. After each rescan,
findings absent from the new scan are reconciled to resolved with
resolved_reason "not_found_on_rescan" - but only when their file was
actually evaluated this pass (or deleted outright), never when it was
skipped for size, the file cap, or a parse failure.
"""
from __future__ import annotations

import ast
import asyncio
import hashlib
import logging
import re
from pathlib import Path
from typing import Any, Callable

import homeassistant.helpers.issue_registry as ir
import homeassistant.util.dt as dt_util
from homeassistant.config_entries import (
    SIGNAL_CONFIG_ENTRY_CHANGED,
    ConfigEntry,
    ConfigEntryChange,
)
from homeassistant.core import HomeAssistant, valid_domain
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.loader import async_get_integration

from .const import DOMAIN, INTEGRATION_LOCATOR_KEYS
from .store import HaSocData

_LOGGER = logging.getLogger(__name__)

# -- Resource bounds --------------------------------------------------------
# Applied per integration, inside the executor job. A malicious or merely
# huge integration directory must never be able to block the executor pool
# indefinitely or exhaust memory parsing a single file.
MAX_FILE_SIZE_BYTES = 500 * 1024
MAX_FILES_PER_SCAN = 400

_PLACEHOLDER_RE = re.compile(
    r"^(changeme|xxx+|todo|example|placeholder|your[_-]?\w+[_-]?here|<.*>|\$\{.*\})$",
    re.IGNORECASE,
)
_CREDENTIAL_NAME_RE = re.compile(
    r"(password|passwd|api[_-]?key|secret|access[_-]?key|auth[_-]?token)", re.IGNORECASE
)
# HA's own universal naming convention (homeassistant.const's CONF_PASSWORD,
# CONF_API_KEY, etc., and every integration that follows the same pattern):
# a CONF_* constant holds a voluptuous/config-schema KEY NAME, never a
# secret value — the actual secret lives in a config entry or this
# integration's own Store, entered by the user at runtime, not in source.
# Excluded here rather than by raising the length/entropy bar, since the
# false positive is about *what kind of thing* the name identifies, not
# about how convincing the literal value looks.
_CONF_CONSTANT_NAME_RE = re.compile(r"^CONF_")

# The sibling convention to CONF_*: an ALL_CAPS constant ending in _KEY or
# _KEYS names a storage or dictionary KEY, not a credential (ha_soc's own
# PROBE_PAIRING_SECRET_KEY = "probe_pairing_secret" in secrets_store.py is
# the shape). Like the CONF_ guard, this is about what kind of thing the
# NAME identifies; the value-shape condition exists only to keep the
# exclusion narrow. Both must hold: the target is an ALL_CAPS *_KEY(S)
# constant, and the literal is a multi-word, digit-free lowercase
# identifier (words joined by underscores or dots). A lowercase variable
# like api_key = "..." never matches the name pattern, so the rule is not
# weakened for it, and API_KEY = "hunter2secret9" still fires on its
# digits. The documented false-negative avenue: a genuinely digit-free,
# multi-word, all-lowercase credential assigned to an ALL_CAPS *_KEY name.
_KEY_NAME_CONSTANT_RE = re.compile(r"^[A-Z][A-Z0-9_]*_KEYS?(?:_NAME)?$")
_IDENTIFIER_VALUE_RE = re.compile(r"^[a-z]+(?:[_.][a-z]+)+$")
_SENSITIVE_ARG_RE = re.compile(
    r"(token|password|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)", re.IGNORECASE
)
_LOGGER_OWNER_RE = re.compile(r"(^|_)(logger|log)$", re.IGNORECASE)

_SUBPROCESS_FUNC_NAMES = {"Popen", "call", "check_call", "check_output", "run"}
_LOGGER_METHOD_NAMES = {"debug", "info", "warning", "error", "exception"}

_SEVERITY_BY_CONFIDENCE = {"high": "high", "medium": "medium", "advisory": "info"}


def _hit(
    lineno: int,
    lines: list[str],
    pattern: str,
    cwe: str,
    confidence: str,
    snippet: str | None = None,
) -> dict[str, Any]:
    # A rule may pass an explicit snippet when the source line itself must
    # not be stored verbatim (the hardcoded_credential rule masks the
    # matched literal this way, work plan item 1.3).
    if snippet is None:
        raw = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
        snippet = raw.strip()[:160]
    return {
        "lineno": lineno,
        "snippet": snippet,
        "pattern": pattern,
        "cwe": cwe,
        "confidence": confidence,
    }


def _dotted_name(node: ast.AST | None) -> str | None:
    """Dotted name of a Name/Attribute chain, walked iteratively: a
    crafted file can nest attribute access thousands of levels deep, and
    a recursive walk would hit RecursionError inside a rule, aborting the
    file's scan (work plan item 4.8)."""
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    elif not parts:
        return None
    return ".".join(reversed(parts))


def _assign_target_name(target: ast.AST) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


# -- Rule 1: disabled TLS verification --------------------------------------
def _rule_tls_verification_disabled(tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
    """`verify`/`ssl`/`cert_reqs` keyword literally `False`, or `ssl.CERT_NONE`.

    Library-agnostic on purpose: matches the keyword name, not the callee, so
    it catches requests/httpx/aiohttp-style calls without knowing which HTTP
    client is in play.
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg not in ("verify", "ssl", "cert_reqs"):
                continue
            value = kw.value
            is_false = isinstance(value, ast.Constant) and value.value is False
            is_cert_none = isinstance(value, ast.Attribute) and value.attr == "CERT_NONE"
            if is_false or is_cert_none:
                hits.append(_hit(node.lineno, lines, "tls_verification_disabled", "CWE-295", "high"))
    return hits


def _is_subprocess_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr in _SUBPROCESS_FUNC_NAMES
    if isinstance(func, ast.Name):
        return func.id in _SUBPROCESS_FUNC_NAMES
    return False


def _is_interpolated(node: ast.AST) -> bool:
    if isinstance(node, ast.JoinedStr):
        return True
    if isinstance(node, ast.BinOp):
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return True
    return False


# os.system / os.popen always hand their argument to a shell, so they join
# the shell rule with no shell=True co-condition needed (work plan item
# 4.8); the interpolated-argument co-condition still applies.
_ALWAYS_SHELL_CALLS = {"os.system", "os.popen"}


# -- Rule 2: command injection risk -----------------------------------------
def _rule_shell_injection_risk(tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
    """`shell=True` alone is not the signal — a hardcoded literal command run
    with `shell=True` is not attacker-controlled. Only flag it alongside an
    argument built from an f-string, concatenation/%-format, or `.format()`:
    that co-condition is what makes an external value's path into the shell
    plausible, and it's the reason this rule needs two things to be true at
    once rather than firing on `shell=True` by itself. ``os.system`` and
    ``os.popen`` always run a shell, so for them the interpolation
    co-condition alone triggers the rule (work plan item 4.8). Obvious
    false negative either way: a command assembled into a variable before
    the call carries no interpolation at the call site and is invisible.
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _is_subprocess_call(node):
            shell_true = any(
                kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
                for kw in node.keywords
            )
            if not shell_true:
                continue
        elif _dotted_name(node.func) not in _ALWAYS_SHELL_CALLS:
            continue
        candidate_args = list(node.args) + [kw.value for kw in node.keywords if kw.arg != "shell"]
        if any(_is_interpolated(arg) for arg in candidate_args):
            hits.append(_hit(node.lineno, lines, "shell_injection_risk", "CWE-78", "high"))
    return hits


# -- Rule 3: eval/exec use ---------------------------------------------------
def _rule_eval_exec_use(tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            hits.append(_hit(node.lineno, lines, "eval_exec_use", "CWE-95", "high"))
    return hits


def _yaml_load_has_safe_loader(node: ast.Call) -> bool:
    loader_arg: ast.AST | None = node.args[1] if len(node.args) >= 2 else None
    for kw in node.keywords:
        if kw.arg == "Loader":
            loader_arg = kw.value
    if loader_arg is None:
        return False
    name = _dotted_name(loader_arg)
    return name is not None and name.rsplit(".", 1)[-1] in ("SafeLoader", "CSafeLoader")


# -- Rule 4: insecure deserialization ----------------------------------------
def _rule_insecure_deserialization(tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
    """`pickle.load(s)` is always flagged; `yaml.load(...)` only when it is
    not explicitly given a Safe(C)Loader. `yaml.safe_load` never reaches this
    rule at all since its func name isn't `load`.
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        owner = _dotted_name(node.func.value)
        if owner is None:
            continue
        owner_lower = owner.lower()
        if node.func.attr in ("load", "loads") and "pickle" in owner_lower:
            hits.append(_hit(node.lineno, lines, "insecure_deserialization", "CWE-502", "medium"))
        elif node.func.attr == "load" and "yaml" in owner_lower and not _yaml_load_has_safe_loader(node):
            hits.append(_hit(node.lineno, lines, "insecure_deserialization", "CWE-502", "medium"))
    return hits


# -- Rule 5: hardcoded credentials -------------------------------------------
def _rule_hardcoded_credential(tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
    """Name-pattern + literal-string heuristic only, with no entropy or
    secret-format check behind it. That means fixtures, docs examples, and
    test constants will match too — an accepted, permanent source of false
    positives, not something a future version should "fix" by escalating
    confidence past medium. Confidence here stays "medium" forever by design.

    Two name-convention guards keep the rule honest about what a NAME
    identifies rather than how a value looks: CONF_* constants hold
    config-schema key names, and ALL_CAPS *_KEY(S) constants whose literal
    is a digit-free lowercase identifier hold storage or dictionary key
    names (see _KEY_NAME_CONSTANT_RE for the exact conditions and the
    false-negative avenue each guard accepts). Lowercase variables such as
    api_key = "..." are outside both guards and always evaluated.

    The stored snippet is the assignment target plus a masked value, e.g.
    ``token = "[redacted, 40 chars]"``. If the match is real, the literal is
    a live credential, and the finding travels far beyond this module (the
    store on disk, every WebSocket listing, the GHSA export text an operator
    may paste elsewhere), so the literal itself must never leave this
    function (work plan item 1.3).
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        # AnnAssign joins the rule (work plan item 4.8): an annotated
        # ``token: str = "..."`` is the same hardcoded credential with a
        # type hint in front of it.
        if isinstance(node, ast.Assign):
            targets: list[ast.AST] = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        value = node.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            continue
        literal = value.value
        if len(literal) < 6 or _PLACEHOLDER_RE.search(literal):
            continue
        for target in targets:
            name = _assign_target_name(target)
            if not name or _CONF_CONSTANT_NAME_RE.match(name):
                continue
            if _KEY_NAME_CONSTANT_RE.match(name) and _IDENTIFIER_VALUE_RE.match(literal):
                continue
            if _CREDENTIAL_NAME_RE.search(name):
                masked = f'{name} = "[redacted, {len(literal)} chars]"'
                hits.append(
                    _hit(node.lineno, lines, "hardcoded_credential", "CWE-798", "medium", snippet=masked)
                )
                break
    return hits


def _logger_owner_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _is_sensitive_name(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and bool(_SENSITIVE_ARG_RE.search(node.id))


# -- Rule 6: logging sensitive fields -----------------------------------------
def _rule_sensitive_data_logged(tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _LOGGER_METHOD_NAMES:
            continue
        owner = _logger_owner_name(node.func.value)
        if not owner or not _LOGGER_OWNER_RE.search(owner):
            continue
        candidates: list[ast.AST] = list(node.args)
        for arg in node.args:
            if isinstance(arg, ast.JoinedStr):
                candidates.extend(v.value for v in arg.values if isinstance(v, ast.FormattedValue))
        if any(_is_sensitive_name(candidate) for candidate in candidates):
            hits.append(_hit(node.lineno, lines, "sensitive_data_logged", "CWE-532", "medium"))
    return hits


# -- Cross-integration extraction rules (work plan item SEC-5) ---------------
# Home Assistant has no process isolation between integrations: any
# integration can enumerate every config entry, open any file the Core
# process can read, and reach into any other integration's hass.data. The
# four rules below flag the extraction patterns that boundary-lessness
# enables. Like every other rule in this module they are advisory pattern
# matches, never verdicts.
#
# All four rules only see what is statically visible in one file's AST. A
# target held in a variable, a constant imported from another module, an
# f-string, or a subclass wrapper is invisible to them, and each rule's
# docstring names that evasion avenue. They also honor a scoped, visible
# acknowledgment marker (see _apply_allow_marker) so a deliberate,
# documented cross-integration read can be recorded as acknowledged in the
# findings table instead of ringing as an open alarm forever. HA SOC's own
# code must pass all four rules with zero open findings (SEC-4/SEC-5), and
# nothing here special-cases the ha_soc domain string: the rules' precise
# definitions are what its legitimate reads pass through.

# Both enumeration surfaces on hass.config_entries return other
# integrations' ConfigEntry objects, so rule (a) watches both.
_ENTRY_ENUM_METHODS = {"async_entries", "async_loaded_entries"}

# hass.data keys registered by core's own bootstrap and helpers modules
# (every string below was collected from the HassKey("...") registrations in
# homeassistant/*.py and homeassistant/helpers/*.py of core 2026.2.3).
# Subscripting hass.data with one of these reads core infrastructure, not
# another integration's private state, so rule (c) skips them. A custom
# integration whose domain happens to collide with one of these names is a
# documented false negative of that skip.
_CORE_HASS_DATA_KEYS = frozenset(
    {
        "aiohttp_clientsession",
        "aiohttp_resolver",
        "all_service_descriptions_cache",
        "area_registry",
        "astral_location_cache",
        "bootstrap_registries_loaded",
        "category_registry",
        "chat_session",
        "chat_session_cleanup",
        "condition_platform_subscriptions",
        "conditions",
        "custom_components",
        "deps_reqs_processed",
        "device_registry",
        "domain_entities",
        "domain_platform_entities",
        "entity_components",
        "entity_registry",
        "floor_registry",
        "hass_customize",
        "homeassistant_stop",
        "httpx_async_client",
        "icon_cache",
        "import_cache",
        "import_failures",
        "integrations",
        "intent",
        "issue_registry",
        "label_registry",
        "llm_action_parameters_cache",
        "logging",
        "missing_platforms",
        "oauth2_impl",
        "oauth2_providers",
        "preload_platforms",
        "recorder",
        "recorder_instance",
        "restore_state",
        "service_description_cache",
        "setup_done",
        "setup_tasks",
        "setup_time",
        "significant_change",
        "storage_manager",
        "storage_semaphore",
        "track_device_registry_updated_data",
        "track_entity_registry_updated_data",
        "track_state_added_domain_data",
        "track_state_removed_domain_data",
        "trigger_disabled_triggers",
        "trigger_platform_subscriptions",
        "triggers",
    }
)

# Method names whose call on a path-like object touches file content, plus
# the callables that build storage paths. Used by rule (b) to decide which
# calls' string literals are worth inspecting at all.
_FILE_ACCESS_ATTRS = {"open", "read_text", "read_bytes", "write_text", "write_bytes"}

_EXTRACTION_PATTERNS = frozenset(
    {
        "foreign_config_entry_read",
        "storage_file_access",
        "foreign_hass_data_read",
        "foreign_storage_key",
    }
)

# A deliberate cross-integration read can be acknowledged in source with
#     # ha-soc-allow: <pattern_id> <reason>
# on the flagged line or the line directly above it. The finding is still
# produced and stored (an acknowledgment must be visible in the table, never
# a silent skip) but is marked acknowledged and does not open a Repairs
# issue. The marker is only honored for the four extraction rules, must name
# the exact pattern id, and must carry a non-empty reason.
_ALLOW_MARKER_RE = re.compile(r"#\s*ha-soc-allow:\s*([a-z0-9_]+)\s+(\S.*?)\s*$")


def _apply_allow_marker(hit: dict[str, Any], lines: list[str]) -> None:
    """Mark an extraction-rule hit acknowledged when its line (or the line
    above) carries a matching ha-soc-allow marker. Text-based on purpose:
    the marker must be greppable and reviewable exactly where the flagged
    code is, so a comment-shaped string literal on the same line would also
    satisfy it, which is acceptable for an advisory mechanism.
    """
    if hit["pattern"] not in _EXTRACTION_PATTERNS:
        return
    lineno = hit["lineno"]
    for idx in (lineno - 1, lineno - 2):
        if 0 <= idx < len(lines):
            m = _ALLOW_MARKER_RE.search(lines[idx])
            if m and m.group(1) == hit["pattern"]:
                hit["acknowledged"] = True
                hit["acknowledged_reason"] = m.group(2)[:200]
                return
    hit["acknowledged"] = False


def _is_own_namespace(name: str, domain: str) -> bool:
    """True when a storage key or path component sits inside the scanned
    integration's own namespace: the domain itself, or the domain followed
    by a separator (``ha_soc.storage``, ``ha_soc_audit``)."""
    if name == domain:
        return True
    return name.startswith(domain) and len(name) > len(domain) and name[len(domain)] in "._-"


def _parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return parents


def _enclosing_function(node: ast.AST, parents: dict[ast.AST, ast.AST], tree: ast.AST) -> ast.AST:
    cur = parents.get(node)
    while cur is not None:
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
        cur = parents.get(cur)
    return tree


def _entry_var_names(scope: ast.AST, call: ast.Call, parents: dict[ast.AST, ast.AST]) -> set[str]:
    """Names bound to individual entries produced by one enumeration call:
    the target of a for loop or comprehension iterating the call directly,
    or iterating a name the call's result was assigned to."""
    assigned: set[str] = set()
    parent = parents.get(call)
    if isinstance(parent, ast.Assign):
        for target in parent.targets:
            if isinstance(target, ast.Name):
                assigned.add(target.id)
    names: set[str] = set()
    for node in ast.walk(scope):
        if isinstance(node, (ast.For, ast.AsyncFor)):
            iters, target = node.iter, node.target
        elif isinstance(node, ast.comprehension):
            iters, target = node.iter, node.target
        else:
            continue
        if iters is call or (isinstance(iters, ast.Name) and iters.id in assigned):
            if isinstance(target, ast.Name):
                names.add(target.id)
    return names


def _unwrap_mapping_exprs(value: ast.AST) -> list[ast.AST]:
    """Expressions that stand for the mapping itself once defaulting and
    grouping are peeled away: ``entry.options or {}`` is the mapping with a
    default, and a tuple of such expressions is a sequence of them."""
    if isinstance(value, ast.BoolOp):
        out: list[ast.AST] = []
        for part in value.values:
            out.extend(_unwrap_mapping_exprs(part))
        return out
    if isinstance(value, ast.Tuple):
        out = []
        for part in value.elts:
            out.extend(_unwrap_mapping_exprs(part))
        return out
    return [value]


def _entry_mapping_alias_nodes(
    scope: ast.AST, entry_names: set[str]
) -> tuple[set[str], set[ast.AST]]:
    """Follow one level of aliasing: ``options = entry.options or {}`` and
    ``for mapping in (entry.options or {}, entry.data or {})`` both bind a
    name to the entry's mapping, so uses of that name must be analyzed like
    uses of ``entry.options`` itself. Returns the alias names and the
    attribute nodes consumed by those bindings (which must not themselves
    count as whole-mapping consumption)."""
    aliases: set[str] = set()
    defining_attrs: set[ast.AST] = set()

    def _bind(value: ast.AST, targets: list[ast.AST]) -> None:
        matched = [
            cand
            for cand in _unwrap_mapping_exprs(value)
            if isinstance(cand, ast.Attribute)
            and cand.attr in ("data", "options")
            and isinstance(cand.value, ast.Name)
            and cand.value.id in entry_names
        ]
        if not matched:
            return
        defining_attrs.update(matched)
        for target in targets:
            if isinstance(target, ast.Name):
                aliases.add(target.id)

    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            _bind(node.value, node.targets)
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            # Only a tuple iteration binds the target to the mappings
            # themselves; iterating a bare mapping yields its keys and is
            # classified as consumption by _mapping_use_fires instead.
            if isinstance(node.iter, ast.Tuple):
                _bind(node.iter, [node.target])
    return aliases, defining_attrs


def _subscript_key_fires(key_node: ast.AST, kind: str, domain: str) -> bool:
    """Whether reading one key of a foreign entry's data/options mapping is
    extraction-shaped. A non-literal key is statically invisible and never
    fires. An indiscriminate (no-domain) enumeration fires on any literal
    key outside INTEGRATION_LOCATOR_KEYS; a targeted (foreign-literal)
    enumeration fires only on credential-shaped keys, because a visible,
    auditable read of one named domain's non-secret fields is how
    legitimate cross-integration features (hygiene checks, enrichment) are
    built."""
    if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
        return False
    key = key_node.value
    if kind == "no_domain":
        return key not in INTEGRATION_LOCATOR_KEYS
    return bool(_SENSITIVE_ARG_RE.search(key))


# Callables that flatten a whole mapping into an inspectable or printable
# value. Passing a foreign entry's data/options to one of these (or logging
# it) is the canonical extraction shape; passing it to any other callable
# has a statically unknowable effect, and the rule stays quiet there rather
# than flag every helper function that takes a mapping.
_MAPPING_CONSUMING_CALLS = frozenset(
    {"str", "repr", "format", "dict", "list", "tuple", "set", "sorted", "iter", "dumps", "dump", "pformat"}
) | _LOGGER_METHOD_NAMES


def _mapping_use_fires(
    node: ast.AST, parents: dict[ast.AST, ast.AST], kind: str, domain: str
) -> bool:
    """Whether one use of a foreign entry's data/options mapping (or an
    alias of it) is extraction-shaped. Exempt uses: subscript or ``.get``
    with a key that passes _subscript_key_fires, membership tests (``key in
    entry.data`` reveals key presence, not values), and passing the mapping
    to a callable outside _MAPPING_CONSUMING_CALLS (its effect is
    statically unknowable). Every other use (f-string interpolation,
    ``str()``/``dict()``/``json.dumps()``, logging it, iterating it,
    ``.items()``/``.values()``, returning or re-assigning the raw mapping
    beyond one recognized alias) consumes the mapping wholesale and
    fires."""
    # `entry.data or {}` is still the mapping, just with a default: climb
    # past defaulting BoolOps so the classification looks at what the
    # defaulted expression is used FOR.
    parent = parents.get(node)
    while isinstance(parent, ast.BoolOp):
        node = parent
        parent = parents.get(node)
    if isinstance(parent, ast.Subscript) and parent.value is node:
        return _subscript_key_fires(parent.slice, kind, domain)
    if isinstance(parent, ast.Attribute) and parent.value is node and parent.attr == "get":
        grandparent = parents.get(parent)
        if isinstance(grandparent, ast.Call) and grandparent.func is parent:
            if grandparent.args:
                return _subscript_key_fires(grandparent.args[0], kind, domain)
            return False
    if isinstance(parent, ast.Compare) and node in parent.comparators:
        if all(isinstance(op, (ast.In, ast.NotIn)) for op in parent.ops):
            return False
    if isinstance(parent, ast.Call) and node is not parent.func:
        callee = parent.func
        name = callee.attr if isinstance(callee, ast.Attribute) else getattr(callee, "id", None)
        return name in _MAPPING_CONSUMING_CALLS
    return True


# -- Rule 7 (SEC-5 a): foreign config entry read -----------------------------
def _rule_foreign_config_entry_read(
    tree: ast.AST, lines: list[str], domain: str
) -> list[dict[str, Any]]:
    """Enumeration of other integrations' config entries combined with an
    extraction-shaped read of their ``data``/``options`` in the same scope.

    Exact semantics: a ``config_entries.async_entries()`` or
    ``async_loaded_entries()`` call qualifies when it passes no domain
    (indiscriminate) or a string-literal domain different from the scanned
    integration's own (targeted). It fires only when, in the enclosing
    function (the whole module for a top-level call), a variable bound to
    the enumerated entries has its ``.data`` or ``.options`` consumed in an
    extraction-shaped way per _mapping_use_fires: wholesale (f-string,
    ``str()``/``dict()``/``json.dumps()``, logging, iteration, assignment
    onward beyond the one-level aliasing _entry_mapping_alias_nodes
    recognizes), or via a literal key that is outside
    INTEGRATION_LOCATOR_KEYS for an indiscriminate call, or
    credential-shaped for a targeted call. Bare enumeration for
    ``entry.domain``/``entry.state`` never fires, and a call whose domain
    argument is a variable never fires.

    Obvious false positive: a function that enumerates entries for their
    domains and, in the same scope, legitimately reads a non-locator field
    of its own or a cooperating integration's entry.

    Evasion: a domain held in a variable, a key held in a variable, or the
    mapping (or the entry object) passed to a helper function whose body
    lives in another scope is invisible to this rule.
    """
    parents = _parent_map(tree)
    hits: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr not in _ENTRY_ENUM_METHODS:
            continue
        owner = _dotted_name(node.func.value)
        if owner is None or not (owner == "config_entries" or owner.endswith(".config_entries")):
            continue
        if not node.args and not node.keywords:
            kind = "no_domain"
        elif (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and node.args[0].value != domain
        ):
            kind = "foreign_literal"
        else:
            continue

        scope = _enclosing_function(node, parents, tree)
        entry_names = _entry_var_names(scope, node, parents)
        if not entry_names:
            continue
        aliases, defining_attrs = _entry_mapping_alias_nodes(scope, entry_names)

        fired = False
        for use in ast.walk(scope):
            if (
                isinstance(use, ast.Attribute)
                and use.attr in ("data", "options")
                and isinstance(use.value, ast.Name)
                and use.value.id in entry_names
                and use not in defining_attrs
            ):
                fired = _mapping_use_fires(use, parents, kind, domain)
            elif (
                isinstance(use, ast.Name)
                and isinstance(use.ctx, ast.Load)
                and use.id in aliases
            ):
                fired = _mapping_use_fires(use, parents, kind, domain)
            if fired:
                break
        if fired and node.lineno not in seen:
            seen.add(node.lineno)
            hits.append(_hit(node.lineno, lines, "foreign_config_entry_read", "CWE-200", "medium"))
    return hits


def _is_file_access_call(node: ast.Call) -> bool:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id in ("open", "Path")
    if isinstance(func, ast.Attribute):
        if func.attr in _FILE_ACCESS_ATTRS or func.attr == "Path":
            return True
        dotted = _dotted_name(func)
        if dotted is None:
            return False
        return dotted == "os.path.join" or dotted.endswith(".path.join") or dotted.endswith("config.path")
    return False


def _call_string_literals(node: ast.Call) -> list[str]:
    """String literals anywhere inside the call's arguments, in source
    order, so a nested path-building call contributes its components to the
    outer call's view of the target."""
    found: list[ast.Constant] = []
    for arg in list(node.args) + [kw.value for kw in node.keywords]:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                found.append(sub)
    found.sort(key=lambda c: (c.lineno, c.col_offset))
    return [c.value for c in found]


# -- Rule 8 (SEC-5 b): raw .storage / secrets.yaml file access ---------------
def _rule_storage_file_access(
    tree: ast.AST, lines: list[str], domain: str
) -> list[dict[str, Any]]:
    """File access whose statically visible target is ``secrets.yaml`` or
    another namespace under ``.storage/``.

    Exact semantics: only calls that touch files or build storage paths are
    inspected (``open``, ``Path(...)``, ``.read_text``/``.read_bytes``/
    ``.write_text``/``.write_bytes``/``.open`` methods, ``os.path.join``,
    ``hass.config.path``). Within such a call, any string literal
    containing ``secrets.yaml`` fires unconditionally: that file holds the
    user's YAML secrets and no integration owns a namespace inside it. A
    literal whose path component is exactly ``.storage`` fires only when
    the following component (in the same literal, or the next literal
    argument of the same call) is visible and does not start with the
    scanned integration's own domain: ``.storage/`` files are private Store
    payloads, and an integration's own subdirectory or key prefix there is
    the one legitimate target. When the following component is not a
    literal, the target cannot be determined and nothing fires.

    Obvious false positive: a filename that merely contains the substring
    ``secrets.yaml`` (for example ``my_secrets.yaml``), or a legitimately
    cooperating tool (a backup or migration helper) reading storage it
    documents.

    Evasion: a path assembled from variables, imported constants, or
    f-strings carries no visible literal and is invisible to this rule, as
    is any file API not in the inspected set.
    """
    hits: list[dict[str, Any]] = []
    seen: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_file_access_call(node):
            continue
        literals = _call_string_literals(node)
        fired = False
        for idx, lit in enumerate(literals):
            if "secrets.yaml" in lit:
                fired = True
                break
            components = [c for c in lit.split("/") if c]
            if ".storage" not in components:
                continue
            after = components[components.index(".storage") + 1 :]
            if not after and idx + 1 < len(literals):
                next_components = [c for c in literals[idx + 1].split("/") if c]
                after = next_components[:1]
            if after and not _is_own_namespace(after[0], domain):
                fired = True
                break
        if fired and node.lineno not in seen:
            seen.add(node.lineno)
            hits.append(_hit(node.lineno, lines, "storage_file_access", "CWE-200", "high"))
    return hits


# -- Rule 9 (SEC-5 c): foreign hass.data read --------------------------------
def _rule_foreign_hass_data_read(
    tree: ast.AST, lines: list[str], domain: str
) -> list[dict[str, Any]]:
    """``hass.data[...]`` subscripted with a string literal that looks like
    another integration's domain.

    Exact semantics: fires on a subscript of an attribute named ``data``
    whose base's final dotted component is ``hass`` or ``_hass`` (``hass``,
    ``self.hass``, ``coordinator.hass``), with a string-literal key that
    (1) is a valid integration domain per core's own ``valid_domain``,
    (2) is not the scanned integration's own domain or a key prefixed with
    it (``mydomain_config`` is its own namespace), and (3) is not one of
    the core bootstrap/helper HassKey names in _CORE_HASS_DATA_KEYS (those
    reads reach core infrastructure, not another integration; the list was
    collected from core 2026.2.3 and a domain colliding with it is a
    documented false negative). Reads and writes both fire, since planting
    data in another domain's slot is cross-integration tampering.

    Obvious false positive: an integration reading a core component's
    published hass.data slot, or a cooperating family of integrations
    sharing one literal key by documented agreement.

    Evasion: a key held in a variable or imported constant (the way most
    code spells ``hass.data[DOMAIN]``), an f-string key, or ``.get()`` on
    hass.data instead of a subscript is invisible to this rule.
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Subscript):
            continue
        value = node.value
        if not (isinstance(value, ast.Attribute) and value.attr == "data"):
            continue
        base = _dotted_name(value.value)
        if base is None or base.rsplit(".", 1)[-1] not in ("hass", "_hass"):
            continue
        key_node = node.slice
        if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
            continue
        key = key_node.value
        if not valid_domain(key):
            continue
        if _is_own_namespace(key, domain) or key in _CORE_HASS_DATA_KEYS:
            continue
        hits.append(_hit(node.lineno, lines, "foreign_hass_data_read", "CWE-200", "medium"))
    return hits


# -- Rule 10 (SEC-5 d): Store built on a foreign storage key -----------------
def _rule_foreign_storage_key(
    tree: ast.AST, lines: list[str], domain: str
) -> list[dict[str, Any]]:
    """``Store(...)`` constructed with a storage-key literal outside the
    scanned integration's own namespace.

    Exact semantics: fires on calls whose callee is named ``Store`` (bare,
    dotted like ``storage.Store``, or the subscripted generic form
    ``Store[...]``) where the key argument (third positional, or the
    ``key`` keyword, matching core's ``Store(hass, version, key)``
    signature) is a string literal whose first dotted component is not the
    scanned domain or a domain-prefixed name. ``Store(hass, 1,
    "ha_soc.secrets")`` in ha_soc passes; ``Store(hass, 1,
    "core.config_entries")`` anywhere else opens another party's private
    storage file through the helper that owns its format.

    Obvious false positive: an integration that deliberately shares one
    storage namespace across a documented family of related domains, or a
    brand-prefixed key that predates the integration's current domain name.

    Evasion: a subclass of Store under another name, or a key held in a
    variable, constant, or f-string, is invisible to this rule.
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # The generic form Store[T](...) parses as a Subscript callee.
        if isinstance(func, ast.Subscript):
            func = func.value
        if isinstance(func, ast.Name):
            callee = func.id
        elif isinstance(func, ast.Attribute):
            callee = func.attr
        else:
            continue
        if callee != "Store":
            continue
        key_node: ast.AST | None = node.args[2] if len(node.args) >= 3 else None
        for kw in node.keywords:
            if kw.arg == "key":
                key_node = kw.value
        if not (isinstance(key_node, ast.Constant) and isinstance(key_node.value, str)):
            continue
        first_component = key_node.value.split(".", 1)[0]
        if _is_own_namespace(first_component, domain):
            continue
        hits.append(_hit(node.lineno, lines, "foreign_storage_key", "CWE-200", "high"))
    return hits


_RULES: list[Callable[[ast.AST, list[str]], list[dict[str, Any]]]] = [
    _rule_tls_verification_disabled,
    _rule_shell_injection_risk,
    _rule_eval_exec_use,
    _rule_insecure_deserialization,
    _rule_hardcoded_credential,
    _rule_sensitive_data_logged,
]

# Rules that need to know which integration is being scanned, so "foreign"
# and "own namespace" have a referent. Kept in a separate registry to leave
# the original two-argument rule signature (and its direct-call tests)
# untouched.
_DOMAIN_RULES: list[Callable[[ast.AST, list[str], str], list[dict[str, Any]]]] = [
    _rule_foreign_config_entry_read,
    _rule_storage_file_access,
    _rule_foreign_hass_data_read,
    _rule_foreign_storage_key,
]


def _finding_from_hit(hit: dict[str, Any], rel_path: str, domain: str, now: str) -> dict[str, Any]:
    digest_src = f"{rel_path}:{hit['lineno']}:{hit['pattern']}"
    digest = hashlib.sha256(digest_src.encode()).hexdigest()[:16]
    confidence = hit["confidence"]
    finding = {
        "id": f"{domain}:{digest}",
        "domain": domain,
        "file": rel_path,
        "line": hit["lineno"],
        "snippet": hit["snippet"],
        "pattern": hit["pattern"],
        "cwe": hit["cwe"],
        "confidence": confidence,
        "severity": _SEVERITY_BY_CONFIDENCE.get(confidence, "info"),
        "first_seen": now,
        "last_seen": now,
        "status": "new",
    }
    # Only the extraction rules carry the acknowledgment mechanism; the
    # fields are copied through so an acknowledged read is visible in the
    # findings table rather than silently absent from it.
    if "acknowledged" in hit:
        finding["acknowledged"] = hit["acknowledged"]
        if hit.get("acknowledged_reason"):
            finding["acknowledged_reason"] = hit["acknowledged_reason"]
    return finding


def scan_directory_report(directory: Path, domain: str) -> dict[str, Any]:
    """Run every rule against one directory tree and report both the
    findings and the coverage actually achieved (work plan item 4.8).
    Blocking (file I/O and ``ast.parse``): production callers go through
    IntegrationScanner, which runs this in an executor job.

    The returned dict carries:

    - ``findings``: the finding dicts, exactly as before.
    - ``coverage``: {scanned_files, skipped_oversize, skipped_over_cap,
      parse_failures, scanned_at} - what this pass really looked at, so a
      domain that was never scanned (or only partially scanned) is never
      rendered as a clean "0 findings".
    - ``scanned_paths``: relative paths of the files whose rules actually
      ran, the only files findings reconciliation may treat as evaluated.
    - ``candidate_paths``: every .py file that exists in the tree, so a
      finding whose file has been deleted outright can also be resolved.
    """
    all_files = sorted(directory.rglob("*.py"))

    sized_files: list[Path] = []
    skipped_too_large = 0
    for path in all_files:
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_SIZE_BYTES:
            skipped_too_large += 1
            continue
        sized_files.append((size, path))

    skipped_over_cap = 0
    if len(sized_files) > MAX_FILES_PER_SCAN:
        # Deterministic cap selection by size DESCENDING with the path as
        # the tie-break (work plan item 4.8): under the old
        # first-N-by-path selection, the large modules that most need
        # scanning were exactly the ones a padded directory could push
        # past the cap. The selected set is then scanned in path order so
        # output stays stable and diffable.
        skipped_over_cap = len(sized_files) - MAX_FILES_PER_SCAN
        sized_files.sort(key=lambda item: (-item[0], item[1]))
        sized_files = sized_files[:MAX_FILES_PER_SCAN]
    selected_files = sorted(path for _size, path in sized_files)

    # Coverage must never be silently under-reported: any file this scan
    # did not look at is logged, not just dropped.
    if skipped_too_large or skipped_over_cap:
        _LOGGER.warning(
            "HA SOC scanner: %s of %s file(s) in %s were skipped (%s over the "
            "%s KB size limit, %s beyond the %s-file scan cap); coverage for "
            "domain %s is partial this pass",
            skipped_too_large + skipped_over_cap,
            len(all_files),
            directory,
            skipped_too_large,
            MAX_FILE_SIZE_BYTES // 1024,
            skipped_over_cap,
            MAX_FILES_PER_SCAN,
            domain,
        )

    now = dt_util.utcnow().isoformat()
    findings: list[dict[str, Any]] = []
    scanned_paths: list[str] = []
    parse_failures = 0
    for path in selected_files:
        rel_path = str(path.relative_to(directory))
        try:
            # The rule loop lives INSIDE the per-file try (work plan item
            # 4.8): a rule blowing up on one pathological file (a
            # recursion bomb that parses but breaks an AST walk, a
            # MemoryError from a giant expression) must cost only that
            # file's coverage, never the rest of the integration's scan.
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            lines = source.splitlines()
            file_findings: list[dict[str, Any]] = []
            for rule in _RULES:
                for hit in rule(tree, lines):
                    file_findings.append(_finding_from_hit(hit, rel_path, domain, now))
            for domain_rule in _DOMAIN_RULES:
                for hit in domain_rule(tree, lines, domain):
                    _apply_allow_marker(hit, lines)
                    file_findings.append(_finding_from_hit(hit, rel_path, domain, now))
        except (
            OSError,
            SyntaxError,
            UnicodeDecodeError,
            ValueError,
            RecursionError,
            MemoryError,
        ) as err:
            # One bad file (binary fixture, non-UTF-8 source, a syntax
            # error in code that HA itself may never load, or a crafted
            # file whose deeply-nested-but-trivial expressions drive
            # CPython's parser into RecursionError/MemoryError) must not
            # abort the rest of this integration's scan; it is counted as
            # a parse failure so coverage stays honest.
            parse_failures += 1
            _LOGGER.debug(
                "HA SOC scanner: skipping %s in domain %s (%s)",
                path,
                domain,
                err.__class__.__name__,
            )
            continue
        findings.extend(file_findings)
        scanned_paths.append(rel_path)

    return {
        "findings": findings,
        "coverage": {
            "scanned_files": len(scanned_paths),
            "skipped_oversize": skipped_too_large,
            "skipped_over_cap": skipped_over_cap,
            "parse_failures": parse_failures,
            "scanned_at": now,
        },
        "scanned_paths": set(scanned_paths),
        "candidate_paths": {str(path.relative_to(directory)) for path in all_files},
    }


def scan_directory(directory: Path, domain: str) -> list[dict[str, Any]]:
    """Findings-only wrapper over scan_directory_report. Module-level so
    the self-scan test can point it at ``custom_components/ha_soc``
    without a running hass."""
    return scan_directory_report(directory, domain)["findings"]


class IntegrationScanner:
    """Runs the rule set above against one integration's files on disk.

    Static analysis only: `ast.parse`/`re` against source text at rest. This
    class never imports or executes a scanned integration's code, and never
    makes a network call of any kind.
    """

    def __init__(self, hass: HomeAssistant, store: HaSocData) -> None:
        self.hass = hass
        self._store = store
        self._unsub_config_entry_changed: Callable[[], None] | None = None

    def async_start(self, hass: HomeAssistant) -> None:
        self._unsub_config_entry_changed = async_dispatcher_connect(
            hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._on_config_entry_changed
        )

    def async_stop(self) -> None:
        if self._unsub_config_entry_changed is not None:
            self._unsub_config_entry_changed()
            self._unsub_config_entry_changed = None

    def _on_config_entry_changed(self, change: ConfigEntryChange, entry: ConfigEntry) -> None:
        if change != ConfigEntryChange.ADDED:
            return
        # The operator's scanner toggle governs EVERY scan path, the
        # on-install one included (work plan item 4.8) - the weekly sweep
        # already honored it and this trigger silently did not.
        if not self._store.settings.get("scanner_enabled", True):
            return
        # Newly added integration: scan it once, off the event loop, rather
        # than waiting for the next weekly sweep.
        self.hass.async_create_task(self._async_scan_on_install(entry.domain))

    async def _async_scan_on_install(self, domain: str) -> None:
        """Wrapper for the fire-and-forget on-install scan task: without this,
        a raise inside async_scan_integration would surface only as a silent
        unretrieved task exception, so log-and-continue instead."""
        try:
            await self.async_scan_integration(domain)
        except Exception:  # noqa: BLE001 - a failed on-install scan must not go unlogged
            _LOGGER.exception("HA SOC scanner: on-install scan of domain %s failed", domain)

    def _scan_dir(self, directory: Path, domain: str) -> dict[str, Any]:
        """Blocking: file I/O and `ast.parse`. Always run via an executor job."""
        return scan_directory_report(directory, domain)

    def _coverage_table(self) -> dict[str, dict[str, Any]]:
        """domain -> coverage record for the domain's latest completed
        scan (work plan item 4.8). setdefault rather than a store.py
        schema change: unknown top-level keys survive the store's
        load-time merge, and the sibling-owned StoreData TypedDict can
        pick the key up in its own pass."""
        return self._store.data.setdefault("scanner_coverage", {})  # type: ignore[typeddict-item]

    def listing_payload(self) -> dict[str, Any]:
        """The Scanner tab's listing: findings plus per-domain coverage,
        so the frontend can render "not scanned" for a domain with no
        coverage record instead of an implied clean zero (work plan item
        4.8). The WS handler is the intended caller."""
        return {
            "findings": list(self._store.data["scanner_findings"].values()),
            "coverage": dict(self._coverage_table()),
        }

    async def async_scan_integration(self, domain: str) -> list[dict[str, Any]]:
        integration = await async_get_integration(self.hass, domain)
        report = await self.hass.async_add_executor_job(self._scan_dir, integration.file_path, domain)
        findings = report["findings"]

        table = self._store.data["scanner_findings"]
        previously_known_ids = {fid for fid, existing in table.items() if existing.get("domain") == domain}

        for finding in findings:
            self._store.async_upsert_finding("scanner_findings", finding["id"], dict(finding))

        self._reconcile_domain_findings(domain, report)
        self._coverage_table()[domain] = report["coverage"]
        self._store.async_schedule_save()

        # An acknowledged extraction finding is a deliberate, documented
        # read (see _apply_allow_marker); it stays visible in the findings
        # table but must not open a Repairs issue, because a permanent alarm
        # on a reviewed pattern trains alarm fatigue.
        new_notable = [
            f
            for f in findings
            if f["id"] not in previously_known_ids
            and f["severity"] in ("high", "medium")
            and not f.get("acknowledged")
        ]
        if new_notable:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                f"scanner_{domain}",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="scanner_finding",
                translation_placeholders={"domain": domain, "count": str(len(new_notable))},
            )
        elif not findings:
            # Nothing found this pass. Harmless no-op if no issue was open;
            # clears a stale one if the integration's code was fixed since.
            ir.async_delete_issue(self.hass, DOMAIN, f"scanner_{domain}")

        return findings

    def _reconcile_domain_findings(self, domain: str, report: dict[str, Any]) -> None:
        """Move findings absent from this rescan to resolved with
        resolved_reason "not_found_on_rescan" (work plan item 4.8).

        Fail-open guard: only a finding whose file was actually scanned
        this pass (or no longer exists at all) may be resolved - a file
        skipped for size, the file cap, or a parse failure was NOT
        evaluated, and absence from an unevaluated file is not evidence
        the pattern is gone. A dismissed finding whose pattern is gone
        from a fully scanned file also moves to resolved: "the code no
        longer contains this" is the more accurate closed state than "an
        analyst chose to ignore it".
        """
        current_ids = {f["id"] for f in report["findings"]}
        scanned_paths: set[str] = report["scanned_paths"]
        candidate_paths: set[str] = report["candidate_paths"]
        now = dt_util.utcnow().isoformat()
        for finding_id, finding in list(self._store.data["scanner_findings"].items()):
            if finding.get("domain") != domain or finding_id in current_ids:
                continue
            if finding.get("status") == "resolved":
                continue
            file_path = finding.get("file")
            if file_path in scanned_paths or file_path not in candidate_paths:
                self._store.async_set_finding_status(
                    "scanner_findings", finding_id, "resolved",
                    by_user_id=None, note=None, at=now,
                )
                finding["resolved_reason"] = "not_found_on_rescan"

    async def async_scan_all(self) -> dict[str, list[dict[str, Any]]]:
        domains = {entry.domain for entry in self.hass.config_entries.async_entries()}
        results: dict[str, list[dict[str, Any]]] = {}
        for domain in domains:
            try:
                results[domain] = await self.async_scan_integration(domain)
            except Exception:  # noqa: BLE001 - one domain's failure must not abort the whole sweep
                _LOGGER.exception("HA SOC scanner: scan of domain %s failed", domain)
            # Weekly sweep, not latency sensitive — but a large install can
            # have hundreds of integrations, and each one runs a blocking
            # executor job; yield so the event loop isn't starved between them.
            await asyncio.sleep(0)
        return results

    def export_ghsa(self, finding: dict[str, Any]) -> dict[str, Any]:
        """Pure function: shapes one finding into GHSA-like fields. No I/O,
        no submission anywhere — this is for a human to copy into an
        advisory themselves, never an automated disclosure channel.
        """
        pattern_words = finding["pattern"].replace("_", " ")
        return {
            "title": f"{pattern_words.title()} in {finding['domain']}",
            "description": (
                f"HA SOC's integration scanner flagged a potential {pattern_words} "
                f"pattern in {finding['domain']} at {finding['file']}:{finding['line']}.\n\n"
                f"Matched code:\n```python\n{finding['snippet']}\n```\n\n"
                "This is a local, heuristic static-analysis finding — it has not been "
                "confirmed as an exploitable vulnerability, and Home Assistant does not "
                "audit third-party integrations. Review it yourself before taking any "
                "action or contacting the integration's author."
            ),
            "severity": finding["severity"],
            "affected": {
                "ecosystem": "home-assistant-integration",
                "package": finding["domain"],
                "version": "unknown",
            },
            "cwe": finding["cwe"],
            "references": [],
        }
