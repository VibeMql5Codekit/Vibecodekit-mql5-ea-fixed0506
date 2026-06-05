"""/mql5-ship — tag + push the current commit.

Phase E command.  Thin wrapper around ``git tag`` + ``git push``.  Does
NOT trigger a PR review or CI pipeline by itself; the assumption is
that CI is already green on the merge commit you're tagging.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class ShipReport:
    tag: str
    commit: str
    pushed: bool
    detail: str = ""


def ship(tag: str, dry_run: bool = False) -> ShipReport:
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True,
    ).strip()
    rep = ShipReport(tag=tag, commit=sha, pushed=False)
    if dry_run:
        rep.detail = "dry-run; no tag/push performed"
        return rep
    subprocess.check_call(["git", "tag", tag])
    subprocess.check_call(["git", "push", "origin", tag])
    rep.pushed = True
    return rep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="mql5-ship")
    parser.add_argument("--tag", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    rep = ship(args.tag, dry_run=args.dry_run)
    print(json.dumps(rep.__dict__, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
