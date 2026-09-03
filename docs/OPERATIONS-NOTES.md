# Operations Notes

Transport and platform quirks discovered while integrating with Home
Assistant Supervisor and related local services, kept here so the reasoning
behind a workaround survives past the commit that added it.

## Container log fetch via the Supervisor journald gateway

Neither `aiohasupervisor` 0.3.x nor the HassIO handler exposes a dedicated
log-fetching method. Supervisor's journald gateway does serve plain-text
logs at fixed paths (`addons/<slug>/logs`, `core/logs`, `supervisor/logs`,
`host/logs`), reached in `custom_components/ha_soc/logs.py` through the
`hassio` component's own `send_command` with `return_text=True`, the same
transport Core's own proxy view uses for its frontend.

Two constraints of that route are handled in `logs.py` rather than
surprising the panel:

- **No `Range` header is possible**, so there is no server-side line count.
  The full text is fetched and tail-capped afterward
  (`_MAX_CONTAINER_LOG_BYTES`).
- **journald colors its output** with ANSI SGR escapes, which are stripped
  before the text is returned to the panel (`_ANSI_SGR_RE`).
