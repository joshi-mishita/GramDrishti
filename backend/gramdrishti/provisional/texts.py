"""Text templates for the provisional API in English, Hindi and Punjabi.

The Hindi and Punjabi strings are drafts written by Claude Code and NEED NATIVE REVIEW before any farmer
sees them. Advisory and priority text moved to ``advisory/templates.yaml`` in S8; what remains here is the
day-name helper, the change summary, feedback thanks and the S2 placeholders (S10 replaces those).
"""

from __future__ import annotations

from datetime import date

MONTHS = {
    "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September",
           "October", "November", "December"],
    "hi": ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर", "अक्टूबर",
           "नवंबर", "दिसंबर"],
    "pa": ["ਜਨਵਰੀ", "ਫ਼ਰਵਰੀ", "ਮਾਰਚ", "ਅਪ੍ਰੈਲ", "ਮਈ", "ਜੂਨ", "ਜੁਲਾਈ", "ਅਗਸਤ", "ਸਤੰਬਰ", "ਅਕਤੂਬਰ",
           "ਨਵੰਬਰ", "ਦਸੰਬਰ"],
}
LANGS = ("en", "hi", "pa")


def day_text(d: date, lang: str) -> str:
    """'10 September' in the chosen language."""
    return f"{d.day} {MONTHS[lang][d.month - 1]}"


def fill(templates: dict[str, str], d: date | None = None, **values: object) -> dict[str, str]:
    """Format one template per language; ``{date}`` becomes the localised day."""
    out = {}
    for lang, t in templates.items():
        extra = {"date": day_text(d, lang)} if d is not None else {}
        out[lang] = t.format(**extra, **values)
    return out


# ---------------------------------------------------------------- explain (static contrast placeholder)
FEATURE_TEXT = {
    "elevation_m": ({"en": "Higher ground than the block average", "hi": "ब्लॉक के औसत से ऊँची ज़मीन",
                     "pa": "ਬਲਾਕ ਦੀ ਔਸਤ ਨਾਲੋਂ ਉੱਚੀ ਜ਼ਮੀਨ"},
                    {"en": "Lower ground than the block average", "hi": "ब्लॉक के औसत से नीची ज़मीन",
                     "pa": "ਬਲਾਕ ਦੀ ਔਸਤ ਨਾਲੋਂ ਨੀਵੀਂ ਜ਼ਮੀਨ"}),
    "irrigated_frac": ({"en": "More irrigated fields around it", "hi": "आसपास ज़्यादा सिंचित खेत",
                        "pa": "ਆਲੇ-ਦੁਆਲੇ ਵੱਧ ਸਿੰਜੇ ਖੇਤ"},
                       {"en": "Fewer irrigated fields around it", "hi": "आसपास कम सिंचित खेत",
                        "pa": "ਆਲੇ-ਦੁਆਲੇ ਘੱਟ ਸਿੰਜੇ ਖੇਤ"}),
    "urban_frac": ({"en": "More built-up land", "hi": "ज़्यादा बसी हुई ज़मीन", "pa": "ਵੱਧ ਵਸੀ ਹੋਈ ਜ਼ਮੀਨ"},
                   {"en": "Less built-up land", "hi": "कम बसी हुई ज़मीन", "pa": "ਘੱਟ ਵਸੀ ਹੋਈ ਜ਼ਮੀਨ"}),
    "water_frac": ({"en": "More open water nearby", "hi": "पास में ज़्यादा खुला पानी",
                    "pa": "ਨੇੜੇ ਵੱਧ ਖੁੱਲ੍ਹਾ ਪਾਣੀ"},
                   {"en": "Less open water nearby", "hi": "पास में कम खुला पानी", "pa": "ਨੇੜੇ ਘੱਟ ਖੁੱਲ੍ਹਾ ਪਾਣੀ"}),
    "tree_frac": ({"en": "More tree cover", "hi": "ज़्यादा पेड़", "pa": "ਵੱਧ ਰੁੱਖ"},
                  {"en": "Less tree cover", "hi": "कम पेड़", "pa": "ਘੱਟ ਰੁੱਖ"}),
    "tpi_z": ({"en": "Sits higher than its surroundings", "hi": "आसपास से ऊँचाई पर स्थित",
               "pa": "ਆਲੇ-ਦੁਆਲੇ ਨਾਲੋਂ ਉਚਾਈ ਤੇ"},
              {"en": "Sits in a low spot where cold air collects",
               "hi": "निचले स्थान पर जहाँ ठंडी हवा जमा होती है",
               "pa": "ਨੀਵੀਂ ਥਾਂ ਤੇ ਜਿੱਥੇ ਠੰਢੀ ਹਵਾ ਇਕੱਠੀ ਹੁੰਦੀ ਹੈ"}),
}

# ---------------------------------------------------------------- misc
CHANGES_NONE = {"en": "No material change since the previous forecast.",
                "hi": "पिछले पूर्वानुमान के बाद कोई खास बदलाव नहीं।",
                "pa": "ਪਿਛਲੇ ਅਨੁਮਾਨ ਤੋਂ ਬਾਅਦ ਕੋਈ ਖ਼ਾਸ ਬਦਲਾਅ ਨਹੀਂ।"}
CHANGES_NO_PREVIOUS = {"en": "No earlier forecast to compare with.",
                       "hi": "तुलना के लिए कोई पिछला पूर्वानुमान नहीं है।",
                       "pa": "ਤੁਲਨਾ ਲਈ ਕੋਈ ਪਿਛਲਾ ਅਨੁਮਾਨ ਨਹੀਂ ਹੈ।"}
CHANGES_SOME = {"en": "The forecast changed for {n} day and variable pairs since {date}.",
                "hi": "{date} के पूर्वानुमान के बाद {n} जगह बदलाव हुआ है।",
                "pa": "{date} ਦੇ ਅਨੁਮਾਨ ਤੋਂ ਬਾਅਦ {n} ਥਾਵਾਂ ਤੇ ਬਦਲਾਅ ਹੋਇਆ ਹੈ।"}
FEEDBACK_THANKS = {"en": "Thank you. Your report helps improve the forecast for your village.",
                   "hi": "धन्यवाद। आपकी जानकारी से आपके गाँव का पूर्वानुमान बेहतर होता है।",
                   "pa": "ਧੰਨਵਾਦ। ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ ਨਾਲ ਤੁਹਾਡੇ ਪਿੰਡ ਦਾ ਅਨੁਮਾਨ ਬਿਹਤਰ ਹੁੰਦਾ ਹੈ।"}
IMPACT_RULES = {
    "spray": ("Advise spraying when the chance of 2.5 mm rain is under 30%.",
              "Advise spraying when the block forecast is under 2.5 mm."),
    "heat_alert": ("Alert when the 90th percentile of Tmax reaches the heat threshold.",
                   "Alert when the block Tmax forecast reaches the heat threshold."),
    "irrigation_wait": ("Wait to irrigate when the chance of 5 mm rain is 50% or more.",
                        "Wait to irrigate when the block forecast is 5 mm or more."),
}
