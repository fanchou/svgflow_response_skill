#!/usr/bin/env python3
"""Install the runtime SVGFlow skill folder into a Codex skills directory."""

from __future__ import annotations

import argparse
import os
import shutil
from pathlib import Path


RUNTIME_PATHS = [
    "SKILL.md",
    "agents",
    "locales",
    "prompts",
    "schemas",
    "templates",
    "validators",
    "scripts/render_infographic.py",
]


def default_skills_dir() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "skills"
    return Path.home() / ".codex" / "skills"


def copy_path(source: Path, target: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, target, dirs_exist_ok=True)
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def install(source_root: Path, skills_dir: Path, name: str) -> Path:
    if not (source_root / "SKILL.md").is_file():
        raise SystemExit(f"SKILL.md not found in source root: {source_root}")

    target_root = skills_dir / name
    target_root.mkdir(parents=True, exist_ok=True)

    for relative in RUNTIME_PATHS:
        source = source_root / relative
        if source.exists():
            copy_path(source, target_root / relative)

    return target_root


def main() -> None:
    parser = argparse.ArgumentParser(description="Install SVGFlow as a Codex skill.")
    parser.add_argument(
        "--source",
        default=".",
        help="Path to the repository or skill source root containing SKILL.md.",
    )
    parser.add_argument(
        "--skills-dir",
        default=None,
        help="Codex skills directory. Defaults to $CODEX_HOME/skills or ~/.codex/skills.",
    )
    parser.add_argument(
        "--name",
        default="svgflow-response",
        help="Installed skill folder name.",
    )
    args = parser.parse_args()

    source_root = Path(args.source).expanduser().resolve()
    skills_dir = Path(args.skills_dir).expanduser().resolve() if args.skills_dir else default_skills_dir()
    target_root = install(source_root, skills_dir, args.name)
    print(f"Installed SVGFlow skill to: {target_root}")
    print("Restart Codex or start a new thread so the skill metadata can be rediscovered.")


if __name__ == "__main__":
    main()
