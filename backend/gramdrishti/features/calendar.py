"""Calendar features of the valid date plus the lead day."""

from __future__ import annotations

import numpy as np
import pandas as pd

NAMES = ["doy_sin", "doy_cos", "month", "lead_day"]


def calendar_features(valid_date: pd.Series, lead_day: pd.Series) -> pd.DataFrame:
    """sin/cos of day of year, month and lead day, aligned to the input index."""
    d = pd.to_datetime(valid_date)
    angle = 2 * np.pi * (d.dt.dayofyear - 1) / 365.25
    return pd.DataFrame({"doy_sin": np.sin(angle), "doy_cos": np.cos(angle), "month": d.dt.month,
                         "lead_day": lead_day.astype(int)}, index=valid_date.index)
