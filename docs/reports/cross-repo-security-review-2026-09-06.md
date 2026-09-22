# Cross-repository security review, trooperthorn HA repositories, 2026-09-06

Scope: all 19 GitHub repositories named ha_*, ha-*, HA-* (HA-net-snmpd is a
2024 fork with no local clone and was not reviewed). Each local clone under
~/repos was fast-forwarded to origin/main before scanning. Method: source
grep and manual read for the TLS class of defect found in ha_int_elkm1, plus
certificate verification defaults, plaintext transports, credential handling
(config flow masking, logging, diagnostics), command construction, workflow
pinning and permissions, app privileges, repository hygiene, a full-history
scan for credential-shaped strings, and the GitHub code-scanning and
secret-scanning alert APIs.

## 1. The ha_int_elkm1 defect class (weakened OpenSSL context)

Property: no SSL context anywhere lowers the cipher floor (SECLEVEL=0),
re-enables legacy renegotiation (OP_LEGACY_SERVER_CONNECT), pins TLS 1.0 or
1.1, or defaults a user to a downgraded protocol.

Result: not present in any repository. Zero matches for set_ciphers,
SECLEVEL, OP_LEGACY_SERVER_CONNECT, PROTOCOL_TLSv1*, or minimum_version
downgrades outside the ha_int_elkm1 docs. ha_int_elkm1 removed the network
transport entirely (commit 8d05665, PR #29) and documented it in the README
(commit bcb1868, PR #31); both are on main. The only hand-built SSLContext
left in the portfolio is ha_Int_soc syslog_export.py:610, which uses
PROTOCOL_TLS_CLIENT with the Python default floor (TLS 1.2) and no cipher
changes.

## 2. Certificate verification disabled by default (CWE-295)

### 2.1 ha_app_kiosk: ignore_certificate_errors defaults to true. MEDIUM, advisory
- wayland-kiosk/config.yaml options: `ignore_certificate_errors: true`;
  run.sh:142 reads it with default 'true'; launch-browser.sh:34 passes
  `--ignore-certificate-errors` to Chromium.
- That Chromium flag disables certificate validation for every origin the
  browser loads, not only ha_url. With the shipped ha_url
  (http://127.0.0.1:8123) it is inert, but any https ha_url gets no
  verification unless the user turns the option off.
- docs/security.md does not mention the option.
- Fix: default false; document that a self-signed HA certificate needs the
  option turned on deliberately. Test: assert the generated Chromium argv
  omits the flag when the option is absent.

### 2.2 ha_Int_soc: UniFi and Pi-hole verify_ssl default False. LOW, documented decision
- const.py:100 DEFAULT_UNIFI_VERIFY_SSL = False, const.py:110
  DEFAULT_PIHOLE_VERIFY_SSL = False. UI labels both "Off by default"
  (settings-view.ts:412-500); docs/decisions.md 2026-09-03 and
  docs/operations.md record the reasoning (consoles ship self-signed
  certificates, same default as the core unifi integration).
- The unverified path goes through HA async_get_clientsession(verify_ssl=False),
  which keeps the HA TLS 1.2+ context; this is verification off, not the
  elkm1 cipher-floor class.
- Syslog TLS verification defaults True (const.py:65).
- Option: keep the default but raise a health finding while either toggle is
  off, so the dashboard that audits everyone else's transport security also
  reports its own.

### 2.3 ha_app_dynglance: InsecureSkipVerify is opt-in. CLEAN
- widget-utils.go:64 and config-fields.go:370 set InsecureSkipVerify only
  when a widget or proxy sets `allow-insecure`; the default client verifies.
- widget-reddit.go:382-399 uses refraction-networking/utls to mimic a
  Firefox handshake (inherited from upstream Glance). ServerName is set and
  InsecureSkipVerify is not, so verification stays on. Supply-chain note
  only: utls is a fingerprint-spoofing library and is pinned by go.sum.

### 2.4 ha_int_SWIS. CLEAN
- DEFAULT_VERIFY_SSL = True (const.py:11); password uses
  TextSelectorType.PASSWORD; verify flag passed to both the HA session and
  the per-request ssl= argument.

### 2.5 ha_int_airthings scripts/probe_airthings_view.py:81-83. INFORMATIONAL
- ssl.CERT_NONE in a developer LAN probe script under scripts/, not in the
  shipped integration.

## 3. Local control endpoints with optional authentication (CWE-306, CWE-319)

### 3.1 ha_int_SleepNumb on-hub bridge. MEDIUM, advisory
- bridge/sleepnumber_bridge.py:47 TOKEN = env SNB_TOKEN, default empty;
  _authorized() returns True when TOKEN is empty (line 110); the server
  binds 0.0.0.0:8765 (line 149) over plaintext HTTP; /raw drives the pump.
- bridge/README.md:37 already states the consequence ("without it any
  device on the LAN can drive the pump"). Argument construction is safe:
  allowlisted keys, character-filtered args, shell=False (lines 62-93).
- Integration side local.py:71-72 talks http:// and sends the token in a
  header, so the shared secret crosses the LAN in clear.
- Fix: refuse to start without SNB_TOKEN (or generate one and print it once),
  and bind to the hub LAN interface rather than all interfaces. Test:
  starting the bridge with SNB_TOKEN unset exits non-zero.

### 3.2 ha_app_kiosk REST control API. LOW, documented
- rest_server.py:455 binds 127.0.0.1:8034; api_token optional (line 49) and
  documented in docs/security.md as the loopback-scoped boundary. Because the
  app runs with host_network: true, loopback is the HAOS host loopback,
  so any process on the host can drive the API when api_token is unset.
- run.sh:355 passes the HA password as a wtype argument, which exposes it on
  the process command line inside the container for the duration of the
  keystroke replay. Prefer wtype reading from stdin.

### 3.3 ha_app_dynglance direct port. LOW, advisory
- ha-addon/dynglance/config.yaml publishes 8080/tcp on the host by default
  while DynGlance auth is off unless the user adds an auth: section;
  DOCS.md:98-103 recommends relying on Ingress. Anyone on the LAN reaches
  the dashboard on :8080 without HA authentication.
- Fix: ship `8080/tcp: null` so direct access is opt-in.

## 4. Credential fields declared as plain `str` in config flows (CWE-549). LOW, unverified
The same class the elkm1 PR #29 fixed (PIN and password masking). These
flows rely on the frontend masking by field name instead of declaring a
password selector:
- ha_int_SleepNumb config_flow.py:31, 170 (CONF_PASSWORD: str)
- ha_int_emporia config_flow.py:356 (CONF_ACCESS_TOKEN), 369 (CONF_PASSWORD)
- ha_int_kidde config_flow.py:48 (CONF_PASSWORD)
- ha_int_phyn config_flow.py:43, 47 (CONF_PASSWORD)
- ha_int_bond config_flow.py:30-34 (CONF_ACCESS_TOKEN)
Unverified: the frontend name-based masking list could not be checked
against a local source (the built frontend is not in the sparse core clone).
Explicit TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
removes the dependency on that heuristic.

## 5. Checks that came back clean
- Secrets in logs: no logger call includes a password, token, key, or PIN.
- Diagnostics: soc, emporia, elkm1, bond, kidde, phyn, davis, monoprice,
  sleepnumb, airthings, homekit redact; yamaha_ynca dumps entry.as_dict()
  but its entry holds only host, port, serial_url; BTSensors dumps the last
  BLE advertisement only.
- Command construction: every subprocess call uses an argv list with no
  shell; kiosk and SleepNumb allowlist the executable. No eval, exec,
  pickle, or unsafe yaml.load in shipped code.
- Workflows: every `uses:` is SHA-pinned, every workflow has a permissions
  block, none use pull_request_target or interpolate event text into run:.
- Repository hygiene: SECURITY.md, dependabot.yml, and CODEOWNERS present in
  all 19. No repo has a gitleaks hook or CI job (baseline gap, optional).
- Git history: zero credential-shaped strings (GitHub PATs, AWS keys, PEM
  private keys, Slack tokens, JWTs) across all branches of all 19 repos.
- GitHub alerts: code scanning 0 open on all 19; secret scanning 0 open on
  18 and disabled on ha_card_music (enable it in Settings > Code security).

## 6. Not verified
- Dependabot alerts: the gh token lacks the scope the API requires. Run
  `gh auth refresh -h github.com -s admin:repo_hook` and re-query, or read
  each repo Security tab.
- HA-net-snmpd (2024 fork, no local clone) was not reviewed.
