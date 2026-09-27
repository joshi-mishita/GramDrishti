// Copies contract/examples/ into public/mock/ so the app can run without a server.
// public/mock/ is git-ignored: contract/examples/ is the single source of truth.
// Also copies contract/snapshot/ (from `python -m gramdrishti.export_snapshot`) into
// public/snapshot/ when it exists, for VITE_SNAPSHOT=1. Both targets are git-ignored.
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../contract/examples");
const dest = resolve(here, "../public/mock");
const snapSrc = resolve(here, "../../contract/snapshot");
const snapDest = resolve(here, "../public/snapshot");

if (!existsSync(join(src, "index.json"))) {
  console.error(
    `sync:mock: ${src}/index.json not found. Generate the examples first:\n` +
      "  cd backend && python -m gramdrishti.contract.make_examples",
  );
  process.exit(1);
}

rmSync(dest, { recursive: true, force: true });
mkdirSync(dest, { recursive: true });
const files = readdirSync(src).filter((f) => f.endsWith(".json") || f.endsWith(".geojson"));
for (const f of files) cpSync(join(src, f), join(dest, f));
console.log(`sync:mock: copied ${files.length} files from contract/examples to public/mock`);

if (existsSync(join(snapSrc, "index.json"))) {
  rmSync(snapDest, { recursive: true, force: true });
  cpSync(snapSrc, snapDest, { recursive: true });
  const n = readdirSync(snapDest).length - 1;
  console.log(`sync:mock: copied ${n} snapshot files from contract/snapshot to public/snapshot`);
} else {
  console.log(
    "sync:mock: no contract/snapshot/ (VITE_SNAPSHOT=1 needs it: " +
      "cd backend && python -m gramdrishti.export_snapshot)",
  );
}
