#!/usr/bin/env python3
"""Validate the maintenance scope before updating skills.

Maintenance mode must explicitly specify the target scope. By default, it is
limited to the current project/current working directory. Maintaining the
DevProjectTeamSkill root skill itself is blocked unless the user explicitly
requests it.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = ROOT / ".trae" / "skills"

ALLOWED_SCOPE_PREFIXES = {
    "current_project",
    "current_directory",
    "dev-project-team-skill",
}


def discover_role_names() -> set[str]:
    if not SKILLS_DIR.exists():
        return set()
    return {
        child.name
        for child in SKILLS_DIR.iterdir()
        if child.is_dir() and (child / "SKILL.md").exists()
    }


def validate_scope(scope: str, explicit_dev_root: bool = False) -> tuple[bool, str]:
    if not scope or not scope.strip():
        return False, "maintenance_scope is required. Use --scope current_project or a specific role package."

    normalized = scope.strip().lower()
    roles = discover_role_names()
    if normalized in roles:
        return True, f"scope={normalized} is allowed for this workspace"

    if normalized in ALLOWED_SCOPE_PREFIXES:
        if normalized == "dev-project-team-skill" and not explicit_dev_root:
            return False, "Maintaining DevProjectTeamSkill itself requires explicit user authorization; use --allow-dev-project-team-skill or --scope current_project."
        return True, f"scope={normalized} is allowed for this workspace"

    return False, (
        f"Unsupported scope '{scope}'. Allowed scopes: current_project, current_directory, "
        f"{', '.join(sorted(roles)) or 'role-*'}; DevProjectTeamSkill requires explicit authorization."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate maintenance scope before editing skills.")
    parser.add_argument("--scope", help="Scope to maintain: current_project, current_directory, a role name, or dev-project-team-skill")
    parser.add_argument("--allow-dev-project-team-skill", action="store_true", help="Explicit authorization to maintain the DevProjectTeamSkill root skill")
    args = parser.parse_args()

    if not args.scope:
        print("ERROR: maintenance_scope is required before skill maintenance starts.", file=sys.stderr)
        print("Example: python3 tools/check_maintenance_scope.py --scope current_project", file=sys.stderr)
        return 2

    ok, msg = validate_scope(args.scope, explicit_dev_root=args.allow_dev_project_team_skill)
    if not ok:
        print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    print(f"OK: {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
