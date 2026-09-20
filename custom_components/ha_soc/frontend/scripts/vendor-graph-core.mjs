/**
 * Refresh src/graph/ from a local clone of trooperthorn/relationship-maps.
 *
 * Usage: node scripts/vendor-graph-core.mjs [--from <path to relationship-maps>]
 * Default source: ../relationship-maps relative to this repository.
 */
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const DEST = resolve(HERE, "..", "src", "graph");

const args = process.argv.slice(2);
const fromIndex = args.indexOf("--from");
const source = resolve(
  fromIndex >= 0 && args[fromIndex + 1]
    ? args[fromIndex + 1]
    : join(HERE, "..", "..", "..", "..", "..", "relationship-maps"),
);
const core = join(source, "packages", "graph-core", "src");

const FILES = {
  "types.ts": join(core, "types.ts"),
  "theme.ts": join(core, "theme.ts"),
  "arc.ts": join(core, "layout", "arc.ts"),
  "force.ts": join(core, "layout", "force.ts"),
  "renderer.ts": join(core, "render", "renderer.ts"),
};

let commit = "unknown";
try {
  commit = execFileSync("git", ["-C", source, "rev-parse", "--short", "HEAD"], {
    encoding: "utf8",
  }).trim();
} catch {
  console.warn(`Could not read the upstream commit from ${source}; stamping "unknown".`);
}

mkdirSync(DEST, { recursive: true });
for (const [name, path] of Object.entries(FILES)) {
  const body = readFileSync(path, "utf8")
    .replaceAll("from '../theme'", "from './theme'")
    .replaceAll("from '../types'", "from './types'")
    // This repository's style rule forbids em dashes in committed files.
    .replaceAll(" \u2014 ", " - ")
    .replaceAll("\u2014", "-");
  const header =
    `// Vendored from trooperthorn/relationship-maps, packages/graph-core (commit ${commit}).\n` +
    "// Framework-neutral engine only: no React. Refresh with frontend/src/graph/VENDOR.md.\n";
  writeFileSync(join(DEST, name), header + body, "utf8");
  console.log(`vendored ${name}`);
}
console.log(`graph-core @ ${commit} -> ${DEST}`);
