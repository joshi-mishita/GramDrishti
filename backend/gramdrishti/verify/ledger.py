"""The TEST window ledger (``docs/test_window_ledger.json``): when TEST was first opened, for which model.

CLAUDE.md rule 5 and ``docs/validation_protocol.md``: TEST is opened once per model version. The ledger is
committed, so a later model version can see that TEST was already used and its report must say so.
Re-running the same frozen version reproduces the same numbers and is recorded as another run, not a
new opening.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from gramdrishti.data.config import ROOT

LEDGER = ROOT / "docs" / "test_window_ledger.json"


@dataclass
class Opening:
    """What a validation run needs to say about the TEST window."""

    model_version: str
    first_opened_at: datetime
    reused: bool                  # TEST was opened before for another model version
    earlier_versions: list[str]


def _read(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {"entries": []}


def open_test(model_version: str, data_hash: str, code_commit: str, now: datetime,
              path: Path = LEDGER) -> Opening:
    """Record that TEST is being opened for ``model_version`` and return the opening facts.

    The first call for a version writes its ``first_opened_at``; later calls only append a run time.
    A different data hash for a known version is refused: that would be a new model under an old name.
    """
    led = _read(path)
    entries = led["entries"]
    mine = next((e for e in entries if e["model_version"] == model_version), None)
    if mine is not None and mine["data_hash_sha256"] != data_hash:
        raise RuntimeError(f"{model_version} was opened on TEST with a different data hash; "
                           "a changed model needs a new version number.")
    stamp = now.isoformat(timespec="seconds")
    if mine is None:
        mine = {"model_version": model_version, "data_hash_sha256": data_hash, "first_opened_at": stamp,
                "code_commit_at_first_open": code_commit, "runs": []}
        entries.append(mine)
    mine["runs"].append({"at": stamp, "code_commit": code_commit})
    path.write_text(json.dumps(led, indent=2) + "\n")
    first = datetime.fromisoformat(mine["first_opened_at"])
    earlier = [e["model_version"] for e in entries if e["model_version"] != model_version
               and datetime.fromisoformat(e["first_opened_at"]) < first]
    return Opening(model_version, first, bool(earlier), earlier)
