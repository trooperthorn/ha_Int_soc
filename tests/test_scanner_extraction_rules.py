"""Tests for scanner.py's four cross-integration extraction rules (SEC-5).

Each rule is exercised with positive cases (the extraction pattern fires),
negative cases (the documented legitimate patterns and false-positive
guards stay quiet), and the acknowledgment marker. The final test scans
custom_components/ha_soc itself and asserts the integration passes its own
rules, which is the plan's honesty requirement for SEC-4/SEC-5.
"""
import ast
import textwrap
from pathlib import Path

from custom_components.ha_soc.scanner import (
    _EXTRACTION_PATTERNS,
    _rule_foreign_config_entry_read,
    _rule_foreign_hass_data_read,
    _rule_foreign_storage_key,
    _rule_storage_file_access,
    scan_directory,
)

DOMAIN = "my_int"


def _run(rule, source: str, domain: str = DOMAIN) -> list[dict]:
    src = textwrap.dedent(source)
    return rule(ast.parse(src), src.splitlines(), domain)


# -- Rule (a): foreign_config_entry_read -------------------------------------


def test_entry_read_fires_on_indiscriminate_stringify() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def sweep(hass):
            for entry in hass.config_entries.async_entries():
                blob = f"{entry.data}{entry.options}"
            return blob
        """,
    )
    assert len(hits) == 1
    assert hits[0]["pattern"] == "foreign_config_entry_read"
    assert hits[0]["confidence"] == "medium"


def test_entry_read_fires_on_non_locator_literal_key() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def sweep(hass):
            found = []
            for entry in hass.config_entries.async_entries():
                found.append(entry.data.get("username"))
            return found
        """,
    )
    assert len(hits) == 1


def test_entry_read_fires_on_targeted_credential_key() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def steal(hass):
            for entry in hass.config_entries.async_entries("other_cloud"):
                token = entry.data["api_key"]
            return token
        """,
    )
    assert len(hits) == 1


def test_entry_read_fires_on_targeted_wholesale_use() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def steal(hass):
            for entry in hass.config_entries.async_entries("other_cloud"):
                blob = str(entry.data)
            return blob
        """,
    )
    assert len(hits) == 1


def test_entry_read_fires_through_one_level_alias() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def sweep(hass):
            for entry in hass.config_entries.async_entries():
                opts = entry.options or {}
                blob = f"{opts}"
            return blob
        """,
    )
    assert len(hits) == 1


def test_entry_read_fires_on_logged_mapping() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def sweep(hass, logger):
            for entry in hass.config_entries.async_entries():
                logger.debug("entry: %s", entry.data)
        """,
    )
    assert len(hits) == 1


def test_entry_read_quiet_on_domain_only_enumeration() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def domains(hass):
            return {entry.domain for entry in hass.config_entries.async_entries()}
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_locator_key() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def find_host(hass):
            for entry in hass.config_entries.async_entries():
                if entry.data.get("host") == "10.0.0.2":
                    return entry.entry_id
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_variable_key_and_membership() -> None:
    # The unifi.py pattern: membership test plus a variable-key subscript.
    # A variable key is statically invisible, which the rule's docstring
    # names as its evasion avenue.
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def hosts(hass, host_keys):
            out = set()
            for entry in hass.config_entries.async_entries():
                for key in host_keys:
                    if key in entry.data:
                        out.add(entry.data[key])
            return out
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_own_domain_literal() -> None:
    # Reading a credential out of the integration's OWN entries is where
    # integrations normally keep their credentials, not extraction.
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def own(hass):
            for entry in hass.config_entries.async_entries("my_int"):
                return entry.data["password"]
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_targeted_non_sensitive_key() -> None:
    # The config_hygiene.py pattern: a visible, auditable read of one named
    # domain's non-secret structural fields.
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def group_members(hass):
            refs = []
            for entry in hass.config_entries.async_entries("group"):
                refs.extend(entry.options.get("entities") or [])
            return refs
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_unrelated_data_attribute() -> None:
    # The health.py pattern: the .data attribute in scope belongs to a
    # store object, not to the enumerated entries.
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def roll(hass, store):
            domains = {entry.domain for entry in hass.config_entries.async_entries()}
            return store.data["integration_health"], domains
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_variable_domain_argument() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def lookup(hass, domain):
            for entry in hass.config_entries.async_entries(domain):
                return entry.data["password"]
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_tuple_alias_with_variable_fields() -> None:
    # The entity_remap.py SEC-4 pattern: both mappings aliased through a
    # tuple iteration, then read with variable field names.
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def refs(hass, fields):
            found = []
            for entry in hass.config_entries.async_entries():
                for mapping in (entry.options or {}, entry.data or {}):
                    for field in fields:
                        value = mapping.get(field)
                        if value:
                            found.append(value)
            return found
        """,
    )
    assert hits == []


def test_entry_read_quiet_on_mapping_passed_to_unknown_helper() -> None:
    # The peripherals.py SEC-4 pattern: the mapping goes to a helper whose
    # effect is statically unknowable, so the rule stays quiet rather than
    # flag every function that takes a mapping.
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def match(hass):
            for entry in hass.config_entries.async_entries():
                for value in iter_locator_strings(entry.data or {}):
                    if value == "/dev/ttyUSB0":
                        return entry.entry_id
        """,
    )
    assert hits == []


