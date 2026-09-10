"""Threat Management posture and block log, read from a UniFi gateway over SSH.

The Network Integration API has no threat, IPS, or event route at any
version, so the perimeter answer has to come from the gateway itself. Two
allowlisted reads in ssh_devices.py feed this module: the six files under
/run/ips/config that configure Suricata and Ubiquiti's blocking daemon, and
the *_BLOCKED* rows of the controller's Mongo alert collection. Everything
here is pure parsing over that text; the file layout, what each field means,
and why the Suricata signature detail is unavailable are recorded in
docs/UNIFI-LOCAL-API-CONTRACT.md.

Two rules shape the output. A file the read did not return is reported as
not parsed, never as "no exemptions" or "no interfaces"; and a mode the
daemon config did not state is "unknown", not "off".
"""
from __future__ import annotations

import ipaddress
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any

KIND_CONFIG = "ips_config"
KIND_BLOCK_LOG = "ips_block_log"

MODE_PREVENT = "prevent"
MODE_DETECT = "detect"
MODE_OFF = "off"
MODE_UNKNOWN = "unknown"

# A blanket suppression in threshold.config: every generator, every signature.
_SUPPRESS = re.compile(
    r"^\s*suppress\s+gen_id\s+(?P<gen>\d+)\s*,\s*sig_id\s+(?P<sig>\d+)\s*,"
    r"\s*track\s+(?P<track>by_src|by_dst|by_either)\s*,\s*ip\s+\[?(?P<ips>[^\]\n]*)\]?",
    re.IGNORECASE,
)
_THRESHOLD_LINE = re.compile(r"^\s*(suppress|threshold|rate_filter|event_filter)\b", re.IGNORECASE)
_YAML_DOC = re.compile(r"^%YAML\b", re.MULTILINE)


def _json_docs(text: str, limit: int) -> tuple[list[Any], str]:
    """Up to ``limit`` JSON documents from the front of ``text``.

    The read concatenates the JSON files, so the documents are back to back
    with no separator. raw_decode reads one and reports where it stopped.
    """
    decoder = json.JSONDecoder()
    docs: list[Any] = []
    pos = 0
    while len(docs) < limit:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        if pos >= len(text) or text[pos] not in "{[":
            break
        try:
            doc, end = decoder.raw_decode(text, pos)
        except ValueError:
            break
        docs.append(doc)
        pos = end
    return docs, text[pos:]


def _yaml_docs(text: str) -> list[Any]:
    import yaml

    docs: list[Any] = []
    starts = [m.start() for m in _YAML_DOC.finditer(text)]
    if not starts:
        return docs
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        try:
            docs.append(yaml.safe_load(text[start:end]))
        except yaml.YAMLError:
            docs.append(None)
    return docs


def _cidrs(value: Any) -> list[str]:
    """Normalised CIDR strings from a list, or from Suricata's ``[a,b]`` text."""
    if isinstance(value, str):
        value = value.strip().strip("[]").split(",")
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            continue
        try:
            out.append(str(ipaddress.ip_network(text, strict=False)))
        except ValueError:
            # Suricata variables such as $HOME_NET, or something unparseable;
            # kept verbatim so the reader can see it.
            out.append(text)
    return out


def _unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _str_list(value: Any) -> list[str]:
    return [str(v) for v in value] if isinstance(value, list) else []


