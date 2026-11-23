#!/usr/bin/env python3
"""Local-subnet host/port discovery for the HA SOC Probe. Stdlib only.

Design constraint (see docs/security.md "Netscan capability" in the main
repo): this replaces the idea of bundling nmap, scapy, or Angry IP Scanner.
Everything here is a plain TCP connect from an unprivileged process plus a
read of the kernel's own ARP table -- no raw sockets, no NET_RAW, no ICMP,
and no new container privileges beyond what the Probe already has.

What one cycle does:
  1. Reads /proc/net/arp for IP -> MAC entries the kernel already knows
     about (devices this host has recently talked to).
  2. Unions that with a bounded TCP-connect sweep of the configured local
     subnet(s) x the configured port list, bounded concurrency via an
     asyncio.Semaphore.
  3. On a successful connect, makes one best-effort banner read and, for
     TLS-typical ports, one additional TLS handshake to read the peer
     certificate (verification disabled on purpose: a self-signed cert on
     a LAN device is the expected case, and the point is to read what is
     presented, not to validate a chain). The certificate is reported as
     its SHA-256 fingerprint, plus the DER bytes when the integration does
     not hold that fingerprint yet; the integration parses it. See
     docs/protocol.md "Netscan certificate delivery".
  4. Matches whatever text was read against a small curated regex table
     (SERVICE_SIGNATURES) for a best-effort service guess.
  5. Looks up a best-effort vendor label for each discovered MAC against
     the static, explicitly non-exhaustive OUI table in oui_prefixes.py.
  6. Emits one JSON result document to stdout and POSTs it to Core the
     same way the firewall and SNMP services already do (Supervisor
     proxy, Authorization: Bearer SUPERVISOR_TOKEN, probe_secret in the
     body), so it lands through ha_soc.ingest_probe_result's existing
     Supervisor-context authentication.

This script does one cycle and exits; the run script that invokes it owns
polling the owner-controlled enabled flag, port list, and concurrency cap,
and re-invoking this script on an interval.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import fcntl
import hashlib
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oui_prefixes import vendor_for_mac

SCANNER_VERSION = "netscan/1.4"

# Bounds independent of whatever the owner configures, so a misconfigured or
# hostile poll response cannot turn this into an unbounded sweep.
MAX_PORT_LIST_ENTRIES = 64
MAX_CONCURRENCY_CAP = 128
MAX_HOSTS_PER_NETWORK = 1024
MAX_TOTAL_HOSTS = 4096
CONNECT_TIMEOUT_SECONDS = 0.75
BANNER_READ_TIMEOUT_SECONDS = 0.75
TLS_HANDSHAKE_TIMEOUT_SECONDS = 1.5
BANNER_MAX_BYTES = 256
# One certificate larger than this is reported by fingerprint only, and one
# cycle never carries more DER than the second bound, whatever the LAN presents.
MAX_DER_BYTES = 8192
MAX_DER_BYTES_PER_CYCLE = 262144
MAX_KNOWN_CERTS = 512
# How long to wait after the sweep before reading the ARP table a second time.
# The sweep's own connection attempts make the kernel resolve every on-link
# target; an address that does not answer is marked failed once the kernel's
# neighbour probes run out, which with Linux's default timers (5 s delay, then
# 3 probes 1 s apart) takes about 8 seconds. See docs/protocol.md "Netscan
# presence" for what is and is not verified about this.
ARP_SETTLE_SECONDS = 9
ACCEPT_PRESENCE = "presence"
ACCEPT_GATEWAY = "gateway"
# Further networks the owner asked to have swept (docs/protocol.md "Netscan
# routed networks"). These bounds are enforced here as well as in the
# integration, so a bad poll response cannot widen the sweep.
MAX_EXTRA_NETWORKS = 8
EXTRA_NETWORK_PREFIX_MIN = 22
EXTRA_NETWORK_PREFIX_MAX = 30
_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(net) for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
)
# The Supervisor's internal Docker network, from the Supervisor API documentation.
_SUPERVISOR_NETWORK = ipaddress.ip_network("172.30.32.0/23")
_SHA256_HEX = re.compile(r"^[0-9a-f]{64}$")

# Ports where a TLS handshake is attempted after (or instead of) a plaintext
# banner read; anything not in this set is never wrapped in TLS.
TLS_TYPICAL_PORTS = frozenset({443, 8443, 993, 995, 465, 636, 8883, 9443})

# A small, curated, explicitly non-exhaustive set of banner signatures.
# Matched against whatever plaintext was read (and, for TLS ports, an empty
# string when only a certificate came back); first match wins.
#
# NOTE: _probe_one() never sends a request, only connects and reads -- so an
# HTTP-family server (including Pi-hole's and Technitium's web UIs) will
# usually stay silent until spoken to, and these two banner patterns will
# rarely fire in practice. They are kept anyway for the case a banner (or a
# body, if a future revision starts sending a request) does contain the
# product name, and are backstopped by PORT_SERVICE_HINTS below for the
# common silent-banner case.
SERVICE_SIGNATURES: list[tuple[str, re.Pattern[str]]] = [
    ("ssh", re.compile(r"^SSH-\d")),
    ("ftp", re.compile(r"^220[ -].*FTP", re.IGNORECASE)),
    ("smtp", re.compile(r"^220[ -]")),
    ("http", re.compile(r"^HTTP/\d\.\d")),
    ("telnet", re.compile(r"login[: ]", re.IGNORECASE)),
    ("mysql", re.compile(r"mysql", re.IGNORECASE)),
    ("rdp", re.compile(r"^\x03\x00")),
    ("vnc", re.compile(r"^RFB \d")),
    ("mqtt", re.compile(r"^\x10")),
    ("smb", re.compile(r"^\x00\x00\x00")),
    ("pihole", re.compile(r"pi-hole", re.IGNORECASE)),
    ("technitium", re.compile(r"technitium", re.IGNORECASE)),
]

# Lower-confidence, port-only fallback for services whose web UI does not
# volunteer a banner on a bare connect (see the SERVICE_SIGNATURES note
# above). Only entries with a distinctive, well-known default port belong
# here -- generic ports like 80/443 are deliberately excluded because they
# would produce too many false positives (e.g. Pi-hole has no such port and
# is intentionally not represented here). 5380 is Technitium DNS Server's
# documented default web console port (see docs/protocol.md's Technitium
# section for the API base; the port itself is upstream's own default, not
# independently re-verified in this repo).
PORT_SERVICE_HINTS: dict[int, str] = {
    5380: "technitium",
}


def _guess_service(text: str) -> tuple[str | None, str | None]:
    """Returns (service_guess, confidence). confidence is "high" for a
    banner-text match, "low" for a port-only heuristic fallback, None when
    there was no basis for a guess."""
    for name, pattern in SERVICE_SIGNATURES:
        if pattern.search(text):
            return name, "high"
    return None, None


def _read_arp_table() -> dict[str, str]:
    """IP -> lowercase colon-MAC from the kernel's own ARP table.

    /proc/net/arp columns: IP address, HW type, Flags, HW address, Mask,
    Device. An all-zero MAC (no entry yet, or an incomplete one) is
    skipped. Never raises: a missing or unreadable file (non-Linux, or a
    sandbox without /proc) yields an empty table rather than aborting the
    whole cycle.
    """
    table: dict[str, str] = {}
    try:
        with open("/proc/net/arp", encoding="ascii", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return table
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        ip, _hw_type, _flags, mac = parts[0], parts[1], parts[2], parts[3]
        if mac in ("00:00:00:00:00:00", "<incomplete>"):
            continue
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            continue
        table[ip] = mac.lower()
    return table


def _read_arp_complete() -> dict[str, str]:
    """IP -> MAC for the ARP entries the kernel currently marks complete.

    Column 3 of /proc/net/arp is the flags word; bit 0x2 (ATF_COM) is set while
    the kernel holds a resolved hardware address for the entry. Read after the
    sweep and the settle wait, a complete entry means the host answered ARP
    during this cycle. Never raises.
    """
    table: dict[str, str] = {}
    try:
        with open("/proc/net/arp", encoding="ascii", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return table
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 4:
            continue
        ip, flags, mac = parts[0], parts[2], parts[3]
        try:
            complete = bool(int(flags, 16) & 0x2)
            ipaddress.ip_address(ip)
        except ValueError:
            continue
        if not complete or mac in ("00:00:00:00:00:00", "<incomplete>"):
            continue
        table[ip] = mac.lower()
    return table


def _default_gateway() -> str | None:
    """The IPv4 next hop of the default route, from /proc/net/route, or None.

    Columns: Iface, Destination, Gateway, Flags, ... Destination and Gateway
    are 8 hex digits in the kernel's little-endian word order (01801BAC is
    172.27.128.1). The default route has destination 00000000 and the
    RTF_GATEWAY flag (0x2). With several default routes the first listed is
    taken, which is the order the kernel prints them in. Never raises.
    """
    try:
        with open("/proc/net/route", encoding="ascii", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return None
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 4 or parts[1] != "00000000":
            continue
        try:
            if not int(parts[3], 16) & 0x2:
                continue
            raw = bytes.fromhex(parts[2])
        except ValueError:
            continue
        if len(raw) == 4 and any(raw):
            return socket.inet_ntoa(raw[::-1])
    return None


def _ioctl_ifaddr(sock: socket.socket, ifname: str, request: int) -> str | None:
    """One SIOCGIFADDR/SIOCGIFNETMASK ioctl; None on any failure (no IPv4,
    interface down, permission, etc.) rather than raising."""
    try:
        packed = struct.pack("256s", ifname[:15].encode("utf-8"))
        result = fcntl.ioctl(sock.fileno(), request, packed)
        return socket.inet_ntoa(result[20:24])
    except OSError:
        return None


def _local_ipv4_networks() -> list[ipaddress.IPv4Network]:
    """This host's own IPv4 subnets, read via ioctl (no shelling out to
    `ip`), skipping loopback and any interface without an IPv4 address.

    The Probe runs with host_network: true, so these are the real host
    interfaces, not a container-private bridge.
    """
    networks: list[ipaddress.IPv4Network] = []
    SIOCGIFADDR = 0x8915
    SIOCGIFNETMASK = 0x891B
    try:
        ifnames = os.listdir("/sys/class/net")
    except OSError:
        return networks
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for ifname in ifnames:
            if ifname == "lo" or ifname.startswith(("docker", "veth")):
                continue
            addr = _ioctl_ifaddr(sock, ifname, SIOCGIFADDR)
            netmask = _ioctl_ifaddr(sock, ifname, SIOCGIFNETMASK)
            if not addr or not netmask:
                continue
            try:
                network = ipaddress.ip_network(f"{addr}/{netmask}", strict=False)
            except ValueError:
                continue
            if network.version == 4 and not network.is_loopback:
                networks.append(network)
    return networks


def _container_networks() -> list[ipaddress.IPv4Network]:
    """The subnets of this host's container bridges, which are never swept."""
    networks: list[ipaddress.IPv4Network] = [_SUPERVISOR_NETWORK]
    try:
        ifnames = os.listdir("/sys/class/net")
    except OSError:
        return networks
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        for ifname in ifnames:
            if not ifname.startswith(("docker", "hassio", "br-", "veth")):
                continue
            addr = _ioctl_ifaddr(sock, ifname, 0x8915)
            netmask = _ioctl_ifaddr(sock, ifname, 0x891B)
            if not addr or not netmask:
                continue
            try:
                networks.append(ipaddress.ip_network(f"{addr}/{netmask}", strict=False))
            except ValueError:
                continue
    return networks


