// prepack: stage the kernel from the repo (npm/ never commits staged copies).
import { cpSync, rmSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, "..");

rmSync(path.join(here, "scripts"), { recursive: true, force: true });
cpSync(path.join(repo, "scripts"), path.join(here, "scripts"), { recursive: true });
cpSync(path.join(repo, "LICENSE"), path.join(here, "LICENSE"));
rmSync(path.join(here, "scripts", "__pycache__"), { recursive: true, force: true });
console.log("staged scripts/ LICENSE from repo root");
