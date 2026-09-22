import { LitElement, html, css, nothing, unsafeCSS } from "lit";
import { customElement, property, state, query } from "lit/decorators.js";
import { Terminal, type ITheme } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import { xtermCss } from "../generated/xterm-css";
import {
  TerminalStatus,
  TerminalOpenResult,
  TerminalEvent,
  TerminalRunResult,
  TerminalExportKind,
  fetchTerminalStatus,
  openTerminal,
  sendTerminalInput,
  resizeTerminal,
  closeTerminal,
  controlTerminalApp,
  forgetTerminalPairing,
  runTerminalCommand,
  fetchTerminalTranscript,
  sendTerminalExportEvent,
  fetchAccessInfo,
} from "../data/ha-soc-ws";
import { sha256Hex, byteLength, lineCount, copyText, downloadText, utcStamp, stripAnsi } from "../data/export-helpers";

const RUN_TIMEOUTS = [30, 60, 120];
const MAX_COMMAND_HISTORY = 10;
const FEEDBACK_MS = 3000;

/**
 * The HA SOC Terminal, rendered in the panel.
 *
 * The browser never talks to the app. Keystrokes go to the integration as
 * base64 over `ha_soc/terminal/input`; output arrives as events on the open
 * command's subscription; the integration holds the one connection to ttyd.
 * Closing this view, navigating away, or losing the WebSocket ends the
 * session server-side and writes the close record (docs/TERMINAL-DESIGN.md).
 *
 * The palette is built from Home Assistant's theme variables so the terminal
 * follows light and dark and any custom theme, and rebuilt when `hass`
 * changes.
 */

const encoder = new TextEncoder();
const decoder = new TextDecoder();

const toBase64 = (text: string): string => {
  const bytes = encoder.encode(text);
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary);
};

const fromBase64 = (data: string): Uint8Array => {
  const binary = atob(data);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes;
};

const REASONS: Record<string, string> = {
  user_closed: "You closed the session.",
  remote_closed: "The shell exited.",
  connection_lost: "The connection to Home Assistant was lost.",
  max_duration: "The session reached its maximum duration.",
  unloaded: "HA SOC was reloaded.",
  error: "The session ended with an error.",
};

// Fallback palette, the same one phase 1 used on ttyd's own page.
const FALLBACK: ITheme = {
  background: "#1c2128",
  foreground: "#e6edf3",
  cursor: "#58a6ff",
  selectionBackground: "#264f78",
  black: "#484f58",
  red: "#ff7b72",
  green: "#3fb950",
  yellow: "#d29922",
  blue: "#58a6ff",
  magenta: "#bc8cff",
  cyan: "#39c5cf",
  white: "#b1bac4",
  brightBlack: "#6e7681",
  brightRed: "#ffa198",
  brightGreen: "#56d364",
  brightYellow: "#e3b341",
  brightBlue: "#79c0ff",
  brightMagenta: "#d2a8ff",
  brightCyan: "#56d4dd",
  brightWhite: "#f0f6fc",
};

// Font choices offered in the header. "theme" resolves Home Assistant's
// --ha-font-family-code token (plain `monospace` unless a theme sets it);
// the rest are families common on Windows, macOS and Linux. Nothing is
// bundled: a family renders only when the viewing machine has it, so the
// list marks each one installed or not by measuring it.
type FontChoice = { id: string; label: string; stack: string };
const FONT_CHOICES: FontChoice[] = [
  { id: "theme", label: "Theme code font", stack: "" },
  { id: "cascadia", label: "Cascadia Mono", stack: "'Cascadia Mono', 'Cascadia Code'" },
  { id: "consolas", label: "Consolas", stack: "Consolas" },
  { id: "jetbrains", label: "JetBrains Mono", stack: "'JetBrains Mono'" },
  { id: "fira", label: "Fira Code", stack: "'Fira Code', 'Fira Mono'" },
  { id: "menlo", label: "Menlo / SF Mono", stack: "Menlo, 'SF Mono'" },
  { id: "roboto", label: "Roboto Mono", stack: "'Roboto Mono'" },
  { id: "dejavu", label: "DejaVu Sans Mono", stack: "'DejaVu Sans Mono'" },
  { id: "courier", label: "Courier New", stack: "'Courier New'" },
  { id: "mono", label: "Browser monospace", stack: "monospace" },
];
const GENERIC_TAIL = "Consolas, 'DejaVu Sans Mono', 'Courier New', monospace";
const FONT_SIZES = [11, 12, 13, 14, 15, 16, 18, 20];
const LINE_HEIGHTS = [1, 1.1, 1.2, 1.3, 1.4];
const PREFS_KEY = "ha_soc.terminal.font";