def parse_ips_config(text: str) -> dict[str, Any]:
    """The posture in the six /run/ips/config files, concatenated in this order:
    config.json, daemon_config.json, ip_reputation.json, homenet.yaml,
    iface.yaml, threshold.config."""
    json_docs, remainder = _json_docs(text, 3)
    config = json_docs[0] if len(json_docs) > 0 and isinstance(json_docs[0], dict) else None
    daemon = json_docs[1] if len(json_docs) > 1 and isinstance(json_docs[1], dict) else None
    reputation = json_docs[2] if len(json_docs) > 2 and isinstance(json_docs[2], dict) else None

    threshold_lines = [line for line in remainder.splitlines() if _THRESHOLD_LINE.match(line)]
    yaml_text = "\n".join(line for line in remainder.splitlines() if not _THRESHOLD_LINE.match(line))
    yaml_docs = _yaml_docs(yaml_text)
    homenet = next((d for d in yaml_docs if isinstance(d, dict) and "vars" in d), None)
    ifaces = next((d for d in yaml_docs if isinstance(d, dict) and "pcap" in d), None)

    drop_categories = _str_list((daemon or {}).get("block_category")) or _str_list(
        ((config or {}).get("drop") or {}).get("category")
    )
    alert_categories = _str_list(((config or {}).get("alert") or {}).get("category"))
    if daemon is None and config is None:
        mode = MODE_UNKNOWN
    elif drop_categories or _str_list((daemon or {}).get("block_sid")):
        mode = MODE_PREVENT
    elif alert_categories or _str_list(((config or {}).get("alert") or {}).get("signature_id")):
        mode = MODE_DETECT
    else:
        mode = MODE_OFF

    src = _cidrs((reputation or {}).get("src_whitelist"))
    dst = _cidrs((reputation or {}).get("dst_whitelist"))

    suppressed: list[str] = []
    suppressed_signatures: list[dict[str, Any]] = []
    for line in threshold_lines:
        match = _SUPPRESS.match(line)
        if not match:
            continue
        networks = _cidrs(match.group("ips"))
        if match.group("gen") == "0" and match.group("sig") == "0":
            suppressed.extend(networks)
        else:
            suppressed_signatures.append(
                {"gen_id": int(match.group("gen")), "sig_id": int(match.group("sig")), "networks": networks}
            )

    home_networks: list[str] = []
    if homenet is not None:
        groups = ((homenet.get("vars") or {}).get("address-groups")) or {}
        home_networks = _cidrs(groups.get("HOME_NET"))

    interfaces: list[dict[str, Any]] = []
    if ifaces is not None:
        for entry in ifaces.get("pcap") or []:
            if isinstance(entry, dict) and entry.get("interface"):
                interfaces.append(
                    {"interface": str(entry["interface"]), "bpf_filter": entry.get("bpf-filter")}
                )

    return {
        "kind": KIND_CONFIG,
        "parsed": {
            "config": config is not None,
            "daemon": daemon is not None,
            "reputation": reputation is not None,
            "homenet": homenet is not None,
            "interfaces": ifaces is not None,
            "threshold": bool(threshold_lines),
        },
        "mode": mode,
        "drop_categories": drop_categories,
        "alert_categories": alert_categories,
        "drop_signature_ids": _str_list((daemon or {}).get("block_sid")),
        "block_time_seconds": _int((daemon or {}).get("block_time")),
        "logging_threat_event": _bool((daemon or {}).get("logging_threat_event")),
        "ssl_inspection": _bool((daemon or {}).get("is_ssl_inspection_enabled")),
        "suricata_version": _int((daemon or {}).get("suricata_version")),
        "exempt_sources": src,
        "exempt_destinations": dst,
        "exempt_networks": _unique(src + dst),
        "suppressed_networks": _unique(suppressed),
        "suppressed_signatures": suppressed_signatures,
        "home_networks": home_networks,
        "interfaces": interfaces,
    }


