"""Text templates for the provisional API in English, Hindi and Punjabi.

The Hindi and Punjabi strings are drafts written by Claude Code and NEED NATIVE REVIEW before any farmer
sees them. Advisory and priority text moved to ``advisory/templates.yaml`` in S8; what remains here is the
day-name helper, the change summary and the feedback thanks. The S2 verification, impact and explain
placeholders were removed in S10.
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
FEEDBACK_THANKS = {"en": "Thank you. Your report helps us check the forecast for your village.",
                   "hi": "धन्यवाद। आपकी जानकारी से हम आपके गाँव के पूर्वानुमान की जाँच करते हैं।",
                   "pa": "ਧੰਨਵਾਦ। ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ ਨਾਲ ਅਸੀਂ ਤੁਹਾਡੇ ਪਿੰਡ ਦੇ ਅਨੁਮਾਨ ਦੀ ਜਾਂਚ ਕਰਦੇ ਹਾਂ।"}
FEEDBACK_DUPLICATE = {"en": "We already have this report. Thank you.",
                      "hi": "यह जानकारी हमें पहले ही मिल चुकी है। धन्यवाद।",
                      "pa": "ਇਹ ਜਾਣਕਾਰੀ ਸਾਨੂੰ ਪਹਿਲਾਂ ਹੀ ਮਿਲ ਚੁੱਕੀ ਹੈ। ਧੰਨਵਾਦ।"}