type FontPrefs = { family: string; size: number; lineHeight: number };
const DEFAULT_PREFS: FontPrefs = { family: "theme", size: 14, lineHeight: 1.2 };

const loadPrefs = (): FontPrefs => {
  try {
    const raw = window.localStorage.getItem(PREFS_KEY);
    if (!raw) return { ...DEFAULT_PREFS };
    const p = JSON.parse(raw) as Partial<FontPrefs>;
    return {
      family: FONT_CHOICES.some((f) => f.id === p.family) ? (p.family as string) : DEFAULT_PREFS.family,
      size: FONT_SIZES.includes(p.size as number) ? (p.size as number) : DEFAULT_PREFS.size,
      lineHeight: LINE_HEIGHTS.includes(p.lineHeight as number)
        ? (p.lineHeight as number)
        : DEFAULT_PREFS.lineHeight,
    };
  } catch {
    return { ...DEFAULT_PREFS };
  }
};

const savePrefs = (p: FontPrefs) => {
  try {
    window.localStorage.setItem(PREFS_KEY, JSON.stringify(p));
  } catch {
    // Private window or storage blocked; the choice lasts for this page.
  }
};

// document.fonts.check() answers "nothing left to load", which is true for
// any system family whether or not it exists, so installation is detected
// the classic way: a family that is present changes the measured width
// against at least one generic fallback.
const fontInstalledCache = new Map<string, boolean>();
const isFontInstalled = (family: string): boolean => {
  const cached = fontInstalledCache.get(family);
  if (cached !== undefined) return cached;
  let result = false;
  try {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    if (ctx) {
      const sample = "mmmmmmmmmmlli1|WWW0O";
      const width = (font: string) => {
        ctx.font = `32px ${font}`;
        return ctx.measureText(sample).width;
      };
      for (const generic of ["monospace", "serif", "sans-serif"]) {
        if (width(`${family}, ${generic}`) !== width(generic)) {
          result = true;
          break;
        }
      }
    }
  } catch {
    result = false;
  }
  fontInstalledCache.set(family, result);
  return result;
};

const firstFamily = (stack: string): string => stack.split(",")[0].trim();

