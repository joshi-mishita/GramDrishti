// Copies contract/examples/ into public/mock/ so the app can run without a server.
// public/mock/ is git-ignored: contract/examples/ is the single source of truth.
import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const src = resolve(here, "../../contract/examples");
const dest = resolve(here, "../public/mock");

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
