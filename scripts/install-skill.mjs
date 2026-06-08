#!/usr/bin/env node
import { cpSync, existsSync, mkdirSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RUNTIME_PATHS = [
  "SKILL.md",
  "agents",
  "locales",
  "prompts",
  "schemas",
  "templates",
  "validators",
];

function usage() {
  return `Usage:
  npx svgflow-response-skill [--skills-dir <path>] [--source <path>] [--name <folder>]
  npx github:fanchou/svgflow_response_skill [--skills-dir <path>]

Options:
  --skills-dir <path>  Target skills directory. Defaults to $CODEX_HOME/skills or ~/.codex/skills.
  --source <path>      Source folder containing SKILL.md. Defaults to this package root.
  --name <folder>      Installed skill folder name. Defaults to svgflow-response.
  --help               Show this help.
`;
}

function parseArgs(argv) {
  const args = {
    name: "svgflow-response",
    skillsDir: undefined,
    source: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--help" || arg === "-h") {
      args.help = true;
    } else if (arg === "--skills-dir") {
      args.skillsDir = argv[++index];
    } else if (arg === "--source") {
      args.source = argv[++index];
    } else if (arg === "--name") {
      args.name = argv[++index];
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

function homeDir() {
  return process.env.HOME || process.env.USERPROFILE;
}

function expandHome(path) {
  if (!path || path === "~") return homeDir();
  if (path.startsWith("~/") || path.startsWith("~\\")) {
    return join(homeDir(), path.slice(2));
  }
  return path;
}

function defaultSkillsDir() {
  if (process.env.SVGFLOW_SKILLS_DIR) return process.env.SVGFLOW_SKILLS_DIR;
  if (process.env.SKILLS_DIR) return process.env.SKILLS_DIR;
  if (process.env.CODEX_HOME) return join(process.env.CODEX_HOME, "skills");
  return join(homeDir(), ".codex", "skills");
}

function packageRoot() {
  return resolve(dirname(fileURLToPath(import.meta.url)), "..");
}

function copyRuntime(sourceRoot, targetRoot) {
  if (!existsSync(join(sourceRoot, "SKILL.md"))) {
    throw new Error(`SKILL.md not found in source folder: ${sourceRoot}`);
  }

  mkdirSync(targetRoot, { recursive: true });

  for (const relativePath of RUNTIME_PATHS) {
    const source = join(sourceRoot, relativePath);
    if (!existsSync(source)) continue;
    const target = join(targetRoot, relativePath);
    const isDirectory = statSync(source).isDirectory();
    cpSync(source, target, {
      recursive: isDirectory,
      force: true,
      errorOnExist: false,
    });
  }
}

try {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    process.stdout.write(usage());
    process.exit(0);
  }

  const sourceRoot = resolve(expandHome(args.source || packageRoot()));
  const skillsDir = resolve(expandHome(args.skillsDir || defaultSkillsDir()));
  const targetRoot = join(skillsDir, args.name);

  copyRuntime(sourceRoot, targetRoot);

  process.stdout.write(`Installed SVGFlow skill to: ${targetRoot}\n`);
  process.stdout.write("Restart your agent or start a new session so it can rediscover skill metadata.\n");
} catch (error) {
  process.stderr.write(`${error.message}\n\n${usage()}`);
  process.exit(1);
}