@customElement("ha-soc-terminal-view")
export class HaSocTerminalView extends LitElement {
  static styles = [
    sharedStyles,
    unsafeCSS(xtermCss),
    css`
      .term-shell {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .term-header {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
        font-size: 12.5px;
      }
      .term-header .spacer {
        flex: 1;
      }
      .term-box {
        background: var(--soc-term-bg, #1c2128);
        border-radius: 8px;
        padding: 8px;
        min-height: 420px;
        height: calc(100vh - 280px);
        overflow: hidden;
      }
      .term-box .xterm {
        height: 100%;
      }
      .font-ctl {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: var(--secondary-text-color);
      }
      .font-ctl select {
        font: inherit;
        color: var(--primary-text-color);
        background: var(--card-background-color, #fff);
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        padding: 2px 4px;
      }
      .recorded {
        color: var(--error-color, #db4437);
        font-weight: 600;
      }
      .ended {
        margin-top: 6px;
      }
      .export-row {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: wrap;
        font-size: 12px;
      }
      .session-list ul {
        list-style: none;
        margin: 0;
        padding: 0;
        display: flex;
        flex-direction: column;
        gap: 4px;
        font-size: 12.5px;
      }
      .run-card {
        margin-top: 4px;
      }
      .run-row {
        display: flex;
        gap: 8px;
      }
      .run-row input[type="text"] {
        flex: 1;
        font: inherit;
        padding: 4px 8px;
        border: 1px solid var(--divider-color, #ccc);
        border-radius: 4px;
        background: var(--card-background-color, #fff);
        color: var(--primary-text-color);
      }
      .chips {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-top: 6px;
      }
      .chip {
        cursor: pointer;
        font-size: 11.5px;
        padding: 2px 8px;
        border-radius: 100px;
        background: var(--secondary-background-color, #eee);
        color: var(--secondary-text-color);
      }
      .rawlog {
        white-space: pre-wrap;
        word-break: break-word;
        max-height: 300px;
        overflow: auto;
      }
    `,
  ];

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _status: TerminalStatus | null = null;
  @state() private _error: string | null = null;
  @state() private _open: TerminalOpenResult | null = null;
  @state() private _ended: { reason: string; duration: number } | null = null;
  @state() private _prefs: FontPrefs = loadPrefs();
  @state() private _busy = false;
  @state() private _isOwner = false;
  @state() private _feedback: string | null = null;
  @state() private _appBusy = false;
  @state() private _runCommand = "";
  @state() private _runTimeout = 30;
  @state() private _runBusy = false;
  @state() private _runOutput: TerminalRunResult | null = null;
  @state() private _runError: string | null = null;
  @state() private _runHistory: string[] = [];
  @state() private _stripAnsi = true;
  @state() private _sessionBusy: string | null = null;

  @query(".term-box") private _box!: HTMLDivElement;

  private _term: Terminal | null = null;
  private _fit: FitAddon | null = null;
  private _unsubscribe: (() => Promise<void>) | null = null;
  private _resizeObserver: ResizeObserver | null = null;
  private _resizeTimer: number | undefined;
  private _feedbackTimer: number | undefined;
  // OSC 133 marks (FTCS): 'C' fires right before a command's output starts,
  // 'A' right before the next prompt; the shell emits both (rootfs/etc/profile.d/ha_soc_terminal.sh).
  // Tracked as absolute buffer rows (baseY + cursorY) so "last output" survives scrollback.
  private _lastOutputStartRow: number | null = null;
  private _lastOutputEndRow: number | null = null;
  private _pendingOutputStartRow: number | null = null;

  connectedCallback() {
    super.connectedCallback();
    void this._refresh();
    fetchAccessInfo(this.hass)
      .then((access) => {
        this._isOwner = !!access.is_owner;
      })
      .catch(() => undefined);
  }

  disconnectedCallback() {
    // Navigating away ends the session; the server writes the close record.
    void this._close("user_closed");
    super.disconnectedCallback();
  }

  updated(changed: Map<string, unknown>) {
    if (changed.has("hass") && this._term) {
      this._term.options.theme = this._theme();
    }
  }

  private async _refresh() {
    try {
      this._status = await fetchTerminalStatus(this.hass);
      this._error = null;
    } catch (e) {
      this._error = (e as { message?: string }).message || String(e);
    }
  }

