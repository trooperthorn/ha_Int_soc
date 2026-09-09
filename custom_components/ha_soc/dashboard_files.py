"""Dashboard file editing: read and rewrite YAML under <config>/dashboards only.

The allowlist root is a single directory and the operations are read and
overwrite; nothing here creates, renames, or deletes a file, and no path
outside the root is reachable. Scope, the digest-based conflict rule, and
the two-tier validation split are in docs/design.md; the trust boundary and
audit contract are in docs/security.md.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from typing import Any

import yaml

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# The only directory this module will ever touch, relative to the config dir.
DASHBOARDS_DIRNAME = "dashboards"

BACKUP_DIR = os.path.join(".storage", "ha_soc_dashboards")
BACKUP_RETENTION_DAYS = 30

ALLOWED_SUFFIXES = (".yaml", ".yml")
# A dashboard file is hand-written YAML; the largest in the reference set is
# under 100 KiB flattened. The cap keeps a read from pulling an arbitrary blob
# into the event loop and into a WebSocket frame.
MAX_FILE_BYTES = 1024 * 1024
MAX_LISTED_FILES = 500
MAX_RELATIVE_PATH_LEN = 1024
MAX_SEGMENT_LEN = 255

AUDIT_CATEGORY_WRITE = "dashboard_file_write"
AUDIT_CATEGORY_DENIED = "dashboard_file_denied"

# Coded refusals; the panel branches on these, so they are part of the protocol.
ERR_DISABLED = "dashboard_edit_disabled"
ERR_NOT_ALLOWED = "not_allowed"
ERR_NOT_FOUND = "not_found"
ERR_TOO_LARGE = "too_large"
ERR_CONFLICT = "conflict"
ERR_INVALID_YAML = "invalid_yaml"
ERR_WRITE_FAILED = "write_failed"


# Serializes HA SOC's own writers per file; core's config-editor locks are not importable.
_FILE_LOCKS: dict[str, asyncio.Lock] = {}


def _lock_for(path: str) -> asyncio.Lock:
    lock = _FILE_LOCKS.get(path)
    if lock is None:
        lock = asyncio.Lock()
        _FILE_LOCKS[path] = lock
    return lock


class DashboardFileError(Exception):
    """A refusal carrying the code the panel branches on."""

    def __init__(self, code: str, message: str, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.extra = extra or {}


def root_path(hass: HomeAssistant) -> str:
    """Absolute path of the one editable directory."""
    return hass.config.path(DASHBOARDS_DIRNAME)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _check_relative(relative: str) -> str:
    """Validate a client-supplied relative path and return it in posix form.

    Rejects absolute paths, drive letters, backslashes, empty or dot segments,
    control characters, and any suffix that is not .yaml/.yml. Containment is
    re-checked against the resolved path in :func:`_resolve`; this is the
    cheap, obvious half of the gate, not the whole of it.
    """
    if not isinstance(relative, str) or not relative:
        raise DashboardFileError(ERR_NOT_ALLOWED, "A dashboard file path is required")
    if len(relative) > MAX_RELATIVE_PATH_LEN:
        raise DashboardFileError(ERR_NOT_ALLOWED, "Path is too long")
    if "\x00" in relative or any(ord(char) < 32 for char in relative):
        raise DashboardFileError(ERR_NOT_ALLOWED, "Path contains control characters")
    if "\\" in relative:
        raise DashboardFileError(ERR_NOT_ALLOWED, "Path must use / as its separator")
    if relative.startswith("/") or os.path.isabs(relative) or ":" in relative:
        raise DashboardFileError(ERR_NOT_ALLOWED, "Path must be relative to the dashboards folder")

    segments = relative.split("/")
    for segment in segments:
        if not segment or segment in (".", ".."):
            raise DashboardFileError(ERR_NOT_ALLOWED, "Path may not contain empty or . segments")
        if len(segment) > MAX_SEGMENT_LEN:
            raise DashboardFileError(ERR_NOT_ALLOWED, "Path segment is too long")

    if not segments[-1].lower().endswith(ALLOWED_SUFFIXES):
        raise DashboardFileError(ERR_NOT_ALLOWED, "Only .yaml and .yml files can be edited")
    return "/".join(segments)


def _resolve(hass: HomeAssistant, relative: str) -> str:
    """Return the absolute path for a validated relative path, or refuse.

    The decisive check is that the fully resolved path still sits under the
    resolved root, which is what makes a symlink pointing out of the folder
    unusable regardless of how the relative path was spelled.
    """
    relative = _check_relative(relative)
    root = root_path(hass)
    real_root = os.path.realpath(root)
    candidate = os.path.join(root, *relative.split("/"))
    real_candidate = os.path.realpath(candidate)
    if real_candidate != real_root and not real_candidate.startswith(real_root + os.sep):
        raise DashboardFileError(ERR_NOT_ALLOWED, "Path escapes the dashboards folder")
    return candidate


def _relative_of(root: str, path: str) -> str:
    return os.path.relpath(path, root).replace(os.sep, "/")


def _list_sync(root: str) -> list[dict[str, Any]]:
    """Walk the dashboards folder; sync, executor-only.

    Symlinks are not followed and any entry whose resolved path leaves the
    folder is skipped rather than reported, so the list never advertises a
    file the read and write paths would refuse.
    """
    if not os.path.isdir(root):
        return []
    real_root = os.path.realpath(root)
    files: list[dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(name for name in dirnames if not name.startswith("."))
        for name in sorted(filenames):
            if name.startswith(".") or not name.lower().endswith(ALLOWED_SUFFIXES):
                continue
            full = os.path.join(dirpath, name)
            real_full = os.path.realpath(full)
            if not real_full.startswith(real_root + os.sep):
                continue
            try:
                stat = os.stat(full, follow_symlinks=False)
            except OSError:
                continue
            files.append(
                {
                    "path": _relative_of(root, full),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "too_large": stat.st_size > MAX_FILE_BYTES,
                }
            )
            if len(files) >= MAX_LISTED_FILES:
                return files
    return files


async def async_list_files(hass: HomeAssistant) -> dict[str, Any]:
    """Every editable dashboard file, relative to the dashboards folder."""
    root = root_path(hass)
    files = await hass.async_add_executor_job(_list_sync, root)
    exists = await hass.async_add_executor_job(os.path.isdir, root)
    return {
        "root": DASHBOARDS_DIRNAME,
        "root_exists": exists,
        "truncated": len(files) >= MAX_LISTED_FILES,
        "max_bytes": MAX_FILE_BYTES,
        "files": files,
    }


def _read_sync(path: str) -> str:
    stat = os.stat(path, follow_symlinks=False)
    if not os.path.isfile(path):
        raise DashboardFileError(ERR_NOT_FOUND, "Not a regular file")
    if stat.st_size > MAX_FILE_BYTES:
        raise DashboardFileError(ERR_TOO_LARGE, "File is larger than the edit limit")
    with open(path, encoding="utf-8") as file:
        return file.read()


async def async_read_file(hass: HomeAssistant, relative: str) -> dict[str, Any]:
    """The file's text plus the digest a later write must present."""
    path = _resolve(hass, relative)
    try:
        content = await hass.async_add_executor_job(_read_sync, path)
    except FileNotFoundError:
        raise DashboardFileError(ERR_NOT_FOUND, "File not found") from None
    except UnicodeDecodeError:
        raise DashboardFileError(ERR_NOT_ALLOWED, "File is not UTF-8 text") from None
    except OSError as err:
        raise DashboardFileError(ERR_NOT_FOUND, f"File could not be read: {err}") from err
    return {
        "path": _check_relative(relative),
        "content": content,
        "sha256": _sha256(content),
    }