def test_entry_read_fires_on_mapping_passed_to_consuming_callable() -> None:
    hits = _run(
        _rule_foreign_config_entry_read,
        """
        def dump(hass, json):
            out = []
            for entry in hass.config_entries.async_entries():
                out.append(json.dumps(entry.data))
            return out
        """,
    )
    assert len(hits) == 1


# -- Rule (b): storage_file_access -------------------------------------------


def test_storage_access_fires_on_foreign_storage_literal() -> None:
    hits = _run(
        _rule_storage_file_access,
        """
        def read_entries(hass):
            with open(hass.config.path(".storage/core.config_entries")) as fh:
                return fh.read()
        """,
    )
    assert len(hits) == 1
    assert hits[0]["pattern"] == "storage_file_access"
    assert hits[0]["confidence"] == "high"


def test_storage_access_fires_on_join_with_following_literal() -> None:
    hits = _run(
        _rule_storage_file_access,
        """
        import os

        def build(hass):
            return os.path.join(hass.config.path(".storage"), "core.restore_state")
        """,
    )
    assert len(hits) == 1


def test_storage_access_fires_once_per_line_for_path_read() -> None:
    hits = _run(
        _rule_storage_file_access,
        """
        def read_auth(config_dir):
            return Path(config_dir, ".storage", "auth").read_text()
        """,
    )
    assert len(hits) == 1


def test_storage_access_fires_on_secrets_yaml() -> None:
    hits = _run(
        _rule_storage_file_access,
        """
        def read_secrets(hass):
            return open(hass.config.path("secrets.yaml")).read()
        """,
    )
    assert len(hits) == 1


def test_storage_access_documented_false_positive_still_fires() -> None:
    # Documented false positive of the substring match: a filename that
    # merely contains "secrets.yaml". Locked in so a change to it is a
    # deliberate decision, not drift.
    hits = _run(
        _rule_storage_file_access,
        """
        def read_mine():
            return open("/config/my_secrets.yaml").read()
        """,
    )
    assert len(hits) == 1


def test_storage_access_quiet_on_undeterminable_namespace() -> None:
    # The audit.py pattern: the namespace component is a constant held in a
    # variable, so the target cannot be determined statically.
    hits = _run(
        _rule_storage_file_access,
        """
        def audit_dir(hass, subdir):
            return hass.config.path(".storage", subdir)
        """,
    )
    assert hits == []


def test_storage_access_quiet_on_own_namespace() -> None:
    hits = _run(
        _rule_storage_file_access,
        """
        def own_cache(hass):
            return hass.config.path(".storage", "my_int_cache")
        """,
    )
    assert hits == []
    hits = _run(
        _rule_storage_file_access,
        """
        def own_file(hass):
            return open(hass.config.path(".storage/my_int.settings")).read()
        """,
    )
    assert hits == []


def test_storage_access_quiet_outside_file_access_calls() -> None:
    hits = _run(
        _rule_storage_file_access,
        """
        STORAGE_LABEL = ".storage"

        def describe():
            return "files under .storage/core.config_entries are private"
        """,
    )
    assert hits == []


def test_storage_access_quiet_on_non_component_substring() -> None:
    hits = _run(
        _rule_storage_file_access,
        """
        def backup():
            return open("/backup/my_int.storage_backup").read()
        """,
    )
    assert hits == []


# -- Rule (c): foreign_hass_data_read ----------------------------------------


def test_hass_data_fires_on_foreign_domain_literal() -> None:
    hits = _run(
        _rule_foreign_hass_data_read,
        """
        def peek(hass):
            return hass.data["zwave_js"]
        """,
    )
    assert len(hits) == 1
    assert hits[0]["pattern"] == "foreign_hass_data_read"
    assert hits[0]["confidence"] == "medium"


def test_hass_data_fires_on_self_hass_and_on_write() -> None:
    hits = _run(
        _rule_foreign_hass_data_read,
        """
        class Thing:
            def poke(self):
                self.hass.data["other_int"] = {"planted": True}
        """,
    )
    assert len(hits) == 1


def test_hass_data_quiet_on_own_domain_and_own_prefix() -> None:
    assert (
        _run(
            _rule_foreign_hass_data_read,
            """
            def own(hass):
                return hass.data["my_int"], hass.data["my_int_config"]
            """,
        )
        == []
    )


def test_hass_data_quiet_on_name_key() -> None:
    # The overwhelmingly common spelling hass.data[DOMAIN] carries no
    # literal, which is also the rule's documented evasion avenue.
    assert (
        _run(
            _rule_foreign_hass_data_read,
            """
            def own(hass):
                return hass.data[DOMAIN]
            """,
        )
        == []
    )


def test_hass_data_quiet_on_core_keys_and_non_domain_shapes() -> None:
    assert (
        _run(
            _rule_foreign_hass_data_read,
            """
            def infra(hass):
                registry = hass.data["entity_registry"]
                dotted = hass.data["helpers.script"]
                return registry, dotted
            """,
        )
        == []
    )


