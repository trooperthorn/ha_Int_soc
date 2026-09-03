import { html, TemplateResult } from "lit";

/**
 * Shared, accessible column sorting for every table in the panel: the <th>
 * carries aria-sort and the clickable element is a real <button>; see
 * docs/design.md for the accessibility contract.
 */

export interface SortState {
  key: string;
  dir: 1 | -1;
}

/** Cycle: unsorted -> ascending -> descending -> ascending ... */
export function nextSort(current: SortState | null, key: string): SortState {
  if (current?.key === key) return { key, dir: current.dir === 1 ? -1 : 1 };
  return { key, dir: 1 };
}

/**
 * Stable sort of rows by the active key's accessor. Null/undefined always sink
 * to the bottom; numbers compare numerically, everything else as
 * case-insensitive strings.
 */
export function sortRows<T>(
  rows: T[],
  state: SortState | null,
  accessors: Record<string, (row: T) => unknown>
): T[] {
  if (!state) return rows;
  const accessor = accessors[state.key];
  if (!accessor) return rows;
  return rows
    .map((row, i) => ({ row, i }))
    .sort((a, b) => {
      const va = accessor(a.row);
      const vb = accessor(b.row);
      const aNull = va === null || va === undefined || va === "";
      const bNull = vb === null || vb === undefined || vb === "";
      if (aNull && bNull) return a.i - b.i;
      if (aNull) return 1;
      if (bNull) return -1;
      let cmp: number;
      if (typeof va === "number" && typeof vb === "number") {
        cmp = va - vb;
      } else if (typeof va === "boolean" && typeof vb === "boolean") {
        cmp = Number(va) - Number(vb);
      } else {
        cmp = String(va).localeCompare(String(vb), undefined, { sensitivity: "base", numeric: true });
      }
      return cmp !== 0 ? cmp * state.dir : a.i - b.i;
    })
    .map((x) => x.row);
}

/** A sortable <th>; the callback stores the next state and the view re-sorts through sortRows. */
export function sortableTh(
  label: string,
  key: string,
  state: SortState | null,
  onSort: (next: SortState) => void,
  opts: { numeric?: boolean } = {}
): TemplateResult {
  const active = state?.key === key;
  const ariaSort = active ? (state!.dir === 1 ? "ascending" : "descending") : "none";
  const arrow = active ? (state!.dir === 1 ? "▲" : "▼") : "⇅";
  return html`
    <th class="sortable ${opts.numeric ? "num" : ""}" aria-sort=${ariaSort}>
      <button
        type="button"
        class="sort-btn"
        title="Sort by ${label}"
        @click=${() => onSort(nextSort(state, key))}
      >
        ${label}<span class="sort-arrow ${active ? "active" : ""}" aria-hidden="true">${arrow}</span>
      </button>
    </th>
  `;
}