def _refusal_reason(
    raw: object, container_networks: list[ipaddress.IPv4Network]
) -> tuple[ipaddress.IPv4Network | None, str | None]:
    """(network, None) when the network may be swept, else (None, why not).

    Allowed: an IPv4 network from /22 to /30 that lies inside the RFC 1918
    private ranges and does not overlap a container bridge. That rules out
    loopback, link-local, multicast and every public range by construction.
    """
    try:
        network = ipaddress.ip_network(str(raw), strict=False)
    except ValueError:
        return None, "not a network"
    if network.version != 4:
        return None, "not IPv4"
    if not EXTRA_NETWORK_PREFIX_MIN <= network.prefixlen <= EXTRA_NETWORK_PREFIX_MAX:
        return None, "prefix outside /22 to /30"
    if not any(network.subnet_of(private) for private in _PRIVATE_NETWORKS):
        return None, "not a private network"
    if any(network.overlaps(container) for container in container_networks):
        return None, "overlaps a container network"
    return network, None


def _parse_extra_networks(raw: str | None) -> list[ipaddress.IPv4Network]:
    """The owner's further networks that pass _refusal_reason, at most MAX_EXTRA_NETWORKS."""
    try:
        parsed = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    containers = _container_networks()
    networks: list[ipaddress.IPv4Network] = []
    for item in parsed[:MAX_EXTRA_NETWORKS]:
        network, _reason = _refusal_reason(item, containers)
        if network is not None and network not in networks:
            networks.append(network)
    return networks


