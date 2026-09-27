"""Spoken advisories: MP3 files made with gTTS and cached under ``backend/artifacts/audio/`` (git-ignored).

gTTS sends the text to Google's text-to-speech service, so making a new file needs internet access. A
cached file is served without it. The file name carries a hash of the spoken text, so an officer's edit
produces a new file instead of replaying the old wording.

Any failure (gTTS not installed, a language gTTS does not list, no text in that language, no internet,
a service error) raises ``AudioUnavailable``; the API answers 404 ``audio_not_available`` and the
frontend falls back to the browser's own speech.
"""

from __future__ import annotations

import hashlib
import logging
import os
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from gramdrishti.data.config import ART

AUDIO_DIR = ART / "audio"
LANGS = ("en", "hi", "pa")
PARTS = ("action", "reason", "fallback")
TIMEOUT_S = 10.0
log = logging.getLogger("gramdrishti.audio")

Synth = Callable[[str, str, Path], None]


class AudioUnavailable(Exception):
    """No audio can be served for this advisory and language."""


@lru_cache(maxsize=1)
def supported_langs() -> frozenset[str]:
    """Our languages that the installed gTTS lists (empty when gTTS is not installed). No network."""
    try:
        from gtts.lang import tts_langs
    except ImportError:
        return frozenset()
    return frozenset(lang for lang in LANGS if lang in tts_langs())


def speech_text(advisory: dict, lang: str) -> str | None:
    """Action, reason and fallback in ``lang`` joined into one text; None when the action has no text in
    that language (for example Hindi nulled by an English-only edit)."""
    texts = [(advisory.get(p) or {}).get(lang) for p in PARTS]
    if not texts[0]:
        return None
    return " ".join(t.strip() for t in texts if t)


def cache_path(root: Path, advisory_id: str, lang: str, text: str) -> Path:
    """``<root>/<advisory id>_<lang>_<hash of text>.mp3``."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return root / f"{advisory_id}_{lang}_{digest}.mp3"


def gtts_synth(text: str, lang: str, path: Path) -> None:
    """Write an MP3 of ``text`` with gTTS (needs internet). Writes to a temporary file first, so a failed
    or concurrent call never leaves a broken file at ``path``."""
    from gtts import gTTS

    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        gTTS(text, lang=lang, timeout=TIMEOUT_S).save(str(tmp))
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def audio_file(advisory: dict, lang: str, root: Path = AUDIO_DIR, synth: Synth = gtts_synth) -> Path:
    """Path of the cached MP3 for this advisory and language, making it first if needed.

    Raises ``AudioUnavailable`` with a plain reason when no audio can be served.
    """
    text = speech_text(advisory, lang)
    if text is None:
        raise AudioUnavailable(f"Advisory {advisory['id']} has no {lang} text")
    path = cache_path(root, advisory["id"], lang, text)
    if path.is_file() and path.stat().st_size > 0:
        return path
    if synth is gtts_synth and lang not in supported_langs():
        raise AudioUnavailable("Text-to-speech (gTTS) is not installed" if not supported_langs()
                               else f"The installed gTTS does not support language '{lang}'")
    root.mkdir(parents=True, exist_ok=True)
    try:
        synth(text, lang, path)
    except Exception as exc:  # noqa: BLE001 - any failure means "no audio"; the UI falls back
        log.warning("audio for %s (%s) failed: %s", advisory["id"], lang, exc)
        raise AudioUnavailable(f"Audio for {advisory['id']} in {lang} could not be generated "
                               "(text-to-speech needs internet access)") from exc
    if not path.is_file() or path.stat().st_size == 0:
        raise AudioUnavailable(f"Audio for {advisory['id']} in {lang} came back empty")
    return path
