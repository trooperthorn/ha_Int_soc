# Shopping list and setup guide

What to buy to run HA SOC with every feature lit up, and the order to set it
up in Home Assistant. The hardware below is what the code was built and
verified against (named in `UNIFI-LOCAL-API-CONTRACT.md`, `backlog.md`,
`operations.md` and `design.md`) plus the host it needs. Prices are rough
US street prices as of 2026 and are estimates, not quotes; check before
buying.

Nothing in tier 2 or 3 is required. HA SOC reports a missing source as "not
configured" or "not installed" rather than as empty, so you can start with
tier 1 and add the rest later.

## Tier 1: required

| Item | Why | Example | Approx. |
| --- | --- | --- | --- |
| Home Assistant host running **Home Assistant OS** | The Probe and Terminal add-ons need the Supervisor (HA OS or Supervised); on Core/Container those features show "not available". Both add-ons build for `amd64` and `aarch64` only. | x86 mini PC: Intel N100/N150, 16 GB RAM, 512 GB NVMe (Beelink EQ12/S12 Pro class) | $180–250 |
| UPS for the HA host and network gear | Crash Forensics exists because unclean host stops happen; a UPS removes the most common cause. Pair with HA's NUT integration. | APC Back-UPS BE600M1 or CyberPower CP685AVR | $70–90 |
| Wired Ethernet for the HA host | Probe port report, netscan and SNMP describe the host's real interfaces. | Cat6 patch cable | $10 |

Why not a Home Assistant Green: it works (aarch64, 4 GB), but HA SOC plus
the Probe, Terminal, a DNS add-on and the NVD/scanner jobs leave little
headroom, and the Resource Watchdog will spend its time warning about it.

## Tier 2: network visibility (Network, Network Security, Device SSH, Threat Management, Baseline tabs)

These tabs talk to a UniFi console's local Integration API (verified against
UniFi Network 10.4.57 and Protect 7.2.105) and to a DNS server.

| Item | Why | Verified on | Approx. |
| --- | --- | --- | --- |
| UniFi Cloud Gateway on UniFi OS with Network 10.x | Clients, devices, WAN, Firewall Policies, ACL Rules, configuration baseline, and the Suricata/Threat Management posture read over Device SSH | **UCG-Fiber** (UniFi OS 5.1.33). UCG-Ultra is the budget option; UCG-Max if you also want Protect on the same box | $130–280 |
| UniFi managed PoE switch | VLANs so there is a real IoT network for the Pi-hole scoping check and firewall findings to reason about; powers APs and cameras | USW-Lite-8-PoE or USW-Pro-Max-16-PoE | $110–400 |
| UniFi access point(s) | Wireless client and per-SSID counts; Wi-Fi join diagnostics over Device SSH | **U7 Pro** | $190 each |
| UniFi Device Bridge (optional) | Only if you need a wireless bridge; the SSH command allowlist covers its tools | **UDB Pro** | $100–150 |
| DNS filter host | Pi-hole v6 or Technitium DNS Server (both supported, configure either or both). Run it on its own box so DNS survives HA restarts | Raspberry Pi 5 4 GB + case, PSU, 64 GB SSD/SD | $110–140 |
| UniFi Protect (optional) | Protect status on the Network tab; `unifiprotect` is on the Security Integrations Health allowlist | UCG-Max/UNVR storage + a G5 Turret Ultra or G5 Bullet per location | $130+ per camera |

## Tier 3: physical security the Security Integrations Health card watches

The card tracks every `lock`, `siren` and `valve` entity, plus this curated
allowlist: Kidde HomeSafe, Elk-M1, Emporia Vue, UniFi Protect, Keymaster
(`operations.md`, `SECURITY_INTEGRATION_DOMAINS`). Buy what fits the house.