def _sweep_targets(networks: list[ipaddress.IPv4Network], arp_ips: set[str]) -> list[str]:
    """The bounded address list to sweep: every host in each local subnet
    (skipped if a network is implausibly large for a bounded sweep) unioned
    with whatever the ARP table already knows, capped overall."""
    targets: set[str] = set()
    for network in networks:
        if network.num_addresses > MAX_HOSTS_PER_NETWORK * 4:
            # A /16 or larger is not a "local subnet" in the sense this
            # feature is scoped for; skip the sweep but keep ARP entries
            # inside it, added below.
            continue
        for count, host in enumerate(network.hosts(), start=1):
            targets.add(str(host))
            if count >= MAX_HOSTS_PER_NETWORK:
                break
    targets.update(arp_ips)
    if len(targets) > MAX_TOTAL_HOSTS:
        # Deterministic truncation (sorted) rather than an arbitrary set
        # ordering, so repeated cycles behave predictably.
        targets = set(sorted(targets)[:MAX_TOTAL_HOSTS])
    return sorted(targets)


async def _read_banner(reader: asyncio.StreamReader) -> str:
    try:
        data = await asyncio.wait_for(
            reader.read(BANNER_MAX_BYTES), timeout=BANNER_READ_TIMEOUT_SECONDS
        )
    except (asyncio.TimeoutError, OSError):
        return ""
    return data.decode("utf-8", errors="replace")


