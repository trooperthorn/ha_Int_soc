import { LitElement, html, css, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";
import { sharedStyles } from "../styles";
import type { HomeAssistant } from "../types";
import {
  DashboardFile,
  DashboardFileContent,
  DashboardFileListing,
  YamlVerdict,
  listDashboardFiles,
  readDashboardFile,
  validateDashboardFile,
  writeDashboardFile,
} from "../data/ha-soc-ws";

/**
 * Edits the YAML files under <config>/dashboards, and nothing else.
 *
 * The container owns every piece of state. `loaded` is the read response held
 * unmodified and `draft` is what the operator typed; keeping them apart is
 * what guarantees the digest sent on a write is the one that came back from
 * the read rather than one derived from the draft, which is the difference
 * between detecting a concurrent change and silently overwriting it.
 *
 * There is no client-side YAML parser here. The panel says "checking" while
 * the server verdict is outstanding rather than rendering a browser opinion
 * with the same authority as the integration's; see docs/design.md.
 */

const VALIDATE_DEBOUNCE_MS = 600;

const EMPTY_VERDICT: YamlVerdict = { valid: true, errors: [], warnings: [] };

const formatBytes = (bytes: number) =>
  bytes < 1024 ? `${bytes} B` : `${Math.round(bytes / 1024)} KB`;

const formatTimestamp = (epochSeconds: number) =>
  new Date(epochSeconds * 1000).toLocaleString();

interface DenialState {
  code: string;
  message: string;
}

interface ConflictState {
  message: string;
}

const errorOf = (err: unknown): DenialState => {
  const wrapped = err as { code?: string; message?: string } | undefined;
  return {
    code: wrapped?.code ?? "unknown_error",
    message: wrapped?.message ?? String(err),
  };
};

@customElement("ha-soc-dashboard-files-view")
export class HaSocDashboardFilesView extends LitElement {
  static styles = [
    sharedStyles,
    css`
      .layout {
        display: grid;
        grid-template-columns: minmax(200px, 260px) 1fr;
        gap: 16px;
        align-items: start;
      }
      @container (max-width: 800px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
      .file {
        display: block;
        width: 100%;
        text-align: left;
        padding: 6px 8px;
        border: none;
        background: none;
        border-radius: 6px;
        cursor: pointer;
        font: inherit;
        color: inherit;
      }
      .file[aria-current="true"] {
        background: var(--primary-color, #03a9f4);
        color: var(--text-primary-color, #fff);
      }
      .file .meta {
        display: block;
        font-size: 11px;
        opacity: 0.75;
      }
      .editor {
        display: flex;
        border: 1px solid var(--divider-color, #444);
        border-radius: 6px;
        overflow: hidden;
        font-family: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
        font-size: 12.5px;
        line-height: 1.5;
      }
      .gutter {
        padding: 8px 6px;
        text-align: right;
        user-select: none;
        opacity: 0.55;
        overflow: hidden;
        background: rgba(127, 127, 127, 0.08);
        white-space: pre;
      }
      textarea {
        flex: 1;
        min-height: 420px;
        border: none;
        outline: none;
        resize: vertical;
        padding: 8px;
        font: inherit;
        color: inherit;
        background: transparent;
        white-space: pre;
        overflow-wrap: normal;
        overflow-x: auto;
      }
      .diag {
        margin: 4px 0;
        padding-left: 8px;
        border-left: 3px solid transparent;
      }
      .diag.error {
        border-left-color: var(--error-color, #db4437);
      }
      .diag.warning {
        border-left-color: var(--warning-color, #ffa600);
      }
      .banner {
        border-left: 4px solid var(--warning-color, #ffa600);
        padding: 8px 12px;
        margin-bottom: 12px;
      }
      .banner.denial {
        border-left-color: var(--error-color, #db4437);
      }
      .commit {
        display: flex;
        gap: 8px;
        align-items: center;
        flex-wrap: wrap;
        margin-top: 12px;
      }
      .commit input[type="text"] {
        flex: 1;
        min-width: 200px;
        padding: 6px 8px;
      }
    `,
  ];

  @property({ attribute: false }) hass!: HomeAssistant;

  @state() private _listing: DashboardFileListing | null = null;
  @state() private _selected: string | null = null;
  // The read response, held unmodified; the source of the digest a write sends.
  @state() private _loaded: DashboardFileContent | null = null;
  @state() private _draft = "";
  @state() private _verdict: YamlVerdict = EMPTY_VERDICT;
  // True while the rendered verdict does not describe the current draft.
  @state() private _checking = false;
  @state() private _reason = "";
  @state() private _busy = false;
  @state() private _conflict: ConflictState | null = null;
  @state() private _denial: DenialState | null = null;
  @state() private _saved: string | null = null;
  @state() private _loading = true;

  private _validateTimer?: ReturnType<typeof setTimeout>;

  connectedCallback(): void {
    super.connectedCallback();
    void this._loadList();
  }

  disconnectedCallback(): void {
    super.disconnectedCallback();
    if (this._validateTimer) {
      clearTimeout(this._validateTimer);
    }
  }

  private async _loadList(): Promise<void> {
    this._loading = true;
    try {
      this._listing = await listDashboardFiles(this.hass);
    } catch (err) {
      this._denial = errorOf(err);
    } finally {
      this._loading = false;
    }
  }

  private async _select(path: string): Promise<void> {
    this._conflict = null;
    this._saved = null;
    this._busy = true;
    try {
      const loaded = await readDashboardFile(this.hass, path);
      this._selected = path;
      this._loaded = loaded;
      this._draft = loaded.content;
      this._reason = "";
      this._verdict = EMPTY_VERDICT;
      this._checking = false;
    } catch (err) {
      this._denial = errorOf(err);
    } finally {
      this._busy = false;
    }
  }

  private _onDraftChange(value: string): void {
    this._draft = value;
    this._saved = null;
    this._checking = true;
    if (this._validateTimer) {
      clearTimeout(this._validateTimer);
    }
    this._validateTimer = setTimeout(() => void this._validate(), VALIDATE_DEBOUNCE_MS);
  }

  private async _validate(): Promise<void> {
    const draftAtRequest = this._draft;
    try {
      const verdict = await validateDashboardFile(
        this.hass,
        draftAtRequest,
        this._selected ?? undefined
      );
      // A verdict that arrives after another keystroke describes stale text.
      if (draftAtRequest !== this._draft) {
        return;
      }
      this._verdict = verdict;
      this._checking = false;
    } catch (err) {
      this._denial = errorOf(err);
      this._checking = false;
    }
  }

  private _blockers(): string[] {
    const blockers: string[] = [];
    if (!this._loaded) blockers.push("No file loaded");
    else if (this._draft === this._loaded.content) blockers.push("No changes");
    if (this._checking) blockers.push("Checking the YAML");
    if (this._verdict.errors.length) blockers.push("Fix the YAML error");
    if (!this._reason.trim()) blockers.push("Enter a reason");
    if (this._busy) blockers.push("Save in progress");
    return blockers;
  }

  private async _save(): Promise<void> {
    if (!this._loaded || this._blockers().length) {
      return;
    }
    this._busy = true;
    this._conflict = null;
    try {
      const result = await writeDashboardFile(
        this.hass,
        this._loaded.path,
        this._draft,
        this._loaded.sha256,
        this._reason.trim()
      );
      this._loaded = { path: result.path, content: this._draft, sha256: result.sha256 };
      this._reason = "";
      this._saved = `Saved. Previous copy kept at ${result.backup}`;
      await this._loadList();
    } catch (err) {
      const denial = errorOf(err);
      if (denial.code === "conflict") {
        // The draft is kept; losing the operator's work to a concurrent edit
        // would be a worse outcome than making them merge it by hand.
        this._conflict = { message: denial.message };
      } else {
        this._denial = denial;
      }
    } finally {
      this._busy = false;
    }
  }

  private async _reload(): Promise<void> {
    if (this._selected) {
      await this._select(this._selected);
    }
  }

  private _syncGutter(event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    const gutter = this.renderRoot.querySelector<HTMLElement>(".gutter");
    if (gutter) {
      gutter.scrollTop = textarea.scrollTop;
    }
  }

  protected render() {
    if (this._denial) {
      // The denial replaces the view: leaving an editable surface under a
      // refusal invites a retry loop against a control that is working.
      return html`
        <div class="card banner denial">
          <h3>Request refused</h3>
          <p>${this._denial.message}</p>
          <p class="muted">Code: ${this._denial.code}</p>
          <button @click=${() => { this._denial = null; void this._loadList(); }}>
            Dismiss
          </button>
        </div>
      `;
    }

    if (this._loading) {
      return html`<div class="card"><p class="muted">Loading dashboard files...</p></div>`;
    }

    if (!this._listing?.enabled) {
      return html`
        <div class="card">
          <h3>Dashboard Files</h3>
          <p class="muted">
            Editing dashboard YAML files is turned off. The owner can turn it on under
            Settings, Dashboard Files. While it is off the server refuses every read and
            write, so nothing here is only hidden.
          </p>
        </div>
      `;
    }

    if (!this._listing.root_exists) {
      return html`
        <div class="card">
          <h3>Dashboard Files</h3>
          <p class="muted">
            No <code>${this._listing.root}</code> folder exists in the configuration
            directory. This view edits YAML-mode dashboards, which live in that folder;
            dashboards stored in the UI are edited in Home Assistant's own raw editor.
          </p>
        </div>
      `;
    }

    return html`
      <div class="layout">
        <div class="card">
          <h3>${this._listing.root}/</h3>
          ${this._listing.files.length
            ? this._listing.files.map((file) => this._renderFile(file))
            : html`<p class="empty">No YAML files in this folder.</p>`}
          ${this._listing.truncated
            ? html`<p class="muted">Listing truncated; only the first files are shown.</p>`
            : nothing}
        </div>

        <div class="card">${this._renderEditor()}</div>
      </div>
    `;
  }

  private _renderFile(file: DashboardFile) {
    return html`
      <button
        class="file"
        aria-current=${this._selected === file.path ? "true" : "false"}
        ?disabled=${file.too_large}
        @click=${() => void this._select(file.path)}
      >
        ${file.path}
        <span class="meta">
          ${formatBytes(file.size)} &middot; ${formatTimestamp(file.modified)}
          ${file.too_large ? html`&middot; too large to edit` : nothing}
        </span>
      </button>
    `;
  }

  private _renderEditor() {
    if (!this._loaded) {
      return html`<p class="empty">Select a file to edit.</p>`;
    }

    const lineCount = this._draft.split("\n").length;
    const gutter = Array.from({ length: lineCount }, (_, index) => index + 1).join("\n");
    const blockers = this._blockers();

    return html`
      <h3>${this._loaded.path}</h3>

      ${this._conflict
        ? html`
            <div class="banner">
              <strong>${this._conflict.message}</strong>
              <p class="muted">
                Your draft is still here. Copy anything you need, then reload to get the
                file as it now stands on disk.
              </p>
              <button @click=${() => void this._reload()}>Reload from disk</button>
            </div>
          `
        : nothing}

      ${this._saved ? html`<p class="muted">${this._saved}</p>` : nothing}

      <div class="editor">
        <div class="gutter">${gutter}</div>
        <textarea
          spellcheck="false"
          .value=${this._draft}
          ?readonly=${this._busy}
          @scroll=${this._syncGutter}
          @input=${(e: Event) => this._onDraftChange((e.target as HTMLTextAreaElement).value)}
        ></textarea>
      </div>

      ${this._renderDiagnostics()}

      <div class="commit">
        <input
          type="text"
          placeholder="Why are you changing this file?"
          .value=${this._reason}
          maxlength="500"
          @input=${(e: Event) => (this._reason = (e.target as HTMLInputElement).value)}
        />
        <button ?disabled=${blockers.length > 0} @click=${() => void this._save()}>
          Save
        </button>
        ${blockers.length ? html`<span class="muted">${blockers[0]}</span>` : nothing}
      </div>
    `;
  }

  private _renderDiagnostics() {
    if (this._checking) {
      return html`<p class="muted">Checking the YAML on the server...</p>`;
    }
    if (!this._verdict.errors.length && !this._verdict.warnings.length) {
      return html`<p class="muted">No YAML errors or warnings.</p>`;
    }
    return html`
      ${this._verdict.errors.map(
        (item) => html`
          <p class="diag error">
            Error${item.line ? html` (line ${item.line})` : nothing}: ${item.message}
          </p>
        `
      )}
      ${this._verdict.warnings.map(
        (item) => html`
          <p class="diag warning">
            Warning${item.line ? html` (line ${item.line})` : nothing}: ${item.message}
          </p>
        `
      )}
    `;
  }
}