| Item | Integration | Example | Approx. |
| --- | --- | --- | --- |
| Z-Wave USB stick | Needed for Keymaster-managed locks; shows up in Local Peripherals | Home Assistant Connect ZWA-2 or Zooz ZST39 800LR | $35–70 |
| Zigbee USB stick (optional) | Sensors and sirens; shows up in Local Peripherals | Home Assistant Connect ZBT-2 | $50 |
| USB extension cable | Keeps radio sticks away from the host's USB 3 noise | 1 m USB 2.0 extension | $8 |
| Z-Wave smart lock(s) | `lock` entities, jammed/battery tracking, Keymaster code management | Schlage BE469ZP, Yale Assure Lock 2 Z-Wave | $180–280 each |
| Siren | `siren` entities | Zooz ZSE19 / Aeotec Siren 6 | $40–60 |
| Water shutoff valve (optional) | `valve` entities | Zooz ZAC36 Titan or Dome/EcoNet valve actuator | $150–300 |
| Kidde HomeSafe smoke/CO detectors | `kidde_homesafe` (HACS) | Kidde HomeSafe Smoke + CO combo | $60–80 each |
| Elk-M1 alarm panel (optional, usually installer-supplied) | `elkm1`; also feeds the Elk Programmer audit ingest | Elk-M1 Gold + M1XEP Ethernet interface | $500+ |
| Emporia Vue energy monitor (optional) | `emporia_vue` (HACS) | Emporia Vue 3 with 16 circuit sensors | $150–180 |

## Tier 4: optional extras

| Item | Why | Approx. |
| --- | --- | --- |
| Syslog/SIEM collector | SIEM export sends the hash-chained audit log as RFC 5424 (JSON or CEF) over TLS. Any collector works: Graylog, Wazuh, or a spare box running rsyslog. Can share the Raspberry Pi above for a small home | $0–80 |
| SNMP monitor | The Probe can export host metrics over SNMPv3 AuthPriv only (`SNMPV3.md`). Any NMS that speaks SNMPv3 | $0 |
| NVD API key | Faster CVE correlation for Device Vulnerabilities. Free from nvd.nist.gov | $0 |

## Rough totals

| Build | What it covers | Approx. |
| --- | --- | --- |
| Starter | Tier 1 only: users, audit, scanner, health, posture, logs, Probe, Terminal, crash forensics | $260–350 |
| Network | Starter + UCG-Ultra, 8-port PoE switch, one U7 Pro, Pi DNS | $750–950 |
| Full | Network + UCG-Fiber/UCG-Max, Protect cameras, Z-Wave stick, two locks, siren, Kidde detectors | $1,800–2,800 before an alarm panel |

## Putting it into Home Assistant

Do these in order; each step unlocks the next set of tabs.

### 1. Host and base install

1. Flash Home Assistant OS to the mini PC's NVMe (balenaEtcher or the HA OS
   installer USB), boot, finish onboarding. The account you create first is
   the **owner**; HA SOC's panel defaults to owner-only.
2. Update to Home Assistant **2026.9.0 or newer** (the minimum in `hacs.json`).
3. Turn on MFA for the owner account now (Profile → Multi-factor
   authentication). HA SOC's MFA policy will otherwise flag it.
4. Plug the UPS USB cable into the host and add the **NUT** add-on and
   integration so a power loss is a clean shutdown, not a Crash Forensics
   bundle.

### 2. Install HA SOC

1. Install HACS, then HACS → ⋮ → Custom repositories → add
   `https://github.com/trooperthorn/ha_Int_soc` as type **Integration**, and
   download **HA SOC**. (Or copy `custom_components/ha_soc/` into
   `config/custom_components/`.)
2. Restart Home Assistant.
3. Settings → Devices & Services → Add Integration → **HA SOC**.
4. A **SOC** panel appears in the sidebar. Open Settings in it and paste the
   NVD API key.

### 3. Add the Probe and Terminal add-ons

1. Settings → Add-ons → Add-on Store → ⋮ → Repositories → add the same
   repository URL.
2. Install **HA SOC Probe** and start it. It pairs itself on first report;
   the Scanner tab shows host listening ports within one scan interval.
3. Install **HA SOC Terminal** if you want the recorded terminal in the panel.
4. Leave the Probe's Protection Mode **on** unless you want Resource Watchdog
   hard CPU/memory caps; those need it off (see `RESOURCE-WATCHDOG.md`).

### 4. Network

