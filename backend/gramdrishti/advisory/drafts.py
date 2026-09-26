"""Generate draft advisories for one issue date and store them (used by ``run_daily`` and the API)."""

from __future__ import annotations

from datetime import date, datetime, time

import pandas as pd

from gramdrishti.advisory.engine import EngineResult, generate
from gramdrishti.advisory.rules import RuleFile, TemplateFile, load_checked
from gramdrishti.store.db import Store

# Drafts are stamped 08:00 on the issue date, not the wall clock, so a rebuild writes identical rows.
CREATED_AT = time(8, 0)


def created_at(issue: date) -> datetime:
    return datetime.combine(issue, CREATED_AT)


def note(rf: RuleFile, model_version: str | None) -> str:
    return (f"Draft from the rules engine: rules.yaml version {rf.version}, "
            f"thresholds {rf.thresholds_status}, "
            f"model {model_version or 'unknown'}.")


def create_drafts(store: Store, issue: date, forecast: pd.DataFrame, static: pd.DataFrame,
                  crops: pd.DataFrame, calendar: pd.DataFrame, *, data_mode: str, model_version: str | None,
                  rules: tuple[RuleFile, TemplateFile] | None = None) -> tuple[EngineResult, int, int]:
    """Run the engine and replace the stored drafts for ``issue``.

    Returns (engine result, drafts written, reviewed advisories left untouched).
    """
    rf, tf = rules or load_checked()
    result = generate(issue, forecast, static, crops, calendar, rf, tf)
    written, kept = store.replace_drafts(issue, result.advisories, created_at(issue), data_mode=data_mode,
                                         rules_version=rf.version, model_version=model_version,
                                         note=note(rf, model_version))
    return result, written, kept
