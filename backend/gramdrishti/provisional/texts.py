"""Text templates for the provisional API in English, Hindi and Punjabi.

The Hindi and Punjabi strings are drafts written by Claude Code and NEED NATIVE REVIEW before any farmer
sees them (every advisory carries ``translation_status: "needs_native_review"``). S8 moves advisory text
into the YAML rule files; these templates exist only so the stub API returns realistic shapes.
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


# ---------------------------------------------------------------- advisories (per category)
ADVISORY = {
    "spray": {
        "action": {"en": "Do not spray pesticide or fertiliser before {date}.",
                   "hi": "{date} से पहले कीटनाशक या खाद का छिड़काव न करें।",
                   "pa": "{date} ਤੋਂ ਪਹਿਲਾਂ ਕੀਟਨਾਸ਼ਕ ਜਾਂ ਖਾਦ ਦਾ ਛਿੜਕਾਅ ਨਾ ਕਰੋ।"},
        "reason": {"en": "Heavy rain is likely on {date}. It would wash the spray off.",
                   "hi": "{date} को भारी बारिश की संभावना है। छिड़काव धुल जाएगा।",
                   "pa": "{date} ਨੂੰ ਭਾਰੀ ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ ਹੈ। ਛਿੜਕਾਅ ਧੁਲ ਜਾਵੇਗਾ।"},
        "fallback": {"en": "If the sky stays clear for a full day, spray in the calm morning hours.",
                     "hi": "अगर पूरे दिन आसमान साफ़ रहे, तो सुबह हवा शांत होने पर छिड़काव करें।",
                     "pa": "ਜੇ ਪੂਰਾ ਦਿਨ ਅਸਮਾਨ ਸਾਫ਼ ਰਹੇ, ਤਾਂ ਸਵੇਰੇ ਹਵਾ ਸ਼ਾਂਤ ਹੋਣ ਤੇ ਛਿੜਕਾਅ ਕਰੋ।"},
    },
    "waterlogging": {
        "action": {"en": "Open the field drains today so water does not stand in the field.",
                   "hi": "आज ही खेत की नालियाँ खोल दें ताकि पानी खेत में न रुके।",
                   "pa": "ਅੱਜ ਹੀ ਖੇਤ ਦੀਆਂ ਨਾਲੀਆਂ ਖੋਲ੍ਹ ਦਿਓ ਤਾਂ ਜੋ ਪਾਣੀ ਖੇਤ ਵਿੱਚ ਨਾ ਖੜ੍ਹੇ।"},
        "reason": {"en": "Heavy rain is likely on {date} and the soil drains slowly.",
                   "hi": "{date} को भारी बारिश की संभावना है और मिट्टी से पानी धीरे निकलता है।",
                   "pa": "{date} ਨੂੰ ਭਾਰੀ ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ ਹੈ ਅਤੇ ਮਿੱਟੀ ਵਿੱਚੋਂ ਪਾਣੀ ਹੌਲੀ ਨਿਕਲਦਾ ਹੈ।"},
        "fallback": {"en": "If less than 10 mm of rain falls, no drain work is needed.",
                     "hi": "अगर 10 मिमी से कम बारिश हो, तो नाली का काम ज़रूरी नहीं।",
                     "pa": "ਜੇ 10 ਮਿਲੀਮੀਟਰ ਤੋਂ ਘੱਟ ਮੀਂਹ ਪਵੇ, ਤਾਂ ਨਾਲੀ ਦਾ ਕੰਮ ਜ਼ਰੂਰੀ ਨਹੀਂ।"},
    },
    "heat_stress": {
        "action": {"en": "Irrigate lightly in the evening to reduce heat stress.",
                   "hi": "गर्मी का असर कम करने के लिए शाम को हल्की सिंचाई करें।",
                   "pa": "ਗਰਮੀ ਦਾ ਅਸਰ ਘਟਾਉਣ ਲਈ ਸ਼ਾਮ ਨੂੰ ਹਲਕੀ ਸਿੰਚਾਈ ਕਰੋ।"},
        "reason": {"en": "The maximum temperature may reach {tmax} C on {date}.",
                   "hi": "{date} को अधिकतम तापमान {tmax} डिग्री सेल्सियस तक जा सकता है।",
                   "pa": "{date} ਨੂੰ ਵੱਧ ਤੋਂ ਵੱਧ ਤਾਪਮਾਨ {tmax} ਡਿਗਰੀ ਸੈਲਸੀਅਸ ਤੱਕ ਜਾ ਸਕਦਾ ਹੈ।"},
        "fallback": {"en": "If the day stays below 35 C, normal irrigation is enough.",
                     "hi": "अगर दिन का तापमान 35 डिग्री से कम रहे, तो सामान्य सिंचाई काफ़ी है।",
                     "pa": "ਜੇ ਦਿਨ ਦਾ ਤਾਪਮਾਨ 35 ਡਿਗਰੀ ਤੋਂ ਘੱਟ ਰਹੇ, ਤਾਂ ਆਮ ਸਿੰਚਾਈ ਕਾਫ਼ੀ ਹੈ।"},
    },
    "frost": {
        "action": {"en": "Give a light irrigation in the evening before {date} to protect the crop "
                         "from frost.",
                   "hi": "पाले से फसल बचाने के लिए {date} से पहले शाम को हल्की सिंचाई करें।",
                   "pa": "ਕੋਰੇ ਤੋਂ ਫ਼ਸਲ ਬਚਾਉਣ ਲਈ {date} ਤੋਂ ਪਹਿਲਾਂ ਸ਼ਾਮ ਨੂੰ ਹਲਕੀ ਸਿੰਚਾਈ ਕਰੋ।"},
        "reason": {"en": "The minimum temperature may fall to {tmin} C on {date}.",
                   "hi": "{date} को न्यूनतम तापमान {tmin} डिग्री सेल्सियस तक गिर सकता है।",
                   "pa": "{date} ਨੂੰ ਘੱਟੋ-ਘੱਟ ਤਾਪਮਾਨ {tmin} ਡਿਗਰੀ ਸੈਲਸੀਅਸ ਤੱਕ ਡਿੱਗ ਸਕਦਾ ਹੈ।"},
        "fallback": {"en": "If the night stays above 4 C, no frost protection is needed.",
                     "hi": "अगर रात का तापमान 4 डिग्री से ऊपर रहे, तो पाले से बचाव की ज़रूरत नहीं।",
                     "pa": "ਜੇ ਰਾਤ ਦਾ ਤਾਪਮਾਨ 4 ਡਿਗਰੀ ਤੋਂ ਉੱਪਰ ਰਹੇ, ਤਾਂ ਕੋਰੇ ਤੋਂ ਬਚਾਅ ਦੀ ਲੋੜ ਨਹੀਂ।"},
    },
    "irrigation": {
        "action": {"en": "Plan an irrigation in the next 2 days.",
                   "hi": "अगले 2 दिनों में सिंचाई की योजना बनाएँ।",
                   "pa": "ਅਗਲੇ 2 ਦਿਨਾਂ ਵਿੱਚ ਸਿੰਚਾਈ ਦੀ ਯੋਜਨਾ ਬਣਾਓ।"},
        "reason": {"en": "Little rain is expected over the next 5 days ({rain5} mm in total).",
                   "hi": "अगले 5 दिनों में कम बारिश की उम्मीद है (कुल {rain5} मिमी)।",
                   "pa": "ਅਗਲੇ 5 ਦਿਨਾਂ ਵਿੱਚ ਘੱਟ ਮੀਂਹ ਦੀ ਉਮੀਦ ਹੈ (ਕੁੱਲ {rain5} ਮਿਲੀਮੀਟਰ)।"},
        "fallback": {"en": "If more than 10 mm of rain falls, skip this irrigation.",
                     "hi": "अगर 10 मिमी से ज़्यादा बारिश हो, तो यह सिंचाई छोड़ दें।",
                     "pa": "ਜੇ 10 ਮਿਲੀਮੀਟਰ ਤੋਂ ਵੱਧ ਮੀਂਹ ਪਵੇ, ਤਾਂ ਇਹ ਸਿੰਚਾਈ ਛੱਡ ਦਿਓ।"},
    },
}
CATEGORY_FOR_RISK = {"heavy_rain": "spray", "waterlogging": "waterlogging", "heat": "heat_stress",
                     "frost": "frost", "dry_spell": "irrigation"}

# ---------------------------------------------------------------- priority headlines (per risk type)
HEADLINE = {
    "heavy_rain": {"en": "Heavy rain likely on {date}",
                   "hi": "{date} को भारी बारिश की संभावना",
                   "pa": "{date} ਨੂੰ ਭਾਰੀ ਮੀਂਹ ਦੀ ਸੰਭਾਵਨਾ"},
    "waterlogging": {"en": "Rain on {date} may waterlog slow-draining fields",
                     "hi": "{date} की बारिश से धीमी निकासी वाले खेतों में पानी भर सकता है",
                     "pa": "{date} ਦੇ ਮੀਂਹ ਨਾਲ ਹੌਲੀ ਨਿਕਾਸੀ ਵਾਲੇ ਖੇਤਾਂ ਵਿੱਚ ਪਾਣੀ ਭਰ ਸਕਦਾ ਹੈ"},
    "heat": {"en": "Hot day on {date}, up to {tmax} C",
             "hi": "{date} को गर्म दिन, {tmax} डिग्री तक",
             "pa": "{date} ਨੂੰ ਗਰਮ ਦਿਨ, {tmax} ਡਿਗਰੀ ਤੱਕ"},
    "frost": {"en": "Cold night on {date}, down to {tmin} C",
              "hi": "{date} को ठंडी रात, {tmin} डिग्री तक",
              "pa": "{date} ਨੂੰ ਠੰਢੀ ਰਾਤ, {tmin} ਡਿਗਰੀ ਤੱਕ"},
    "dry_spell": {"en": "Little rain in the next 5 days",
                  "hi": "अगले 5 दिनों में कम बारिश",
                  "pa": "ਅਗਲੇ 5 ਦਿਨਾਂ ਵਿੱਚ ਘੱਟ ਮੀਂਹ"},
}

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
