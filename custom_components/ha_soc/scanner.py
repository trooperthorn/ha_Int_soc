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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.loader import async_get_integration

from .const import DOMAIN
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
_SENSITIVE_ARG_RE = re.compile(
    r"(token|password|secret|api[_-]?key|access[_-]?token|refresh[_-]?token)", re.IGNORECASE
)
_LOGGER_OWNER_RE = re.compile(r"(^|_)(logger|log)$", re.IGNORECASE)

_SUBPROCESS_FUNC_NAMES = {"Popen", "call", "check_call", "check_output", "run"}
_LOGGER_METHOD_NAMES = {"debug", "info", "warning", "error", "exception"}

_SEVERITY_BY_CONFIDENCE = {"high": "high", "medium": "medium", "advisory": "info"}


def _hit(lineno: int, lines: list[str], pattern: str, cwe: str, confidence: str) -> dict[str, Any]:
    raw = lines[lineno - 1] if 0 < lineno <= len(lines) else ""
    return {
        "lineno": lineno,
        "snippet": raw.strip()[:160],
        "pattern": pattern,
        "cwe": cwe,
        "confidence": confidence,
    }


def _dotted_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return None


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


# -- Rule 2: command injection risk -----------------------------------------
def _rule_shell_injection_risk(tree: ast.AST, lines: list[str]) -> list[dict[str, Any]]:
    """`shell=True` alone is not the signal — a hardcoded literal command run
    with `shell=True` is not attacker-controlled. Only flag it alongside an
    argument built from an f-string, concatenation/%-format, or `.format()`:
    that co-condition is what makes an external value's path into the shell
    plausible, and it's the reason this rule needs two things to be true at
    once rather than firing on `shell=True` by itself.
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not _is_subprocess_call(node):
            continue
        shell_true = any(
            kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True
            for kw in node.keywords
        )
        if not shell_true:
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
    """
    hits: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if not (isinstance(value, ast.Constant) and isinstance(value.value, str)):
            continue
        literal = value.value
        if len(literal) < 6 or _PLACEHOLDER_RE.search(literal):
            continue
        for target in node.targets:
            name = _assign_target_name(target)
            if not name or _CONF_CONSTANT_NAME_RE.match(name):
                continue
            if _CREDENTIAL_NAME_RE.search(name):
                hits.append(_hit(node.lineno, lines, "hardcoded_credential", "CWE-798", "medium"))
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


_RULES: list[Callable[[ast.AST, list[str]], list[dict[str, Any]]]] = [
    _rule_tls_verification_disabled,
    _rule_shell_injection_risk,
    _rule_eval_exec_use,
    _rule_insecure_deserialization,
    _rule_hardcoded_credential,
    _rule_sensitive_data_logged,
]


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

    def _scan_dir(self, directory: Path, domain: str) -> list[dict[str, Any]]:
        """Blocking: file I/O and `ast.parse`. Always run via an executor job."""
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
            sized_files.append(path)

        skipped_over_cap = 0
        if len(sized_files) > MAX_FILES_PER_SCAN:
            skipped_over_cap = len(sized_files) - MAX_FILES_PER_SCAN
            sized_files = sized_files[:MAX_FILES_PER_SCAN]

        # Coverage must never be silently under-reported: any file this scan
        # did not look at is logged, not just dropped.
        if skipped_too_large or skipped_over_cap:
            _LOGGER.warning(
                "HA SOC scanner: %s of %s file(s) in %s were skipped (%s over the "
                "%s KB size limit, %s beyond the %s-file scan cap) — coverage for "
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
        for path in sized_files:
            try:
                source = path.read_text(encoding="utf-8")
                tree = ast.parse(source)
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
                # abort the rest of this integration's scan.
                _LOGGER.debug(
                    "HA SOC scanner: skipping %s in domain %s (%s)",
                    path,
                    domain,
                    err.__class__.__name__,
                )
                continue

            lines = source.splitlines()
            rel_path = str(path.relative_to(directory))
            for rule in _RULES:
                for hit in rule(tree, lines):
                    digest_src = f"{rel_path}:{hit['lineno']}:{hit['pattern']}"
                    digest = hashlib.sha256(digest_src.encode()).hexdigest()[:16]
                    confidence = hit["confidence"]
                    findings.append(
                        {
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
                    )
        return findings

    async def async_scan_integration(self, domain: str) -> list[dict[str, Any]]:
        integration = await async_get_integration(self.hass, domain)
        findings = await self.hass.async_add_executor_job(self._scan_dir, integration.file_path, domain)

        table = self._store.data["scanner_findings"]
        previously_known_ids = {fid for fid, existing in table.items() if existing.get("domain") == domain}

        for finding in findings:
            self._store.async_upsert_finding("scanner_findings", finding["id"], dict(finding))

        new_notable = [
            f
            for f in findings
            if f["id"] not in previously_known_ids and f["severity"] in ("high", "medium")
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
