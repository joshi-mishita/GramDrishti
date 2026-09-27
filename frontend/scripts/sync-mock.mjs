// Copies contract/examples/ into public/mock/ so the app can run without a server.
// public/mock/ is git-ignored: contract/examples/ is the single source of truth.
//
// Snapshot (offline demo insurance, VITE_SNAPSHOT=1): contract/snapshot/ from
// `python -m gramdrishti.export_snapshot` is copied into public/snapshot/ only when
// VITE_SNAPSHOT=1 is set or `--snapshot` is passed (`npm run sync:snapshot`). Otherwise
// public/snapshot/ is removed, so a normal build does not carry about 100 MB of files.
// Both targets are git-ignored.
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../contract/examples");
const dest = resolve(here, "../public/mock");
const snapSrc = resolve(here, "../../contract/snapshot");
const snapDest = resolve(here, "../public/snapshot");
const wantSnapshot = process.argv.includes("--snapshot") || process.env.VITE_SNAPSHOT === "1";

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

if (!wantSnapshot) {
  if (existsSync(snapDest)) {
    rmSync(snapDest, { recursive: true, force: true });
    console.log("sync:mock: removed public/snapshot (set VITE_SNAPSHOT=1 to use the snapshot)");
  }
} else if (existsSync(join(snapSrc, "index.json"))) {
  rmSync(snapDest, { recursive: true, force: true });
  cpSync(snapSrc, snapDest, { recursive: true });
  const n = readdirSync(snapDest).length - 1;
  console.log(`sync:mock: copied ${n} snapshot files from contract/snapshot to public/snapshot`);
} else {
  console.error(
    "sync:mock: VITE_SNAPSHOT=1 needs contract/snapshot/index.json. Export it first:\n" +
      "  cd backend && python -m gramdrishti.export_snapshot",
  );
  process.exit(1);
}