class _TagTolerantLoader(yaml.SafeLoader):
    """SafeLoader that parses Home Assistant's tags without resolving them.

    !include and !secret are what a dashboards folder is built from, and
    resolving them here would mean reading files outside the folder. Keeping
    them opaque checks the syntax, which is the part an editor can check
    honestly, and leaves the semantics to Home Assistant's own loader.
    """


def _opaque_tag(loader: yaml.Loader, suffix: str, node: yaml.Node) -> None:
    return None


_TagTolerantLoader.add_multi_constructor("!", _opaque_tag)


def _diagnostic(message: str, mark: Any) -> dict[str, Any]:
    line = getattr(mark, "line", None)
    column = getattr(mark, "column", None)
    return {
        "message": message,
        # yaml marks are zero-based; editors count from one.
        "line": None if line is None else line + 1,
        "column": None if column is None else column + 1,
    }


def _duplicate_key_warnings(content: str) -> list[dict[str, Any]]:
    """Duplicate mapping keys, reported the way Home Assistant treats them.

    annotatedyaml (the loader core delegates to) logs a warning and keeps the
    last value rather than failing, so this is a warning here too; calling it
    an error would refuse a file Home Assistant would happily load.
    """
    warnings: list[dict[str, Any]] = []
    try:
        for node in yaml.compose_all(content, Loader=_TagTolerantLoader):
            warnings.extend(_duplicate_keys_in_node(node))
    except yaml.YAMLError:
        # The syntax pass already reported this; nothing to add.
        return []
    return warnings


