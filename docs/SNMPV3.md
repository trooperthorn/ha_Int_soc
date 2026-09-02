# SNMPv3 monitoring export

HA SOC can run a Net-SNMP agent inside the optional Probe add-on. This is a
valid way to feed SolarWinds and other monitoring/observability platforms
because the Probe shares the Home Assistant host's network namespace. It is
not implemented in the Core integration: a Home Assistant integration cannot
bind a host socket or observe host interfaces from its own container.

## Security contract

- Disabled by default.
- SNMPv3 USM AuthPriv only: HMAC-SHA-256 authentication and AES-128 privacy.
- Read-only `rouser`; no `rwuser`, community string, SNMPv1/v2c, or SET access.
- Exact assigned listener IP and explicit port; wildcard addresses are rejected
  by Core and revalidated by the Probe.
- Authentication and privacy passphrases must be different, 20-128 characters,
  and are stored in HA SOC's private atomic secret store. The authenticated
  Probe receives them only when its configuration generation changes.
- Net-SNMP consumes the temporary mode-0600 `createUser` record and persists
  engine-localized keys in the Probe's private `/data` volume. Disabling the
  service deletes that localized identity. The daemon has a dedicated
  `ha_soc_snmp` account, so the unprivileged port scanner cannot read its key
  database.
- The VACM view contains only the system, interface, selected storage/processor,
  and UCD CPU/memory subtrees. Process and installed-software tables are not
  exposed.
- Restrict UDP/161 (or the selected port) to monitoring sources with a VLAN ACL
  or upstream firewall. AuthPriv protects the SNMP payload, but source filtering
  still reduces attack surface and discovery noise.