async def _read_tls_cert(ip: str, port: int) -> dict[str, object] | None:
    """One additional TLS handshake, verification disabled on purpose: a
    self-signed certificate is the expected shape on a LAN, and the point
    is to read whatever is presented, not to validate a chain.

    Returns None when there was no TLS handshake, an empty dict when the
    handshake succeeded without a leaf certificate, and otherwise the
    fingerprint plus the raw DER under "_der" (removed again by
    _attach_certificates before anything is reported).

    With verify_mode CERT_NONE the dict form of getpeercert() is always
    empty, so only binary_form=True yields the certificate.
    """
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(ip, port, ssl=ctx), timeout=TLS_HANDSHAKE_TIMEOUT_SECONDS
        )
    except (asyncio.TimeoutError, OSError, ssl.SSLError):
        return None
    try:
        ssl_object = writer.get_extra_info("ssl_object")
        der = ssl_object.getpeercert(binary_form=True) if ssl_object is not None else None
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except (OSError, ssl.SSLError):
            pass
    if not der:
        return {}
    return {"sha256": hashlib.sha256(der).hexdigest(), "_der": der}


def _attach_certificates(
    hosts: list[dict[str, object]], known: set[str] | None
) -> None:
    """Decide, in place, what each TLS entry reports.

    ``known`` is the set of fingerprints the integration already holds, or
    None when the integration did not send one. None means an integration
    build from before certificate delivery, whose schema rejects the new
    keys, so every TLS entry is reported in the old shape.

    Otherwise each entry carries "sha256", and "der" (base64) the first time
    a fingerprint the integration does not hold appears in this cycle, while
    the per-certificate and per-cycle size bounds allow.
    """
    budget = MAX_DER_BYTES_PER_CYCLE
    sent: set[str] = set()
    for host in hosts:
        for entry in host.get("open_ports") or []:  # type: ignore[union-attr]
            tls = entry.get("tls")
            if not isinstance(tls, dict):
                continue
            der = tls.pop("_der", None)
            fingerprint = tls.get("sha256")
            if known is None:
                entry["tls"] = {
                    "subject": None,
                    "issuer": None,
                    "not_after": None,
                    "self_signed": None,
                }
                continue
            if not der or fingerprint in known or fingerprint in sent:
                continue
            if len(der) > MAX_DER_BYTES or len(der) > budget:
                continue
            budget -= len(der)
            sent.add(fingerprint)
            tls["der"] = base64.b64encode(der).decode("ascii")


