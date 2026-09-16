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
     presented, not to validate a chain).
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
import fcntl
import ipaddress
import json
import os
import re
import socket
import ssl
import struct
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from oui_prefixes import vendor_for_mac

SCANNER_VERSION = "netscan/1.0"

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

# Ports where a TLS handshake is attempted after (or instead of) a plaintext
# banner read; anything not in this set is never wrapped in TLS.
TLS_TYPICAL_PORTS = frozenset({443, 8443, 993, 995, 465, 636, 8883, 9443})

# A small, curated, explicitly non-exhaustive set of banner signatures.
# Matched against whatever plaintext was read (and, for TLS ports, an empty
# string when only a certificate came back); first match wins.
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
]


def _guess_service(text: str) -> str | None:
    for name, pattern in SERVICE_SIGNATURES:
        if pattern.search(text):
            return name
    return None


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
    is to read whatever is presented, not to validate a chain."""
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
        cert = ssl_object.getpeercert() if ssl_object is not None else None
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
    if not cert:
        # A handshake with no leaf certificate available (anonymous cipher,
        # or getpeercert() unsupported for this connection) still proves TLS.
        return {"subject": None, "issuer": None, "not_after": None, "self_signed": None}
    subject = ", ".join(
        f"{k}={v}" for pair in cert.get("subject", ()) for k, v in pair
    ) or None
    issuer = ", ".join(
        f"{k}={v}" for pair in cert.get("issuer", ()) for k, v in pair
    ) or None
    self_signed = bool(subject and issuer and subject == issuer)
    return {
        "subject": subject,
        "issuer": issuer,
        "not_after": cert.get("notAfter"),
        "self_signed": self_signed,
    }


async def _probe_one(
    ip: str, port: int, semaphore: asyncio.Semaphore
) -> dict[str, object] | None:
    async with semaphore:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port), timeout=CONNECT_TIMEOUT_SECONDS
            )
        except (asyncio.TimeoutError, OSError):
            return None
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

    entry: dict[str, object] = {"port": port}
    if banner:
        entry["banner"] = banner.strip()
    service_guess = _guess_service(banner) or ("tls" if tls_info is not None else None)
    if service_guess:
        entry["service_guess"] = service_guess
    if tls_info is not None:
        entry["tls"] = tls_info
    return entry


async def _run_cycle(port_list: list[int], max_concurrency: int) -> list[dict[str, object]]:
    arp_table = _read_arp_table()
    networks = _local_ipv4_networks()
    targets = _sweep_targets(networks, set(arp_table))

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
        host = hosts.setdefault(ip, {"ip": ip, "open_ports": []})
        host["open_ports"].append(entry)  # type: ignore[union-attr]

    # Include ARP-known hosts with no open port in the configured list too,
    # so the panel can show "seen on the network, nothing scanned open"
    # rather than silently dropping them.
    for ip in arp_table:
        hosts.setdefault(ip, {"ip": ip, "open_ports": []})

    for ip, host in hosts.items():
        mac = arp_table.get(ip)
        if mac:
            host["mac"] = mac
            vendor = vendor_for_mac(mac)
            if vendor:
                host["vendor"] = vendor

    return sorted(hosts.values(), key=lambda h: tuple(int(x) for x in str(h["ip"]).split(".")))


def _post_result(
    ingest_url: str, supervisor_token: str, probe_secret: str, hosts: list[dict[str, object]]
) -> int:
    payload = json.dumps(
        {
            "netscan_result": hosts,
            "netscan_capabilities": {"tcp_connect": True},
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


def main() -> int:
    parser = argparse.ArgumentParser(description="HA SOC Probe netscan cycle")
    parser.add_argument("--ports", required=True, help="JSON list of TCP ports to sweep")
    parser.add_argument("--max-concurrency", type=int, default=32)
    parser.add_argument("--ingest-url", required=True)
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

    hosts = asyncio.run(_run_cycle(port_list, max_concurrency))
    print(json.dumps({"hosts": hosts, "count": len(hosts)}))

    status = _post_result(args.ingest_url, supervisor_token, probe_secret, hosts)
    if status not in (200, 201):
        print(f"netscan: ingest POST returned status {status}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