  // Home Assistant's theme variables, resolved against this element, with the
  // fallback palette for anything a theme does not define.
  private _theme(): ITheme {
    const cs = getComputedStyle(this);
    const v = (name: string, fallback: string) => cs.getPropertyValue(name).trim() || fallback;
    const dark = this.hass?.themes?.darkMode ?? true;
    const bg = v("--code-editor-background-color", dark ? FALLBACK.background! : "#f6f8fa");
    const fg = v("--primary-text-color", dark ? FALLBACK.foreground! : "#1f2328");
    const accent = v("--primary-color", FALLBACK.blue!);
    const theme: ITheme = {
      ...FALLBACK,
      background: bg,
      foreground: fg,
      cursor: accent,
      cursorAccent: bg,
      selectionBackground: v("--accent-color", accent) + "55",
      blue: accent,
      brightBlue: accent,
      red: v("--error-color", FALLBACK.red!),
      brightRed: v("--error-color", FALLBACK.brightRed!),
      green: v("--success-color", FALLBACK.green!),
      brightGreen: v("--success-color", FALLBACK.brightGreen!),
      yellow: v("--warning-color", FALLBACK.yellow!),
      brightYellow: v("--warning-color", FALLBACK.brightYellow!),
      cyan: v("--info-color", FALLBACK.cyan!),
      brightCyan: v("--info-color", FALLBACK.brightCyan!),
    };
    if (!dark) {
      theme.black = "#24292f";
      theme.white = "#6e7781";
      theme.brightBlack = "#57606a";
      theme.brightWhite = "#1f2328";
    }
    this.style.setProperty("--soc-term-bg", bg);
    return theme;
  }

  private async _start() {
    if (this._busy || this._open) return;
    this._busy = true;
    this._error = null;
    this._ended = null;
    try {
      // The terminal element first, so the size sent with open is the real one.
      await this.updateComplete;
      const term = new Terminal({
        cursorBlink: true,
        fontSize: this._prefs.size,
        // Never a var() here: xterm measures the cell on an OffscreenCanvas,
        // whose font parser rejects custom properties and silently keeps the
        // canvas default (10px sans-serif). Every row was measured on that
        // font and drawn in the real one, which is what "compressed" was.
        fontFamily: this._fontFamily(),
        lineHeight: this._prefs.lineHeight,
        scrollback: 5000,
        allowProposedApi: false,
        theme: this._theme(),
      });
      const fit = new FitAddon();
      term.loadAddon(fit);
      term.open(this._box);
      fit.fit();
      this._term = term;
      this._fit = fit;
      this._lastOutputStartRow = null;
      this._lastOutputEndRow = null;
      this._pendingOutputStartRow = null;
      // OSC 133;C marks "output is about to start", OSC 133;A marks "a new
      // prompt is about to be drawn" (the boundary between a command's output
      // and the next one). Together they bound exactly the previous command's
      // output, independent of how the shell wrapped or scrolled it.
      term.parser.registerOscHandler(133, (data: string) => {
        const mark = data.split(";")[0];
        const row = term.buffer.active.baseY + term.buffer.active.cursorY;
        if (mark === "C") {
          this._pendingOutputStartRow = row;
        } else if (mark === "A") {
          if (this._pendingOutputStartRow !== null) {
            this._lastOutputStartRow = this._pendingOutputStartRow;
            this._lastOutputEndRow = row;
            this._pendingOutputStartRow = null;
          }
        }
        return false;
      });

      const open = await openTerminal(this.hass, "self", term.cols, term.rows, (ev) => this._onEvent(ev));
      this._open = open.result;
      this._unsubscribe = open.unsubscribe;

      term.onData((data) => {
        if (!this._open) return;
        void sendTerminalInput(this.hass, this._open.session_id, toBase64(data)).catch((e) => {
          this._error = (e as { message?: string }).message || String(e);
        });
      });
      term.onResize(({ cols, rows }) => {
        if (!this._open) return;
        void resizeTerminal(this.hass, this._open.session_id, cols, rows).catch(() => undefined);
      });
      this._resizeObserver = new ResizeObserver(() => {
        window.clearTimeout(this._resizeTimer);
        this._resizeTimer = window.setTimeout(() => this._fit?.fit(), 80);
      });
      this._resizeObserver.observe(this._box);
      term.focus();
    } catch (e) {
      this._error = (e as { message?: string }).message || String(e);
      this._teardownTerminal();
    } finally {
      this._busy = false;
    }
  }