async def _probe_one(
    ip: str, port: int, semaphore: asyncio.Semaphore
) -> dict[str, object] | None:
    async with semaphore:
        started = time.monotonic()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=CONNECT_TIMEOUT_SECONDS
            )
        except ConnectionRefusedError:
            # A refusal is an answer: the host is there, the port is shut.
            return {"_refused": True, "_rtt_ms": (time.monotonic() - started) * 1000}
        except (asyncio.TimeoutError, OSError):
            return None
        rtt_ms = (time.monotonic() - started) * 1000
        banner = ""
        try:
            banner = await _read_banner(reader)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except OSError:
                pass

    tls_info = None
    if port in TLS_TYPICAL_PORTS:
        async with semaphore:
            tls_info = await _read_tls_cert(ip, port)

    entry: dict[str, object] = {"port": port, "_rtt_ms": rtt_ms}
    if banner:
        entry["banner"] = banner.strip()
    service_guess, confidence = _guess_service(banner)
    if service_guess is None and port in PORT_SERVICE_HINTS:
        service_guess, confidence = PORT_SERVICE_HINTS[port], "low"
    if service_guess is None and tls_info is not None:
        service_guess, confidence = "tls", "high"
    if service_guess:
        entry["service_guess"] = service_guess
        entry["service_confidence"] = confidence
    if tls_info is not None:
        entry["tls"] = tls_info
    return entry


