# HA SOC frontend

Lit + TypeScript sidebar panel, bundled with Rollup — the same pattern
Alarmo and Browser Mod use. The built output (`dist/ha-soc-panel.js`) is
committed so HACS installs need no Node.js build step; only contributors
touching `src/` need to rebuild.

```bash
npm install
npm run build   # writes dist/ha-soc-panel.js
npm run watch   # rebuild on change, for local development
```

`custom_components/ha_soc/panel.py` serves `dist/ha-soc-panel.js` as a
static path and registers it as a custom panel via `panel_custom`. If the
bundle is missing, `panel.py` logs a warning and skips panel registration
rather than failing integration setup.