  /** Concrete font-family string for xterm, with the theme token resolved. */
  private _fontFamily(): string {
    const choice = FONT_CHOICES.find((f) => f.id === this._prefs.family) ?? FONT_CHOICES[0];
    if (choice.id === "theme") {
      const themed = getComputedStyle(this).getPropertyValue("--ha-font-family-code").trim();
      if (themed && themed !== "monospace") return `${themed}, ${GENERIC_TAIL}`;
      return GENERIC_TAIL;
    }
    if (choice.id === "mono") return "monospace";
    return `${choice.stack}, ${GENERIC_TAIL}`;
  }

  private _setPrefs(patch: Partial<FontPrefs>) {
    this._prefs = { ...this._prefs, ...patch };
    savePrefs(this._prefs);
    const term = this._term;
    if (!term) return;
    term.options.fontFamily = this._fontFamily();
    term.options.fontSize = this._prefs.size;
    term.options.lineHeight = this._prefs.lineHeight;
    this._fit?.fit();
    term.focus();
  }

  private _renderFontControls() {
    const p = this._prefs;
    return html`
      <label class="font-ctl">
        Font
        <select
          @change=${(e: Event) => this._setPrefs({ family: (e.target as HTMLSelectElement).value })}
        >
          ${FONT_CHOICES.map((f) => {
            const installed =
              f.id === "theme" || f.id === "mono" ? true : isFontInstalled(firstFamily(f.stack));
            return html`<option value=${f.id} ?selected=${f.id === p.family} ?disabled=${!installed}>
              ${f.label}${installed ? "" : " (not installed)"}
            </option>`;
          })}
        </select>
      </label>
      <label class="font-ctl">
        Size
        <select
          @change=${(e: Event) => this._setPrefs({ size: Number((e.target as HTMLSelectElement).value) })}
        >
          ${FONT_SIZES.map((n) => html`<option value=${n} ?selected=${n === p.size}>${n}px</option>`)}
        </select>
      </label>
      <label class="font-ctl">
        Line
        <select
          @change=${(e: Event) =>
            this._setPrefs({ lineHeight: Number((e.target as HTMLSelectElement).value) })}
        >
          ${LINE_HEIGHTS.map(
            (n) => html`<option value=${n} ?selected=${n === p.lineHeight}>${n.toFixed(1)}</option>`,
          )}
        </select>
      </label>
    `;
  }

  private _onEvent(ev: TerminalEvent) {
    if (ev.kind === "output" && this._term) {
      this._term.write(fromBase64(ev.data));
    } else if (ev.kind === "closed") {
      this._ended = { reason: ev.reason, duration: ev.duration_seconds };
      this._open = null;
      void this._teardownSubscription();
      void this._refresh();
    }
  }

  private async _close(reason: string) {
    const open = this._open;
    this._open = null;
    if (open) {
      try {
        await closeTerminal(this.hass, open.session_id);
      } catch {
        // Already gone server-side; the close event, if any, said why.
      }
      if (!this._ended) this._ended = { reason, duration: 0 };
    }
    await this._teardownSubscription();
    this._teardownTerminal();
    void this._refresh();
  }

  private async _teardownSubscription() {
    const unsubscribe = this._unsubscribe;
    this._unsubscribe = null;
    if (unsubscribe) {
      try {
        await unsubscribe();
      } catch {
        // The connection may already be closed.
      }
    }
  }

  private _teardownTerminal() {
    this._resizeObserver?.disconnect();
    this._resizeObserver = null;
    this._term?.dispose();
    this._term = null;
    this._fit = null;
  }

  private _showFeedback(text: string) {
    window.clearTimeout(this._feedbackTimer);
    this._feedback = text;
    this._feedbackTimer = window.setTimeout(() => {
      this._feedback = null;
    }, FEEDBACK_MS);
  }

  /** Every row in `[start, end)`, trailing whitespace trimmed, newline-joined. */
  private _rowsText(start: number, end: number): string {
    const term = this._term;
    if (!term) return "";
    const buffer = term.buffer.active;
    const lines: string[] = [];
    for (let row = start; row < end; row++) {
      const line = buffer.getLine(row);
      if (line) lines.push(line.translateToString(true).replace(/\s+$/u, ""));
    }
    return lines.join("\n");
  }