async def _run_cycle(
    port_list: list[int],
    max_concurrency: int,
    known_certs: set[str] | None = None,
    presence: bool = False,
    extra_networks: list[ipaddress.IPv4Network] | None = None,
    only_extra: bool = False,
) -> list[dict[str, object]]:
    """One sweep. With ``presence`` each host also reports whether it answered
    (``responded``: a completed or refused connection), whether the kernel held
    a resolved ARP entry for it after the sweep (``arp_after_sweep``), and the
    fastest TCP connect or refusal time (``rtt_ms``). Without it the result has
    the shape older integrations accept.

    ``extra_networks`` are swept as well as the local ones and each host found
    in one carries ``network``. ``only_extra`` sweeps them alone, with no ARP
    read at all: that is the trial of one network before the owner adds it."""
    extra_networks = extra_networks or []
    if only_extra:
        arp_table: dict[str, str] = {}
        targets = _sweep_targets(extra_networks, set())
    else:
        arp_table = _read_arp_table()
        networks = _local_ipv4_networks()
        targets = _sweep_targets(networks + extra_networks, set(arp_table))

    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = {
        (ip, port): asyncio.create_task(_probe_one(ip, port, semaphore))
        for ip in targets
        for port in port_list
    }
    results = await asyncio.gather(*tasks.values(), return_exceptions=False)

    hosts: dict[str, dict[str, object]] = {}
    for (ip, _port), entry in zip(tasks.keys(), results):
        if entry is None:
            continue
        rtt_ms = entry.pop("_rtt_ms", None)
        refused = entry.pop("_refused", False)
        if refused and not presence:
            continue
        host = hosts.setdefault(ip, {"ip": ip, "open_ports": []})
        if not refused:
            host["open_ports"].append(entry)  # type: ignore[union-attr]
        if presence:
            host["responded"] = True
            if isinstance(rtt_ms, float) and rtt_ms < float(host.get("rtt_ms", 1e9)):  # type: ignore[arg-type]
                host["rtt_ms"] = round(rtt_ms, 1)

    # Include ARP-known hosts with no open port in the configured list too,
    # so the panel can show "seen on the network, nothing scanned open"
    # rather than silently dropping them.
    for ip in arp_table:
        hosts.setdefault(ip, {"ip": ip, "open_ports": []})

    if presence and not only_extra:
        await asyncio.sleep(ARP_SETTLE_SECONDS)
        for ip, mac in _read_arp_complete().items():
            host = hosts.setdefault(ip, {"ip": ip, "open_ports": []})
            host["arp_after_sweep"] = True
            # The first read ran before the sweep, so a host that only now
            # resolved gets its MAC in this cycle instead of the next.
            arp_table.setdefault(ip, mac)

    for ip, host in hosts.items():
        address = ipaddress.ip_address(ip)
        for network in extra_networks:
            if address in network:
                host["network"] = str(network)
                break
        mac = arp_table.get(ip)
        if mac:
            host["mac"] = mac
            vendor = vendor_for_mac(mac)
            if vendor:
                host["vendor"] = vendor

    ordered = sorted(hosts.values(), key=lambda h: tuple(int(x) for x in str(h["ip"]).split(".")))
    _attach_certificates(ordered, known_certs)
    return ordered


