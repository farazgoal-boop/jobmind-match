"""One-time cleanup pass: re-scan the HuntedContact registry and flag
obvious placeholder/example emails (a@b.com, admin@gmail.com, ...) as "low"
confidence instead of leaving them at medium/high. Never deletes anything.

Default is a dry run — prints what would change without touching the DB, so
the pattern can be sanity-checked before committing to it. Pass --apply to
actually write the reclassification.

Usage:
    python scripts/reclassify_placeholder_contacts.py            # dry run
    python scripts/reclassify_placeholder_contacts.py --apply    # write it
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlmodel import Session

from app.db import engine
from app.services.lead_hunter_registry import reclassify_placeholder_confidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply", action="store_true",
        help="Write the reclassification (default is dry run / report only).",
    )
    args = parser.parse_args()

    with Session(engine) as session:
        changed = reclassify_placeholder_confidence(session, dry_run=not args.apply)

    verb = "Reclassified" if args.apply else "Would reclassify"
    print(f"{verb} {len(changed)} contact(s) to 'low' confidence:\n")
    for row in changed:
        was = row["confidence"]  # pre-change value — dict is built before the row is mutated
        print(f"  [{was:>6} -> low] {row['email'] or row['whatsapp']:<40} source={row['source']!r}")

    if not args.apply and changed:
        print("\nDry run only — nothing written. Re-run with --apply to commit.")


if __name__ == "__main__":
    main()