  private _screenText(): string {
    const term = this._term;
    if (!term) return "";
    const base = term.buffer.active.baseY;
    return this._rowsText(base, base + term.rows);
  }

  private _allText(): string {
    const term = this._term;
    if (!term) return "";
    return this._rowsText(0, term.buffer.active.baseY + term.rows);
  }

  private _lastOutputText(): string {
    if (this._lastOutputStartRow === null || this._lastOutputEndRow === null) return "";
    return this._rowsText(this._lastOutputStartRow, this._lastOutputEndRow);
  }

  /**
   * Copies or downloads `text`, then audits it with export_event; a failed
   * audit call still leaves the copy/download in place, with a warning line
   * instead of silently pretending it never happened.
   */
  private async _export(kind: TerminalExportKind, text: string, mode: "copy" | "download", filenameBase?: string) {
    if (!text) {
      this._showFeedback("Nothing to " + mode);
      return;
    }
    const lines = lineCount(text);
    const bytes = byteLength(text);
    try {
      if (mode === "copy") await copyText(text);
      else downloadText(text, `${filenameBase ?? "ha-soc-terminal"}-${utcStamp()}.txt`);
    } catch (e) {
      this._error = (e as { message?: string }).message || String(e);
      return;
    }
    this._showFeedback(`${mode === "copy" ? "Copied" : "Downloaded"} ${lines} line(s)`);
    try {
      const sha256 = await sha256Hex(text);
      await sendTerminalExportEvent(this.hass, kind, lines, bytes, sha256, this._open?.session_id);
    } catch {
      this._showFeedback(`${mode === "copy" ? "Copied" : "Downloaded"} ${lines} line(s) (audit record failed)`);
    }
  }

  private async _downloadTranscript(sessionId: string) {
    try {
      const transcript = await fetchTerminalTranscript(this.hass, sessionId);
      const text = this._stripAnsi ? stripAnsi(transcript.text) : transcript.text;
      downloadText(text, `ha-soc-terminal-transcript-${sessionId}.txt`);
      this._showFeedback(`Downloaded transcript for ${sessionId}`);
    } catch (e) {
      this._error = (e as { message?: string }).message || String(e);
    }
  }

  private async _controlApp(action: "start" | "restart") {
    this._appBusy = true;
    this._error = null;
    try {
      const result = await controlTerminalApp(this.hass, action);
      if (!result.ok) this._error = result.error || result.reason || "The app did not respond.";
    } catch (e) {
      this._error = (e as { message?: string }).message || String(e);
    } finally {
      this._appBusy = false;
      void this._refresh();
    }
  }

  private async _forgetPairing() {
    if (!window.confirm("Forget the Terminal app's pairing? It will re-pair on its own the next time it starts.")) {
      return;
    }
    this._appBusy = true;
    try {
      await forgetTerminalPairing(this.hass);
    } catch (e) {
      this._error = (e as { message?: string }).message || String(e);
    } finally {
      this._appBusy = false;
      void this._refresh();
    }
  }

  private async _closeOtherSession(sessionId: string) {
    this._sessionBusy = sessionId;
    try {
      await closeTerminal(this.hass, sessionId);
    } catch (e) {
      this._error = (e as { message?: string }).message || String(e);
    } finally {
      this._sessionBusy = null;
      void this._refresh();
    }
  }

  private async _runOnce() {
    const command = this._runCommand.trim();
    if (!command || this._runBusy) return;
    this._runBusy = true;
    this._runError = null;
    this._runOutput = null;
    try {
      const result = await runTerminalCommand(this.hass, command, this._runTimeout);
      this._runOutput = result;
      this._runHistory = [command, ...this._runHistory.filter((c) => c !== command)].slice(
        0,
        MAX_COMMAND_HISTORY
      );
    } catch (e) {
      this._runError = (e as { message?: string }).message || String(e);
    } finally {
      this._runBusy = false;
    }
  }

