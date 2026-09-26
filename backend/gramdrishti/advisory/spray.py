"""Day-level spray planner (Backend Guide 9.7): Good, Caution or Avoid for each forecast day.

DAY-LEVEL ONLY. The forecast and all mock data are daily, so a rating covers a whole day. It cannot say
"spray between 6 and 9 am"; hour-level spray windows need hourly NWP (GFS gives 3-hourly fields) and
are future work. Nothing in the API or the advisory text may claim an hour-level window.

A day is rated from the chance of 2.5 mm or more of rain on that day and on the following day (rain
soon after spraying washes it off) and from the upper estimate (p90) of that day's wind (drift).
The thresholds are PLACEHOLDERS in ``rules.yaml`` (``spray_planner``).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

GOOD, CAUTION, AVOID = "good", "caution", "avoid"
THRESHOLD_NAMES = ("avoid_rain_today", "avoid_rain_next_day", "avoid_wind",
                   "caution_rain_today", "caution_rain_next_day", "caution_wind")


def _at_least(x: float | None, limit: float) -> bool:
    return x is not None and x >= limit


def day_rating(p_today: float | None, p_next: float | None, wind_p90: float | None,
               th: Mapping[str, float]) -> str:
    """Rating for one whole day. A missing number never makes a day worse; with no rain chance for
    the day itself the day is Caution, since nothing says it is safe."""
    if p_today is None:
        return CAUTION
    if (_at_least(p_today, th["avoid_rain_today"]) or _at_least(p_next, th["avoid_rain_next_day"])
            or _at_least(wind_p90, th["avoid_wind"])):
        return AVOID
    if (_at_least(p_today, th["caution_rain_today"]) or _at_least(p_next, th["caution_rain_next_day"])
            or _at_least(wind_p90, th["caution_wind"])):
        return CAUTION
    return GOOD


def plan(p_rain_2_5: Sequence[float | None], wind_p90: Sequence[float | None],
         th: Mapping[str, float]) -> list[str]:
    """Ratings for consecutive days. The last day has no following day in the forecast, so only its own
    rain and wind count (its rating can be too optimistic)."""
    n = len(p_rain_2_5)
    return [day_rating(p_rain_2_5[i], p_rain_2_5[i + 1] if i + 1 < n else None, wind_p90[i], th)
            for i in range(n)]
