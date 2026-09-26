"""Print stored advisories in plain English for reading and review (read-only).

Run: ``cd backend && python -m gramdrishti.advisory.show --issue-date 2024-09-09`` (one per rule, up to 10)
     ``... --issue-date 2024-09-09 --panchayat MP0307 MP0311 --crop bajra`` (compare Panchayats)
     ``... --issue-date 2024-12-24 --counts`` (advisories by category and status)
"""

from __future__ import annotations

import argparse
from datetime import date

from gramdrishti.store.db import Store


def render(a: dict, lang: str = "en") -> str:
    """One advisory as a short text block."""
    head = (f"{a['id']}  [{a['rule_id']}]  priority {a['priority']}, confidence {a['confidence']}, "
            f"stage {a['stage'] or '-'}, {a['valid_from']} to {a['valid_to']}, {a['status']}")
    body = [f"  Action:   {a['action'][lang]}", f"  Reason:   {a['reason'][lang]}",
            f"  Fallback: {a['fallback'][lang]}"]
    body += [f"    - {e['label']}: {e['value']}" for e in a["evidence"]]
    return "\n".join([head, *body])


def pick(items: list[dict], n: int) -> list[dict]:
    """First advisory of each rule (by id), then fill up to ``n`` in id order."""
    seen, first, rest = set(), [], []
    for a in items:
        (rest if a["rule_id"] in seen else first).append(a)
        seen.add(a["rule_id"])
    return (first + rest)[:n]


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--issue-date", type=date.fromisoformat, required=True)
    ap.add_argument("--panchayat", nargs="*", default=None, help="only these Panchayat ids")
    ap.add_argument("--crop", default=None)
    ap.add_argument("--n", type=int, default=10, help="how many to print (default 10)")
    ap.add_argument("--lang", choices=("en", "hi", "pa"), default="en")
    ap.add_argument("--counts", action="store_true", help="print counts by category and status only")
    args = ap.parse_args(argv)
    store = Store()
    if args.counts:
        c = store.counts(args.issue_date)
        print(f"{args.issue_date}: {sum(c['category'].values())} advisories")
        print("  by category: " + ", ".join(f"{k} {v}" for k, v in c["category"].items()))
        print("  by status:   " + ", ".join(f"{k} {v}" for k, v in c["status"].items()))
        return 0
    items = store.list(issue=args.issue_date)
    if args.panchayat:
        items = [a for a in items if a["panchayat_id"] in args.panchayat]
    if args.crop:
        items = [a for a in items if a["crop"] == args.crop]
    chosen = items if args.panchayat else pick(items, args.n)
    if not chosen:
        print(f"No advisories for {args.issue_date}. Run `python -m gramdrishti.pipeline.run_daily "
              "--all-demo-dates` first.")
    print("\n\n".join(render(a, args.lang) for a in chosen))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