def test_hass_data_quiet_on_non_hass_base_and_on_get() -> None:
    assert (
        _run(
            _rule_foreign_hass_data_read,
            """
            def other(msg, hass):
                a = msg.data["zwave_js"]
                b = hass.data.get("zwave_js")
                return a, b
            """,
        )
        == []
    )


# -- Rule (d): foreign_storage_key -------------------------------------------


def test_storage_key_fires_on_foreign_literal() -> None:
    hits = _run(
        _rule_foreign_storage_key,
        """
        def make(hass):
            return Store(hass, 1, "core.config_entries")
        """,
    )
    assert len(hits) == 1
    assert hits[0]["pattern"] == "foreign_storage_key"
    assert hits[0]["confidence"] == "high"


def test_storage_key_fires_on_dotted_generic_and_keyword_forms() -> None:
    hits = _run(
        _rule_foreign_storage_key,
        """
        def make(hass, storage):
            a = storage.Store(hass, 1, "other_domain")
            b = Store[dict[str, str]](hass, 1, "auth")
            c = Store(hass, version=1, key="core.uuid")
            return a, b, c
        """,
    )
    assert len(hits) == 3


def test_storage_key_quiet_on_own_namespace() -> None:
    assert (
        _run(
            _rule_foreign_storage_key,
            """
            def make(hass):
                a = Store(hass, 1, "my_int.storage")
                b = Store(hass, 1, "my_int_data")
                c = Store(hass, 1, "my_int")
                return a, b, c
            """,
        )
        == []
    )


def test_storage_key_quiet_on_variable_key_and_subclass() -> None:
    # A key held in a constant and a Store subclass under another name are
    # both invisible, which the rule's docstring names as its evasion
    # avenue; ha_soc's own HaSocStore relies on exactly this shape and is
    # deliberately not special-cased.
    assert (
        _run(
            _rule_foreign_storage_key,
            """
            def make(hass):
                a = Store(hass, 1, STORAGE_KEY)
                b = MyStore(hass, 1, "core.anything")
                return a, b
            """,
        )
        == []
    )


# -- Acknowledgment marker ----------------------------------------------------


def test_allow_marker_records_acknowledged_not_skipped(tmp_path: Path) -> None:
    """A marked read still produces a finding (visible, counted) but it is
    acknowledged, carries the reason, and does not count as open."""
    source = textwrap.dedent(
        """
        def sweep(hass):
            # ha-soc-allow: foreign_config_entry_read documented read-only enrichment
            for entry in hass.config_entries.async_entries():
                blob = f"{entry.data}"
            return blob
        """
    )
    (tmp_path / "marked.py").write_text(source, encoding="utf-8")
    findings = scan_directory(tmp_path, DOMAIN)
    extraction = [f for f in findings if f["pattern"] in _EXTRACTION_PATTERNS]
    assert len(extraction) == 1
    assert extraction[0]["acknowledged"] is True
    assert extraction[0]["acknowledged_reason"] == "documented read-only enrichment"
    assert extraction[0]["severity"] == "medium"


def test_allow_marker_requires_matching_pattern(tmp_path: Path) -> None:
    source = textwrap.dedent(
        """
        def sweep(hass):
            # ha-soc-allow: some_other_rule wrong marker
            for entry in hass.config_entries.async_entries():
                blob = f"{entry.data}"
            return blob
        """
    )
    (tmp_path / "wrong.py").write_text(source, encoding="utf-8")
    findings = scan_directory(tmp_path, DOMAIN)
    extraction = [f for f in findings if f["pattern"] in _EXTRACTION_PATTERNS]
    assert len(extraction) == 1
    assert extraction[0]["acknowledged"] is False
    assert "acknowledged_reason" not in extraction[0]


# -- The self-scan honesty requirement ---------------------------------------


def test_ha_soc_passes_its_own_extraction_rules() -> None:
    """custom_components/ha_soc must produce zero OPEN findings from the
    four SEC-5 extraction rules (acknowledged findings would be allowed,
    but as of SEC-4 none are needed). Nothing in the rules special-cases
    the ha_soc domain string; this test is the proof that the precise rule
    definitions and the integration's own narrowed reads line up."""
    component_dir = Path(__file__).resolve().parent.parent / "custom_components" / "ha_soc"
    assert component_dir.is_dir()
    findings = scan_directory(component_dir, "ha_soc")
    open_findings = [
        f
        for f in findings
        if f["pattern"] in _EXTRACTION_PATTERNS and not f.get("acknowledged")
    ]
    detail = "\n".join(
        f'  {f["file"]}:{f["line"]}  {f["pattern"]}  {f["snippet"]}' for f in open_findings
    )
    assert not open_findings, (
        "HA SOC's own code must pass its extraction rules (work plan item SEC-5). "
        f"Open findings:\n{detail}\n"
        "If every file named above is peripherals.py or entity_remap.py, this is "
        "pre-SEC-4 code and clears when that item's locator-key allowlist lands; "
        "any other file is a new regression."
    )
