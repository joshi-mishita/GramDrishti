"""Feature group -> plain sentence, in English. Hindi and Punjabi are left null (placeholders) until a
native speaker writes them; the UI falls back to English.

A reason reads "<what is different here>, so it is likely <effect> than the block average."
The first half depends on whether the Panchayat's feature value is above or below its block's
average ("higher" / "lower"); categorical groups name the Panchayat's own class; block-wide groups
(the same value for every Panchayat in the block) have one fixed phrase. The second half depends on
the sign of the SHAP contrast.
"""

from __future__ import annotations

EFFECT_WORD = {"warmer": "warmer", "cooler": "cooler", "wetter": "wetter", "drier": "drier",
               "more_humid": "more humid", "less_humid": "less humid", "windier": "windier",
               "calmer": "calmer"}

# Effect of a positive contribution, per served variable (RH is explained through the dew point model).
EFFECT_POS = {"tmax": "warmer", "tmin": "warmer", "rain": "wetter", "rh": "more_humid", "wind": "windier"}
EFFECT_NEG = {"tmax": "cooler", "tmin": "cooler", "rain": "drier", "rh": "less_humid", "wind": "calmer"}

# Direction-aware phrases for groups that vary inside a block: (value above block average, below).
# " than the rest of the block" is appended unless the phrase already makes its own comparison.
REST = " than the rest of the block"
PHRASE = {
    "position_ns": ("Lies further north than most of the block", "Lies further south than most of the block"),
    "position_ew": ("Lies further east than most of the block", "Lies further west than most of the block"),
    "elevation": ("Higher ground", "Lower ground"),
    "tpi": ("Sits higher in the landscape than most of the block",
            "Sits lower in the landscape than most of the block"),
    "slope": ("Steeper land", "Flatter land"),
    "irrigated": ("More irrigated fields", "Fewer irrigated fields"),
    "canal_distance": ("Further from a canal than most of the block",
                       "Closer to a canal than most of the block"),
    "cropland": ("More farmland", "Less farmland"),
    "urban": ("More built-up land", "Less built-up land"),
    "water": ("More ponds and open water", "Less open water"),
    "trees": ("More tree cover", "Less tree cover"),
    "clay": ("More clay in the soil", "Less clay in the soil"),
    "sand": ("Sandier soil", "Less sandy soil"),
    "silt": ("More silt in the soil", "Less silt in the soil"),
    "water_holding": ("Soil holds more water", "Soil holds less water"),
    "vegetation": ("Greener crops and vegetation (satellite)", "Less green vegetation (satellite)"),
    "greening": ("Crops greening faster (satellite)", "Crops greening more slowly (satellite)"),
    "land_surface_temp": ("Hotter ground in recent satellite images",
                          "Cooler ground in recent satellite images"),
}
# Categorical groups: the Panchayat's own class is filled in.
CATEGORY_PHRASE = {"drainage": "Its {value} soil drainage", "soil_texture": "Its {value} soil"}
# Block-wide groups: every Panchayat in the block has the same value; they matter only through
# how they combine with local features.
BLOCK_WIDE_PHRASE = {
    "block_forecast": "The block forecast for this day, combined with local conditions",
    "season": "The time of year, combined with local conditions",
    "lead_day": "How many days ahead this forecast looks, combined with local conditions",
    "recent_rain": "Rain at the block's stations over the past week, combined with local conditions",
    "satellite_age": "How recent the satellite images are, combined with local conditions",
}
SAME_PHRASE = "Local conditions in this Panchayat"
TEMPLATE = "{phrase}, so it is likely {effect} than the block average."


def phrase_for(group: str, direction: int, value: str | None = None) -> str:
    """First half of the sentence. ``direction`` is +1 (above block average), -1 (below) or 0."""
    if group in CATEGORY_PHRASE:
        return CATEGORY_PHRASE[group].format(value=(value or "unknown").replace("_", " "))
    if group in BLOCK_WIDE_PHRASE:
        return BLOCK_WIDE_PHRASE[group]
    if group in PHRASE and direction != 0:
        text = PHRASE[group][0 if direction > 0 else 1]
        return text if " than " in text or " compared " in text else _with_rest(text)
    return SAME_PHRASE


def _with_rest(text: str) -> str:
    """Insert the comparison before a trailing "(satellite)" note."""
    note = " (satellite)"
    if text.endswith(note):
        return text.removesuffix(note) + REST + note
    return text + REST


def effect_for(var: str, contribution: float) -> str:
    """Effect enum value from the sign of the contribution (0 counts as negative: never "warmer" by 0)."""
    return EFFECT_POS[var] if contribution > 0 else EFFECT_NEG[var]


def sentence(group: str, direction: int, var: str, contribution: float, value: str | None = None) -> dict:
    """LocalizedText dict. ``hi`` and ``pa`` are null placeholders (need native writing)."""
    en = TEMPLATE.format(phrase=phrase_for(group, direction, value),
                         effect=EFFECT_WORD[effect_for(var, contribution)])
    return {"en": en, "hi": None, "pa": None}
