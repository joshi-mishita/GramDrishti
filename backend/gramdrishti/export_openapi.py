"""Write the OpenAPI document of the API to ``contract/openapi.json``.

Run: ``cd backend && python -m gramdrishti.export_openapi``. The frontend generates its types from this file
(``npm run gen:types``). A test fails when the committed file is out of date.
"""

from __future__ import annotations

import json
from pathlib import Path

from gramdrishti.api.main import create_app
from gramdrishti.data.config import ROOT

OUT = ROOT / "contract" / "openapi.json"


def openapi_text() -> str:
    """The OpenAPI document as stable, pretty-printed JSON."""
    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"


def main(out: Path = OUT) -> None:
    """Write ``contract/openapi.json``."""
    out.write_text(openapi_text(), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