def _int(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _covered(address: str, networks: list[str]) -> str | None:
    """The first network that contains ``address``, or None."""
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return None
    for network in networks:
        try:
            if ip in ipaddress.ip_network(network, strict=False):
                return network
        except ValueError:
            continue
    return None


def evaluate(posture: dict[str, Any], server_ips: list[str]) -> list[dict[str, Any]]:
    """Advisory findings from a posture, as {id, severity, category, title, detail}.

    ``server_ips`` is the Home Assistant server's own addresses as the Probe
    reported them; empty means unknown, and the findings say so rather than
    assuming the server is or is not covered.
    """
    findings: list[dict[str, Any]] = []
    parsed = posture.get("parsed") or {}
    mode = posture.get("mode")

    if mode == MODE_OFF:
        findings.append(
            {
                "id": "ips_off",
                "severity": "high",
                "category": "coverage",
                "title": "Threat Management is off on the gateway",
                "detail": (
                    "The gateway's IPS daemon lists no categories to alert on or block, so "
                    "Suricata produces nothing. Turn Threat Management on under Settings, "
                    "Security in the UniFi UI; Detect mode logs without blocking."
                ),
            }
        )
    elif mode == MODE_DETECT:
        findings.append(
            {
                "id": "ips_detect_only",
                "severity": "medium",
                "category": "coverage",
                "title": "Threat Management detects but does not block",
                "detail": (
                    f"{len(posture.get('alert_categories') or [])} categories alert and none "
                    "block. A detection is recorded but the connection completes. Switch to "
                    "Prevent for the categories you trust, or accept this as a deliberate choice."
                ),
            }
        )
    elif mode == MODE_UNKNOWN:
        findings.append(
            {
                "id": "ips_mode_unknown",
                "severity": "info",
                "category": "coverage",
                "title": "Threat Management mode could not be read",
                "detail": (
                    "Neither IPS configuration file parsed, so HA SOC cannot say whether the "
                    "gateway alerts, blocks, or does nothing. Run the ips_config read again "
                    "against the gateway."
                ),
            }
        )

    if parsed.get("daemon") and posture.get("logging_threat_event") is False:
        findings.append(
            {
                "id": "ips_threat_logging_off",
                "severity": "medium",
                "category": "coverage",
                "title": "Threat events are not being logged",
                "detail": (
                    "The IPS daemon's logging_threat_event is false, so blocks happen without a "
                    "record in the controller's alert collection and nothing downstream can see "
                    "them. Enable threat logging in the UniFi UI."
                ),
            }
        )

    exempt = _unique(list(posture.get("exempt_networks") or []) + list(posture.get("suppressed_networks") or []))
    if exempt and (parsed.get("reputation") or parsed.get("threshold")):
        if server_ips:
            hits = [(ip, net) for ip in server_ips if (net := _covered(ip, exempt))]
            if hits:
                listed = ", ".join(f"{ip} (in {net})" for ip, net in hits)
                findings.append(
                    {
                        "id": "ips_exempts_server",
                        "severity": "high",
                        "category": "coverage",
                        "title": "The Home Assistant server is exempt from the IDS",
                        "detail": (
                            f"The gateway's IPS allowlist and suppression rules cover {listed}, in "
                            "both directions for every signature. Suricata sees the packets and is "
                            "told to say nothing, so no attack on or from this host can ever appear "
                            "in the threat log. If the entry was added to silence false positives, "
                            "record that decision; otherwise remove the address under Settings, "
                            "Security, Threat Management, Allow List."
                        ),
                    }
                )
        elif exempt:
            findings.append(
                {
                    "id": "ips_exemptions_unchecked",
                    "severity": "info",
                    "category": "coverage",
                    "title": f"The IDS exempts {len(exempt)} network(s) and the server's address is unknown",
                    "detail": (
                        "The Probe has not reported the Home Assistant server's own addresses, so "
                        "HA SOC cannot say whether this host is among the exemptions: "
                        + ", ".join(exempt)
                        + ". Install or pair the Probe to close the question."
                    ),
                }
            )

    home = list(posture.get("home_networks") or [])
    if parsed.get("homenet") and home and server_ips:
        outside = [ip for ip in server_ips if _covered(ip, home) is None]
        if outside:
            findings.append(
                {
                    "id": "ips_not_covering_server",
                    "severity": "medium",
                    "category": "coverage",
                    "title": "The Home Assistant server is outside Suricata's HOME_NET",
                    "detail": (
                        f"HOME_NET on the gateway is {', '.join(home)}, which does not contain "
                        f"{', '.join(outside)}. Signatures that key on HOME_NET treat traffic to "
                        "this host as external-to-external and mostly ignore it. Check that the "
                        "server's network is one the gateway routes and inspects."
                    ),
                }
            )

    return findings


# --- block log ------------------------------------------------------------

_THREAT_PREFIX = "THREAT_BLOCKED"
_TRAFFIC_PREFIX = "TRAFFIC_BLOCKED"


def _endpoint(parameters: dict[str, Any], *keys: str) -> dict[str, Any]:
    """The first present endpoint parameter, flattened to address/mac/name."""
    for key in keys:
        value = parameters.get(key)
        if not isinstance(value, dict):
            continue
        target = value.get("target_id")
        target_text = str(target) if target is not None else None
        is_mac = bool(target_text and re.fullmatch(r"(?i)[0-9a-f]{2}(:[0-9a-f]{2}){5}", target_text))
        return {
            "kind": key,
            "address": value.get("ip") if is_mac else target_text,
            "mac": target_text if is_mac else None,
            "name": value.get("hostname") or value.get("name"),
        }
    return {"kind": None, "address": None, "mac": None, "name": None}


def parse_block_log(text: str, *, now: datetime | None = None) -> dict[str, Any]:
    """One JSON object per line, as the ips_block_log command projects them."""
    now = now or datetime.now(UTC)
    day_ago = now - timedelta(hours=24)
    rows: list[dict[str, Any]] = []
    unparsed = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except ValueError:
            unparsed += 1
            continue
        if not isinstance(raw, dict) or not isinstance(raw.get("key"), str):
            unparsed += 1
            continue
        key = raw["key"]
        if key.startswith(_THREAT_PREFIX):
            kind = "threat"
        elif key.startswith(_TRAFFIC_PREFIX):
            kind = "firewall"
        else:
            kind = "other"
        parameters = raw.get("parameters") if isinstance(raw.get("parameters"), dict) else {}
        millis = _int(raw.get("time"))
        when = datetime.fromtimestamp(millis / 1000, UTC) if millis else None
        trigger = parameters.get("TRIGGER") if isinstance(parameters.get("TRIGGER"), dict) else None
        rows.append(
            {
                "id": str(raw.get("id") or raw.get("_id") or ""),
                "key": key,
                "kind": kind,
                "time": when.isoformat() if when else None,
                "severity": raw.get("severity"),
                "source": _endpoint(parameters, "SRC_CLIENT", "SRC_DEVICE", "SRC_IP"),
                "destination": _endpoint(parameters, "DST_CLIENT", "DST_DEVICE", "DST_IP"),
                "policy": (trigger or {}).get("name"),
                "last_24h": bool(when and when >= day_ago),
            }
        )
    rows.sort(key=lambda r: r["time"] or "", reverse=True)

    by_key: dict[str, int] = {}
    for row in rows:
        by_key[row["key"]] = by_key.get(row["key"], 0) + 1
    recent = [r for r in rows if r["last_24h"]]
    sources_24h = _unique(
        [r["source"]["address"] or r["source"]["mac"] for r in recent if r["source"]["address"] or r["source"]["mac"]]
    )
    return {
        "kind": KIND_BLOCK_LOG,
        "rows": rows,
        "unparsed": unparsed,
        "by_key": by_key,
        "threat_blocks_24h": sum(1 for r in recent if r["kind"] == "threat"),
        "firewall_blocks_24h": sum(1 for r in recent if r["kind"] == "firewall"),
        "sources_24h": sources_24h,
    }