def _duplicate_keys_in_node(node: yaml.Node) -> list[dict[str, Any]]:
    warnings: list[dict[str, Any]] = []
    if isinstance(node, yaml.MappingNode):
        seen: dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = getattr(key_node, "value", None)
            if isinstance(key, str):
                if key in seen:
                    warnings.append(
                        _diagnostic(
                            f'Duplicate key "{key}"; Home Assistant keeps the last one',
                            key_node.start_mark,
                        )
                    )
                seen[key] = key_node
            warnings.extend(_duplicate_keys_in_node(value_node))
    elif isinstance(node, yaml.SequenceNode):
        for child in node.value:
            warnings.extend(_duplicate_keys_in_node(child))
    return warnings


def _missing_include_warnings(hass: HomeAssistant, relative: str, content: str) -> list[dict[str, Any]]:
    """!include targets that do not resolve to a file inside the folder.

    Advisory only. The target is resolved the way Home Assistant resolves it,
    relative to the including file, and a target outside the dashboards folder
    is reported as such rather than checked, because this module has no
    business stat-ing the rest of the config directory.
    """
    warnings: list[dict[str, Any]] = []
    root = root_path(hass)
    real_root = os.path.realpath(root)
    base = os.path.dirname(os.path.join(root, *relative.split("/")))
    try:
        nodes = list(yaml.compose_all(content, Loader=_TagTolerantLoader))
    except yaml.YAMLError:
        return []
    for node in nodes:
        for scalar in _iter_scalar_nodes(node):
            if scalar.tag not in ("!include", "!include_dir_list", "!include_dir_merge_list",
                                  "!include_dir_named", "!include_dir_merge_named"):
                continue
            target = str(scalar.value)
            resolved = os.path.realpath(os.path.join(base, target))
            if not resolved.startswith(real_root + os.sep):
                warnings.append(
                    _diagnostic(
                        f"{scalar.tag} {target} points outside the dashboards folder; "
                        "HA SOC cannot check or edit it",
                        scalar.start_mark,
                    )
                )
                continue
            if not os.path.exists(resolved):
                warnings.append(
                    _diagnostic(f"{scalar.tag} target {target} does not exist", scalar.start_mark)
                )
    return warnings


def _iter_scalar_nodes(node: yaml.Node):
    if isinstance(node, yaml.ScalarNode):
        yield node
    elif isinstance(node, yaml.SequenceNode):
        for child in node.value:
            yield from _iter_scalar_nodes(child)
    elif isinstance(node, yaml.MappingNode):
        for key_node, value_node in node.value:
            yield from _iter_scalar_nodes(key_node)
            yield from _iter_scalar_nodes(value_node)


def _validate_sync(hass: HomeAssistant, relative: str | None, content: str) -> dict[str, Any]:
    """Syntax errors and advisory warnings; sync, executor-only (it stats files)."""
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    try:
        list(yaml.compose_all(content, Loader=_TagTolerantLoader))
    except yaml.MarkedYAMLError as err:
        message = err.problem or str(err)
        if err.context:
            message = f"{err.context}: {message}"
        errors.append(_diagnostic(message, err.problem_mark or err.context_mark))
    except yaml.YAMLError as err:
        errors.append(_diagnostic(str(err), None))

    if not errors:
        warnings.extend(_duplicate_key_warnings(content))
        if relative is not None:
            warnings.extend(_missing_include_warnings(hass, relative, content))
        if len(content.encode("utf-8")) > MAX_FILE_BYTES:
            errors.append(_diagnostic("File is larger than the edit limit", None))
    return {"valid": not errors, "errors": errors, "warnings": warnings}


