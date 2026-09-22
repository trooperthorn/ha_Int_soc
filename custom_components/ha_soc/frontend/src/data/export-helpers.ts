/**
 * Shared copy/download/hash plumbing for anything that lets screen text leave
 * the panel (the terminal view's screen buffer, run output, and the Logs
 * view's raw log). Every caller audits what actually left through
 * `ha_soc/terminal/export_event` with the sha256 of the exact bytes, computed
 * here before the panel hands them to the clipboard or a download.
 */

export const sha256Hex = async (text: string): Promise<string> => {
  const bytes = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
};

export const byteLength = (text: string): number => new TextEncoder().encode(text).length;

export const lineCount = (text: string): number => (text ? text.split("\n").length : 0);

/** Copies text to the clipboard, falling back to a hidden textarea + execCommand. */
export const copyText = async (text: string): Promise<void> => {
  try {
    await navigator.clipboard.writeText(text);
    return;
  } catch {
    // Fall through to the textarea fallback below (older browsers, or a
    // permissions-policy-restricted iframe).
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  try {
    document.execCommand("copy");
  } finally {
    document.body.removeChild(textarea);
  }
};

/** Saves text as a file download named `filename`. */
export const downloadText = (text: string, filename: string): void => {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

/** UTC timestamp suitable for a filename: 2026-09-22T18-04-33Z. */
export const utcStamp = (): string => new Date().toISOString().replace(/:/g, "-").replace(/\.\d+Z$/, "Z");

/** Strips CSI/OSC/other ANSI escape sequences a terminal transcript may carry. */
export const stripAnsi = (text: string): string =>
  // eslint-disable-next-line no-control-regex
  text.replace(/\x1b\][^\x07]*(\x07|\x1b\\)/g, "").replace(/\x1b\[[0-9;?]*[a-zA-Z]/g, "").replace(/\x1b[()][A-Za-z0-9]/g, "");
