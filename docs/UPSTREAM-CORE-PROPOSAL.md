# Draft: observable authentication and authorization events for Home Assistant core

Status: DRAFT for owner review (work plan decision D-22, recorded 2026-08-30).
Nothing in this repository files this anywhere; the text exists so the owner
can review, amend, and submit it to the Home Assistant architecture
discussion forum if and when they choose.

## Problem

Security tooling running inside Home Assistant (as an integration) cannot
observe three classes of authentication and authorization activity, because
core neither fires an event nor writes a structured log record for them.
All three statements below were verified against core 2026.2.3 source:

1. **Failed logins carry no username.** The only artifact of a failed login
   is a WARNING on the `http.ban` logger, formatted as a single string with
   the remote host, address, and requested URL. The attempted username is
   never logged or exposed anywhere (`components/http/ban.py`). An operator
   can see that someone is guessing, but never which account is being
   targeted, so account-targeted lockout or alerting is impossible to build.
2. **Permission denials are invisible.** A WebSocket command or service
   call that fails an admin or policy check raises `Unauthorized`, which is
   reported to the caller and nowhere else. No event fires, no dedicated
   logger records it. A user probing for reachable admin surface leaves no
   trail.
3. **Long-lived access token use is invisible on success.** Refresh-token
   `last_used_at`/`last_used_ip` update only on the `/auth/token` grant
   path. A bearer LLAT is validated by `async_validate_access_token`, a
   pure callback with no side effects, so successful LLAT use, the exact
   credential class most often exfiltrated, produces no signal at all.

## Proposal

Three additive, low-volume bus events, all fired from code paths that
already exist, none changing any behavior:

### `auth_failed`

Fired where `process_wrong_login` runs today. Data:

- `provider`: the auth provider type string (`homeassistant`,
  `trusted_networks`, ...), when the flow knows it.
- `username_hash`: SHA-256 of the attempted username, salted with a
  per-install random value generated once and stored with core's other
  auth data. The hash lets tooling correlate repeated attacks on one
  account and compare against the install's own (identically hashed) user
  list, without core ever persisting or emitting the raw attempted string,
  which may itself be a password typed into the wrong field.
- `remote_ip`, `request_path`: what the ban logger already exposes.

### `permission_denied`

Fired where `Unauthorized` is converted into a client error (the WebSocket
connection's exception handler and the HTTP equivalent). Data: `user_id`,
`surface` (`websocket` or `http`), the command type or path, and the
permission that failed. Volume is bounded by how often clients err;
a burst of these from one user is precisely the signal worth having.

### `token_used` (rate-limited)

Fired at most once per refresh token per configurable interval (default
once per hour) from access-token validation, carrying `token_id`,
`token_type`, and `remote_ip` when a request context exists. The rate
limit keeps the bus quiet while making an exfiltrated LLAT's use visible
within the hour instead of never. Updating `last_used_at` for LLATs on
the same rate-limited path would fix the stale "last used" display in the
profile UI as a side effect.

## Why events and not logs

Log lines are string-formatted, level-gated, and rotated; integrations
parsing them are brittle by construction (this project parses the ban
logger's string today and documents that as a weakness). Bus events are
the mechanism core already uses for every other observable state change,
they carry structure, and listeners opt in.

## Privacy posture

Nothing in this proposal emits a secret or a raw attempted username. The
salted hash in `auth_failed` is deliberately not reversible and not
comparable across installs. `token_used` carries the token id, which is
already visible to its owner in the profile UI, never the token itself.

## Prior art in this repository

HA SOC (github.com/trooperthorn/ha_Int_soc) documents all three gaps as
structural limitations in its audit module docstring and compensates with
weaker signals (log parsing for failures, a token-grant poll, first-seen
session records). Those workarounds are the evidence that the demand
exists and that the gaps cannot be closed from integration land.