async def async_validate(
    hass: HomeAssistant, content: str, relative: str | None = None
) -> dict[str, Any]:
    """Server-side verdict on a draft. The panel's own parse is advisory."""
    checked_relative = _check_relative(relative) if relative else None
    return await hass.async_add_executor_job(_validate_sync, hass, checked_relative, content)


def _backup_sync(hass_config_dir: str, relative: str, content: str, stamp: str) -> str:
    """Copy the pre-write text aside; sync, executor-only."""
    dir_path = os.path.join(hass_config_dir, BACKUP_DIR)
    os.makedirs(dir_path, mode=0o700, exist_ok=True)
    os.chmod(dir_path, 0o700)
    stem = relative.replace("/", "_")
    path = os.path.join(dir_path, f"{stem}-{stamp}.bak")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as file:
        file.write(content)
    return path


def _prune_backups_sync(hass_config_dir: str) -> None:
    dir_path = os.path.join(hass_config_dir, BACKUP_DIR)
    if not os.path.isdir(dir_path):
        return
    cutoff = time.time() - BACKUP_RETENTION_DAYS * 24 * 3600
    for name in os.listdir(dir_path):
        path = os.path.join(dir_path, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                os.unlink(path)
        except OSError:
            # A vanished or undeletable backup must not block the write.
            continue


def _write_sync(path: str, content: str) -> None:
    """Replace the file's contents atomically; sync, executor-only.

    The temp file is created in the same directory so os.replace stays on one
    filesystem, and the original mode is carried over so a deliberately
    tightened dashboard file does not come back world-readable.
    """
    directory = os.path.dirname(path)
    mode = os.stat(path, follow_symlinks=False).st_mode & 0o777
    tmp_path = os.path.join(directory, f".ha_soc-{os.path.basename(path)}.tmp")
    fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


async def async_write_file(
    hass: HomeAssistant,
    relative: str,
    content: str,
    expected_sha256: str,
) -> dict[str, Any]:
    """Overwrite one dashboard file, refusing on a stale digest or bad YAML.

    The caller has already checked authorization and the feature switch; what
    is enforced here is that the digest presented came from a read of the
    text now on disk, so two operators editing the same file cannot silently
    overwrite one another.
    """
    checked = _check_relative(relative)
    path = _resolve(hass, relative)
    async with _lock_for(path):
        return await _async_write_locked(hass, checked, path, content, expected_sha256)


async def _async_write_locked(
    hass: HomeAssistant,
    checked: str,
    path: str,
    content: str,
    expected_sha256: str,
) -> dict[str, Any]:
    """The compare-and-write body, run with the per-file lock held."""
    current = await async_read_file(hass, checked)
    if current["sha256"] != expected_sha256:
        raise DashboardFileError(
            ERR_CONFLICT,
            "The file changed on disk since it was loaded",
            {"path": checked, "sha256": current["sha256"], "content": current["content"]},
        )

    verdict = await async_validate(hass, content, checked)
    if not verdict["valid"]:
        raise DashboardFileError(
            ERR_INVALID_YAML, "The draft is not valid YAML", {"errors": verdict["errors"]}
        )

    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise DashboardFileError(ERR_TOO_LARGE, "The draft is larger than the edit limit")

    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    backup = await hass.async_add_executor_job(
        _backup_sync, hass.config.config_dir, checked, current["content"], stamp
    )
    try:
        await hass.async_add_executor_job(_write_sync, path, content)
    except OSError as err:
        raise DashboardFileError(ERR_WRITE_FAILED, f"The file could not be written: {err}") from err
    await hass.async_add_executor_job(_prune_backups_sync, hass.config.config_dir)

    return {
        "path": checked,
        "sha256": _sha256(content),
        "previous_sha256": current["sha256"],
        "backup": os.path.relpath(backup, hass.config.config_dir).replace(os.sep, "/"),
        "warnings": verdict["warnings"],
        "bytes": len(content.encode("utf-8")),
    }
