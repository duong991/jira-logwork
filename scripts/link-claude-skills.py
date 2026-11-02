#!/usr/bin/env python3
"""Expose `.agents/skills/*` to Claude Code through `.claude/skills/*` symlinks.

`.agents/skills/` stays the single source of truth. Each skill directory that
contains a `SKILL.md` gets a relative symlink `.claude/skills/<name>` pointing at
`../../.agents/skills/<name>`. Stale symlinks that point into `.agents/skills/`
are removed; real directories and foreign links in `.claude/skills/` are never
touched.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source_skills(root: Path) -> list[str]:
    skills_dir = root / ".agents" / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(
        path.name
        for path in skills_dir.iterdir()
        if path.is_dir() and not path.is_symlink() and (path / "SKILL.md").is_file()
    )


def expected_target(name: str) -> str:
    return os.path.join("..", "..", ".agents", "skills", name)


def points_into_agents(link: Path) -> bool:
    return os.readlink(link).replace("\\", "/").startswith("../../.agents/skills/")


def plan(root: Path) -> tuple[list[str], list[str], list[str]]:
    """Return (missing-or-wrong links to create, stale links to remove, conflicts)."""
    claude_dir = root / ".claude" / "skills"
    skills = source_skills(root)
    create: list[str] = []
    remove: list[str] = []
    conflicts: list[str] = []
    for name in skills:
        link = claude_dir / name
        if link.is_symlink():
            if os.readlink(link) != expected_target(name):
                create.append(name)
        elif link.exists():
            conflicts.append(name)
        else:
            create.append(name)

    if claude_dir.is_dir():
        known = set(skills)
        for entry in claude_dir.iterdir():
            if entry.is_symlink() and points_into_agents(entry) and entry.name not in known:
                remove.append(entry.name)

    return sorted(create), sorted(remove), sorted(conflicts)


def apply(root: Path) -> int:
    claude_dir = root / ".claude" / "skills"
    claude_dir.mkdir(parents=True, exist_ok=True)
    create, remove, conflicts = plan(root)

    if conflicts:
        for name in conflicts:
            print(f"conflict: {claude_dir / name} is not a symlink, skipping", file=sys.stderr)

    for name in remove:
        (claude_dir / name).unlink()
        print(f"removed:  .claude/skills/{name}")

    for name in create:
        link = claude_dir / name
        if link.is_symlink():
            link.unlink()
        link.symlink_to(expected_target(name))
        print(f"linked:   .claude/skills/{name} -> {expected_target(name)}")

    return 1 if conflicts else 0


def check(root: Path) -> int:
    create, remove, conflicts = plan(root)
    if not (create or remove or conflicts):
        print("ok: .claude/skills is in sync with .agents/skills")
        return 0

    for name in create:
        print(f"missing:  .claude/skills/{name}")
    for name in remove:
        print(f"stale:    .claude/skills/{name}")
    for name in conflicts:
        print(f"conflict: .claude/skills/{name}")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="exit non-zero if symlinks are out of sync")
    args = parser.parse_args()
    return check(ROOT) if args.check else apply(ROOT)


if __name__ == "__main__":
    sys.exit(main())