  private _renderStatusControls() {
    const s = this._status;
    if (!s?.installed) return nothing;
    return html`
      ${!s.running
        ? html`<button class="ha-btn" ?disabled=${this._appBusy} @click=${() => this._controlApp("start")}>
            Start app
          </button>`
        : html`<button class="ha-btn" ?disabled=${this._appBusy} @click=${() => this._controlApp("restart")}>
            Restart app
          </button>`}
      ${this._isOwner && s.paired
        ? html`<button class="ha-btn" ?disabled=${this._appBusy} @click=${() => this._forgetPairing()}>
            Forget pairing
          </button>`
        : nothing}
    `;
  }

  private _renderSessionList() {
    const sessions = this._status?.sessions ?? [];
    if (!sessions.length) return nothing;
    const myId = this.hass.user?.id;
    const visible = sessions.filter((s) => this._isOwner || s.user_id === myId);
    if (!visible.length) return nothing;
    return html`
      <div class="session-list">
        <h4 style="margin:8px 0 4px;">Open sessions</h4>
        <ul>
          ${visible.map(
            (s) => html`
              <li>
                <code>${s.session_id}</code> — ${s.user_id} — started ${new Date(s.started).toLocaleString()}
                (${s.bytes_in}B in / ${s.bytes_out}B out)
                <button
                  class="ha-btn"
                  ?disabled=${this._sessionBusy === s.session_id}
                  @click=${() => this._closeOtherSession(s.session_id)}
                >
                  Close
                </button>
                <button class="ha-btn" @click=${() => this._downloadTranscript(s.session_id)}>
                  Download transcript
                </button>
              </li>
            `
          )}
        </ul>
      </div>
    `;
  }

  private _renderExportButtons() {
    if (!this._open) return nothing;
    return html`
      <div class="export-row">
        <button class="ha-btn" @click=${() => this._export("copy_screen", this._screenText(), "copy")}>
          Copy screen
        </button>
        <button class="ha-btn" @click=${() => this._export("copy_all", this._allText(), "copy")}>
          Copy all
        </button>
        <button class="ha-btn" @click=${() => this._export("copy_last", this._lastOutputText(), "copy")}>
          Copy last output
        </button>
        <button
          class="ha-btn"
          @click=${() =>
            this._export("download_screen", this._screenText(), "download", `ha-soc-terminal-${this._open?.session_id}`)}
        >
          Download screen
        </button>
        <button
          class="ha-btn"
          @click=${() =>
            this._export("download_all", this._allText(), "download", `ha-soc-terminal-${this._open?.session_id}`)}
        >
          Download all
        </button>
        <label class="font-ctl">
          <input
            type="checkbox"
            .checked=${this._stripAnsi}
            @change=${(e: Event) => (this._stripAnsi = (e.target as HTMLInputElement).checked)}
          />
          strip ANSI in transcript downloads
        </label>
        ${this._feedback ? html`<span class="muted">${this._feedback}</span>` : nothing}
      </div>
    `;
  }