The protocol basis is SNMPv3 USM ([RFC 3414](https://www.rfc-editor.org/rfc/rfc3414)),
HMAC-SHA-2 for USM ([RFC 7860](https://www.rfc-editor.org/rfc/rfc7860)), and
AES-CFB-128 privacy ([RFC 3826](https://www.rfc-editor.org/rfc/rfc3826)). Net-SNMP's
agent configuration behavior is documented in its
[`snmpd.conf` manual](https://www.net-snmp.org/docs/man/snmpd.conf.html).

## Exposed MIB objects

Table objects require an instance suffix: `.ifIndex` for IF-MIB rows and
`.hrStorageIndex` for HOST-RESOURCES rows. Scalars require `.0`.

| Purpose | Object | OID / calculation |
| --- | --- | --- |
| Interface identity | `ifName`, `ifAlias` | `.1.3.6.1.2.1.31.1.1.1.1.<ifIndex>`, `.18.<ifIndex>` |
| State and speed | `ifAdminStatus`, `ifOperStatus`, `ifHighSpeed` | `.1.3.6.1.2.1.2.2.1.7/.8.<ifIndex>`, `.1.3.6.1.2.1.31.1.1.1.15.<ifIndex>` |
| Errors/discards | `ifInDiscards`, `ifInErrors`, `ifOutDiscards`, `ifOutErrors` | `.1.3.6.1.2.1.2.2.1.13/.14/.19/.20.<ifIndex>` |
| 64-bit input | `ifHCInOctets`, `ifHCInUcastPkts`, `ifHCInMulticastPkts`, `ifHCInBroadcastPkts` | `.1.3.6.1.2.1.31.1.1.1.6/.7/.8/.9.<ifIndex>` |
| 64-bit output | `ifHCOutOctets`, `ifHCOutUcastPkts`, `ifHCOutMulticastPkts`, `ifHCOutBroadcastPkts` | `.1.3.6.1.2.1.31.1.1.1.10/.11/.12/.13.<ifIndex>` |
| Counter reset detection | `ifCounterDiscontinuityTime` | `.1.3.6.1.2.1.31.1.1.1.19.<ifIndex>` |
| Processor | `hrProcessorLoad` | `.1.3.6.1.2.1.25.3.3.1.2.<index>` |
| Memory, KiB | `memTotalReal`, `memAvailReal` | `.1.3.6.1.4.1.2021.4.5.0`, `.1.3.6.1.4.1.2021.4.6.0` |
| CPU raw ticks | `ssCpuRawIdle` | `.1.3.6.1.4.1.2021.11.53.0` |
| Storage row | `hrStorageIndex` through `hrStorageAllocationFailures` | `.1.3.6.1.2.1.25.2.3.1.1` through `.7`, each with `.<hrStorageIndex>` |

The IF-MIB definitions and counter behavior come from
[RFC 2863](https://www.rfc-editor.org/rfc/rfc2863). The HC values are cumulative
`Counter64` objects, not bandwidth. A collector calculates traffic rate from
the delta between polls, rejects a sample when `ifCounterDiscontinuityTime`
changes, and compares the result with `ifHighSpeed` (in units of 1,000,000
bits/second).

The storage calculation is defined by
[HOST-RESOURCES-MIB / RFC 2790](https://www.rfc-editor.org/rfc/rfc2790):

```text
capacity_bytes = hrStorageAllocationUnits * hrStorageSize
used_bytes     = hrStorageAllocationUnits * hrStorageUsed
capacity_GiB   = capacity_bytes / 1024^3
capacity_GB    = capacity_bytes / 1000^3
```

Do not divide `hrStorageSize` by 1024 on its own. Net-SNMP may increase the
allocation-unit size so large filesystems remain representable in the MIB's
32-bit integer. Binary or decimal display is a collector/UI choice after byte
calculation, not an ambiguity in the MIB.

`memTotalReal`, `memAvailReal`, and the `ssCpu*` family are Net-SNMP's UCD-SNMP
enterprise objects, not IETF-standard MIB objects. Net-SNMP marks `ssCpuIdle`
`.1.3.6.1.4.1.2021.11.11.0` deprecated; use `ssCpuRawIdle` deltas or
`hrProcessorLoad`. See the [Net-SNMP UCD object reference](https://www.net-snmp.org/docs/mibs/ucdavis.html).

## Scope boundary

- IF-MIB values describe the Home Assistant host's actual interfaces because
  the Probe uses `host_network: true`.
- Kernel CPU and memory sources are shared with the host, but must still be
  verified on the deployed HAOS/Supervisor version.
- `hrStorageTable` describes filesystems mounted into the Probe container. It
  must not be presented as complete HAOS host-volume inventory. Expanding that
  scope would require another host mount or namespace privilege and is deferred
  until its security benefit justifies that access.
- No custom/private HA SOC MIB is shipped in this phase. Every exposed object is
  from an existing standard or Net-SNMP-provided MIB.

## Configure and validate

In HA SOC **Settings → SNMPv3 Telemetry**, enter the exact Home Assistant IP,
port, security name, and two distinct passphrases, then enable the service.
Use the same security parameters in the monitoring platform.

From a trusted management host with Net-SNMP tools:

```sh
snmpget -v3 -l authPriv -u solarwinds_sem -a SHA-256 -A 'AUTH_PASSPHRASE' \
  -x AES -X 'PRIV_PASSPHRASE' 192.168.30.3 1.3.6.1.2.1.1.3.0

snmpwalk -v3 -l authPriv -u solarwinds_sem -a SHA-256 -A 'AUTH_PASSPHRASE' \
  -x AES -X 'PRIV_PASSPHRASE' 192.168.30.3 1.3.6.1.2.1.31.1.1
```

Negative tests are required before treating deployment as complete:

1. SNMPv1 and SNMPv2c/community queries time out.
2. SNMPv3 `authNoPriv` and `noAuthNoPriv` queries fail.
3. A valid AuthPriv GET succeeds from the management VLAN.
4. The same GET is blocked from an unapproved VLAN by the network ACL.
5. A SET request fails, and a walk outside the documented VACM subtrees is denied.
6. After disabling the feature, UDP/161 no longer appears at the configured IP.

These are live-environment checks; CI can prove configuration generation,
credential masking, script policy, and package/build behavior, but cannot prove
your VLAN ACL or the deployed HAOS namespace view.
