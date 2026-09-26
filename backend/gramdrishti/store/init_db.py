"""Create or migrate the SQLite store.

Run: ``cd backend && python -m gramdrishti.store.init_db`` (``--db PATH`` for another file; the default is
``GRAMDRISHTI_DB`` or ``backend/artifacts/gramdrishti.sqlite``). Safe to run again: applied migrations are
skipped. ``run_daily`` and the API call the same function, so running this by hand is optional.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from gramdrishti.store.db import MIGRATIONS, db_path, init_db


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", type=Path, default=None,
                    help="database file (default: GRAMDRISHTI_DB or artifacts)")
    args = ap.parse_args(argv)
    path = args.db or db_path()
    version = init_db(path)
    print(f"{path}: schema version {version} (latest {max(v for v, _ in MIGRATIONS)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