  private _renderRunCard() {
    const s = this._status;
    const target = s?.targets.find((t) => t.id === "self");
    if (!target?.available) return nothing;
    return html`
      <div class="card run-card">
        <h3 style="margin:0 0 6px;">Run a command</h3>
        <div class="run-row">
          <input
            type="text"
            .value=${this._runCommand}
            placeholder="e.g. ha core logs"
            @input=${(e: Event) => (this._runCommand = (e.target as HTMLInputElement).value)}
            @keydown=${(e: KeyboardEvent) => {
              if (e.key === "Enter") void this._runOnce();
            }}
          />
          <select
            @change=${(e: Event) => (this._runTimeout = Number((e.target as HTMLSelectElement).value))}
          >
            ${RUN_TIMEOUTS.map(
              (t) => html`<option value=${t} ?selected=${t === this._runTimeout}>${t}s</option>`
            )}
          </select>
          <button class="ha-btn" ?disabled=${this._runBusy} @click=${() => this._runOnce()}>
            ${this._runBusy ? "Running…" : "Run"}
          </button>
        </div>
        ${this._runHistory.length
          ? html`<div class="chips">
              ${this._runHistory.map(
                (c) => html`<span class="chip" @click=${() => (this._runCommand = c)}>${c}</span>`
              )}
            </div>`
          : nothing}
        ${this._runError ? html`<div class="alert">${this._runError}</div>` : nothing}
        ${this._runOutput
          ? html`
              <p class="muted" style="font-size:12px;margin:6px 0 2px;">
                exit ${this._runOutput.exit_code} — ${this._runOutput.duration_seconds}s${this._runOutput.truncated
                  ? " — output truncated at 256 KiB"
                  : ""}
              </p>
              <pre class="rawlog">${this._runOutput.stdout || "(no output)"}</pre>
              <div class="export-row">
                <button
                  class="ha-btn"
                  @click=${() => this._export("copy_run", this._runOutput!.stdout, "copy")}
                >
                  Copy output
                </button>
                <button
                  class="ha-btn"
                  @click=${() =>
                    this._export("download_run", this._runOutput!.stdout, "download", "ha-soc-terminal-run")}
                >
                  Download output
                </button>
              </div>
            `
          : nothing}
      </div>
    `;
  }

  render() {
    const s = this._status;
    const target = s?.targets.find((t) => t.id === "self");
    const canOpen = !!target?.available && !this._open && !this._busy;
    return html`
      <div class="card term-shell">
        <div class="term-header">
          <h3 style="margin:0;">Terminal</h3>
          ${s?.recording === false
            ? html`<span class="muted">not recorded (app option)</span>`
            : html`<span class="recorded">● recorded</span>`}
          <span class="muted">
            ${!s
              ? "Checking the Terminal app…"
              : !s.supervisor
                ? "Needs a Supervisor-based install."
                : !s.installed
                  ? "The HA SOC Terminal app is not installed."
                  : !s.running
                    ? "The Terminal app is installed but not running; start it under Settings, Apps."
                    : !s.paired
                      ? "The Terminal app has not paired with HA SOC yet; it does so within a minute of starting."
                      : this._open
                        ? `Session ${this._open.session_id} on ${this._open.host}`
                        : `Ready. ${s.sessions_open} of ${s.max_sessions} sessions open.`}
          </span>
          <span class="spacer"></span>
          ${this._renderStatusControls()}
          ${this._renderFontControls()}
          ${this._open
            ? html`<button class="ha-btn" @click=${() => this._close("user_closed")}>Close session</button>`
            : html`<button class="ha-btn" ?disabled=${!canOpen} @click=${() => this._start()}>
                ${this._busy ? "Opening…" : "Open session"}
              </button>`}
          <button class="ha-btn" ?disabled=${this._busy} @click=${() => this._refresh()}>Refresh</button>
        </div>
        ${this._error ? html`<div class="alert">${this._error}</div>` : nothing}
        <div class="term-box" @click=${() => this._term?.focus()}></div>
        ${this._renderExportButtons()}
        ${this._ended
          ? html`<p class="muted ended">
              ${REASONS[this._ended.reason] ?? this._ended.reason}
              ${this._ended.duration ? ` Duration ${Math.round(this._ended.duration / 60)} min.` : ""}
              The session's open and close records are in the Audit Log.
            </p>`
          : nothing}
        <p class="muted" style="font-size:11.5px;margin:0;">
          Executes only on this server, in the Terminal app's own container. Paste with
          Ctrl+Shift+V or the browser's paste; scroll with the mouse wheel. Every session is
          recorded by the app unless its option is off, and opens and closes are audited here.
          Font, size and line spacing are remembered in this browser; a family listed as not
          installed is missing on this machine, not on the server.
        </p>
        ${this._renderSessionList()}
        ${this._renderRunCard()}
      </div>
    `;
  }
}
