"""Seed five DEMO farmer profiles into the SQLite store (Backend Guide 10).

Run: ``cd backend && python -m gramdrishti.store.seed_demo``

These are demo profiles, not real people: the names say "Demo farmer" and nothing else about them is
personal. Each one sits in a different Panchayat with different crops and a different language; F001 and
F002 share block MB03 so the farmer app can show two neighbours getting different advice from the same
block forecast. Crops and sowing dates are the Panchayat's own rows in ``panchayat_crops_mock.csv``
(the advisories are made per Panchayat and crop, so a farmer's dates must match them). Seeding replaces
the whole ``farmers`` table and is idempotent. The API seeds on first use when the table is empty.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass

import pandas as pd

from gramdrishti.data import loaders
from gramdrishti.store.db import Store

# Seasons shown in a profile: the rabi before the demo dates, then kharif and rabi 2024.
SEASONS = ("rabi_2023_24", "kharif_2024", "rabi_2024_25")


@dataclass(frozen=True)
class DemoFarmer:
    id: str
    panchayat_id: str
    language: str
    crops: tuple[str, ...]
    livestock: bool
    why: str


DEMO_FARMERS = (
    DemoFarmer("F001", "MP0307", "hi", ("bajra", "wheat"), True,
               "low-lying Panchayat in the wettest block MB03; keeps cattle"),
    DemoFarmer("F002", "MP0311", "pa", ("bajra", "mustard"), False,
               "same block MB03 as F001, earlier bajra that nears harvest in September"),
    DemoFarmer("F003", "MP0601", "en", ("cotton", "mustard"), False, "cotton grower in block MB06"),
    DemoFarmer("F004", "MP0508", "hi", ("bajra", "gram"), True, "bajra and gram in block MB05; keeps cattle"),
    DemoFarmer("F005", "MP0103", "pa", ("wheat",), False,
               "wheat only in block MB01; the Panchayat's bajra advice is not for this farmer"),
)


def demo_farmers(crops: pd.DataFrame | None = None) -> list[dict]:
    """The demo farmers as store rows. Fails loudly if a profile's crop is missing from the crop table."""
    crops = loaders.load_crops() if crops is None else crops
    out = []
    for i, f in enumerate(DEMO_FARMERS):
        c = crops[(crops["panchayat_id"] == f.panchayat_id) & crops["season"].isin(SEASONS)
                  & crops["crop"].isin(f.crops)].sort_values(["sowing_date", "crop"])
        missing = set(f.crops) - set(c["crop"])
        if missing:
            raise ValueError(f"{f.id}: {f.panchayat_id} grows none of {sorted(missing)} in {SEASONS}")
        rows = [{"crop": r.crop, "season": r.season, "sowing_date": r.sowing_date.date().isoformat(),
                 "expected_harvest_date": (r.expected_harvest_date.date().isoformat()
                                           if pd.notna(r.expected_harvest_date) else None),
                 "area_fraction": round(float(r.crop_area_fraction), 2)}
                for r in c.itertuples(index=False)]
        out.append({"id": f.id, "name": f"Demo farmer {i + 1}", "panchayat_id": f.panchayat_id,
                    "language": f.language, "crops": rows, "livestock": f.livestock})
    return out


def seed(store: Store) -> int:
    """Write the demo farmers into ``store`` (replacing any). Returns the number written."""
    return store.replace_farmers(demo_farmers())


def main() -> None:
    """Seed the local store and print the profiles."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.parse_args()
    store = Store()
    n = seed(store)
    print(f"{n} demo farmers written to {store.path}")
    why = {f.id: f.why for f in DEMO_FARMERS}
    for f in store.farmers().values():
        crops = ", ".join(f"{c['crop']} ({c['season']}, sown {c['sowing_date']})" for c in f["crops"])
        print(f"  {f['id']} {f['name']:14} {f['panchayat_id']} {f['language']} "
              f"livestock={'yes' if f['livestock'] else 'no'}: {crops}\n       {why[f['id']]}")


if __name__ == "__main__":
    main()