1. Build the network in UniFi: separate VLANs for Trusted, IoT and Cameras,
   and zone-based Firewall Policies (Settings → Security → Create Policy).
   Point the IoT network's DHCP DNS at the Pi-hole/Technitium box.
2. Install Pi-hole v6 or Technitium on the Raspberry Pi. Give the IoT subnet
   its own Pi-hole client group, which the Network Security tab checks for.
3. In UniFi: Local Site → Settings → Integrations → create a **local API
   key** (read-only). Create a second one for Protect if you have it.
4. In the SOC panel's Settings: enter the UniFi Network host + key, the
   Protect host + key, the Pi-hole host + app password (Pi-hole → Settings →
   API → App password) and/or the Technitium host + API token
   (Administration → Sessions → Create token), and the **IoT network CIDR**.
5. Device SSH (optional, owner-only, off by default): turn it on in Settings,
   copy the Ed25519 public key it shows, and paste it into the UniFi
   controller's device SSH key setting so it pushes the key to every adopted
   device. Host keys are pinned on first use.
6. Also add Home Assistant's own **UniFi Network** and **UniFi Protect**
   integrations; HA SOC correlates their config-entry hosts against UniFi
   clients to flag "integration IP failing".

### 5. Physical security devices

1. Plug the Z-Wave (and Zigbee) stick in via the extension cable. Add the
   **Z-Wave JS** (and **ZHA**) integration; the stick appears in HA SOC's
   Local Peripherals with its assigned integration.
2. Pair locks, sirens and valves. Install **Keymaster** from HACS for lock
   codes.
3. Install **Kidde HomeSafe** and **Emporia Vue** from HACS; add **Elk-M1**
   (core integration) pointed at the M1XEP.
4. In SOC Settings → Security Integrations Health, confirm each source shows
   as installed and toggled on. Any automation that sends `notify.*` from one
   of these sources while it is toggled off is raised as a HIGH "notify
   coverage gap".

### 6. Export and monitoring (optional)

1. SIEM & Audit → enable syslog export, pick TLS, format (RFC 5424 JSON or
   CEF), and the collector host.
2. SNMPv3: set the user, SHA-256 auth and AES privacy secrets and an explicit
   bind address in SOC Settings; the Probe picks them up on its next poll.
3. Set up an HA mobile app notification for new HIGH detections.

### 7. First-week checklist

- Accept a **UniFi configuration baseline** once the network is how you want
  it, so later drift is visible.
- Run the Integration Security scanner and confirm or dismiss findings.
- Work the Repairs items HA SOC raises (cleartext HTTP, `trusted_networks`,
  backup protection and so on).
- Check that the posture grade is no longer marked **provisional**; if it is,
  the missing terms are listed next to it.

## Keeping the list in Home Assistant

To track purchases inside HA, create a to-do list (Settings → Devices &
Services → Add Integration → **Local To-do**, name it `SOC build`) and run
this script once from Developer tools → Actions (YAML mode). Edit the items
to match what you actually plan to buy.

```yaml
action: todo.add_item
target:
  entity_id: todo.soc_build
data:
  item: "Mini PC N100 16GB/512GB (HA OS host)"
```

Or add everything at once as a script:

```yaml
alias: Load SOC shopping list
sequence:
  - repeat:
      for_each:
        - "Mini PC N100 16GB/512GB (HA OS host)"
        - "UPS (APC BE600M1)"
        - "UniFi Cloud Gateway (UCG-Ultra / UCG-Fiber)"
        - "UniFi PoE switch (USW-Lite-8-PoE)"
        - "UniFi U7 Pro access point"
        - "Raspberry Pi 5 kit for Pi-hole/Technitium"
        - "Z-Wave stick (ZWA-2 / ZST39) + USB extension"
        - "Z-Wave lock (Schlage BE469ZP / Yale Assure 2)"
        - "Z-Wave siren"
        - "Kidde HomeSafe smoke/CO detectors"
        - "UniFi Protect camera(s)"
      sequence:
        - action: todo.add_item
          target:
            entity_id: todo.soc_build
          data:
            item: "{{ repeat.item }}"
```