def _post_result(
    ingest_url: str,
    supervisor_token: str,
    probe_secret: str,
    hosts: list[dict[str, object]],
    tls_der: bool = False,
    presence: bool = False,
    gateway: str | None = None,
    networks_swept: list[str] | None = None,
) -> int:
    payload = json.dumps(
        {
            **({"netscan_gateway": gateway} if gateway else {}),
            **({"netscan_networks": networks_swept} if networks_swept is not None else {}),
            "netscan_result": hosts,
            "netscan_capabilities": {"tcp_connect": True, "tls_der": tls_der, "presence": presence},
            "scanner_version": SCANNER_VERSION,
            "probe_secret": probe_secret,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        ingest_url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {supervisor_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.URLError:
        return 0


def _parse_port_list(raw: str) -> list[int]:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = []
    ports: list[int] = []
    if isinstance(parsed, list):
        for item in parsed:
            try:
                port = int(item)
            except (TypeError, ValueError):
                continue
            if 1 <= port <= 65535 and port not in ports:
                ports.append(port)
    return ports[:MAX_PORT_LIST_ENTRIES]


def _post_trial(
    ingest_url: str, supervisor_token: str, probe_secret: str, trial: dict[str, object]
) -> int:
    payload = json.dumps(
        {"netscan_trial": trial, "scanner_version": SCANNER_VERSION, "probe_secret": probe_secret}
    ).encode("utf-8")
    request = urllib.request.Request(
        ingest_url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {supervisor_token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status
    except urllib.error.URLError:
        return 0


def _parse_known_certs(raw: str | None) -> set[str] | None:
    """The fingerprints the integration already holds, or None when it sent
    no list at all (see _attach_certificates). A malformed list is treated
    as empty rather than absent: the integration did ask for certificates."""
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return set()
    if not isinstance(parsed, list):
        return set()
    return {
        item
        for item in parsed[:MAX_KNOWN_CERTS]
        if isinstance(item, str) and _SHA256_HEX.match(item)
    }


def _parse_accepts(raw: str | None) -> set[str]:
    """The optional report fields the integration said it accepts. Anything
    malformed is treated as nothing, so the report keeps the old shape."""
    try:
        parsed = json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return set()
    return {item for item in parsed if isinstance(item, str)} if isinstance(parsed, list) else set()


def main() -> int:
    parser = argparse.ArgumentParser(description="HA SOC Probe netscan cycle")
    parser.add_argument("--ports", required=True, help="JSON list of TCP ports to sweep")
    parser.add_argument("--max-concurrency", type=int, default=32)
    parser.add_argument("--ingest-url", required=True)
    parser.add_argument(
        "--known-certs",
        default=None,
        help="JSON list of certificate SHA-256 fingerprints the integration already holds",
    )
    parser.add_argument(
        "--extra-networks",
        default=None,
        help="JSON list of further private IPv4 networks (/22 to /30) to sweep",
    )
    parser.add_argument("--trial-id", default=None, help="Sweep --trial-network once and report it")
    parser.add_argument("--trial-network", default=None)
    parser.add_argument(
        "--accepts",
        default=None,
        help="JSON list of optional report fields the integration accepts",
    )
    args = parser.parse_args()

    port_list = _parse_port_list(args.ports)
    if not port_list:
        print("netscan: empty or unparseable port list; nothing to do", file=sys.stderr)
        return 1
    max_concurrency = max(1, min(args.max_concurrency, MAX_CONCURRENCY_CAP))

    supervisor_token = os.environ.get("SUPERVISOR_TOKEN", "")
    probe_secret = os.environ.get("PROBE_SECRET", "")
    if not supervisor_token or not probe_secret:
        print("netscan: missing SUPERVISOR_TOKEN or PROBE_SECRET; refusing to run", file=sys.stderr)
        return 1

    if args.trial_id:
        # One network, swept once, reported apart from the regular result so
        # nothing about it reaches the inventory before the owner adds it.
        network, reason = _refusal_reason(args.trial_network, _container_networks())
        trial: dict[str, object] = {"id": args.trial_id, "network": str(args.trial_network)[:18]}
        if network is None:
            trial.update(refused=reason, hosts=[])
        else:
            trial["network"] = str(network)
            found = asyncio.run(
                _run_cycle(port_list, max_concurrency, set(), True, [network], only_extra=True)
            )
            trial.update(refused=None, hosts=found)
        print(json.dumps({"trial": trial["network"], "count": len(trial["hosts"])}))  # type: ignore[arg-type]
        status = _post_trial(args.ingest_url, supervisor_token, probe_secret, trial)
        if status not in (200, 201):
            print(f"netscan: trial POST returned status {status}", file=sys.stderr)
            return 1
        return 0

    known_certs = _parse_known_certs(args.known_certs)
    accepts = _parse_accepts(args.accepts)
    presence = ACCEPT_PRESENCE in accepts
    extra_networks = _parse_extra_networks(args.extra_networks)
    hosts = asyncio.run(
        _run_cycle(port_list, max_concurrency, known_certs, presence, extra_networks)
    )
    # The count only: the result now carries certificate bytes, and the host
    # list is a LAN map that does not belong in the app log.
    print(json.dumps({"count": len(hosts)}))

    status = _post_result(
        args.ingest_url,
        supervisor_token,
        probe_secret,
        hosts,
        tls_der=known_certs is not None,
        presence=presence,
        gateway=_default_gateway() if ACCEPT_GATEWAY in accepts else None,
        # Sent only when the integration asked for further networks, which only a
        # build that accepts this key does.
        networks_swept=[str(n) for n in extra_networks] if args.extra_networks else None,
    )
    if status not in (200, 201):
        print(f"netscan: ingest POST returned status {status}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
