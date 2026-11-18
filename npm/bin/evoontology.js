#!/usr/bin/env node
// dsh-evoontology CLI — JS shell spawning the bundled Python kernel
// (the family sidecar pattern; subcommand names strip before routing).
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const argv = process.argv.slice(2);
const [cmd, ...rest] = argv;

// Artifacts land in the caller's cwd via EVO_HOME.
const env = {
  ...process.env,
  EVO_HOME: path.join(process.cwd(), ".evo"),
};

const r = spawnSync("python3", [path.join(root, "scripts", "evoontology.py"), ...argv], {
  stdio: "inherit",
  env,
});
process.exit(r.status ?? 1);
