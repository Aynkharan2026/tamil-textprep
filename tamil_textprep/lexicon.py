"""English-in-Tamil exception table + Eezham lexicon application.

The tables are DATA, not code — `data/english_exceptions.json` is owned
and edited by Karan / Kumar Annai (same governance family as the dialect
blocklist). Policies per entry:

  speak-as-english  — leave Latin as-is (engines that handle it)
  transliterate     — always replace with the Tamil-script rendering
  spell-out         — acronym: replace with letter-by-letter Tamil

Engine overrides: bulbul:v2 destroyed Latin brands in testing
(VoxTN→"Voxel", PBX→"போக்ஸ்"), so entries may set "v2": "transliterate"
while staying speak-as-english elsewhere.
"""
from __future__ import annotations

import json
import pathlib
import re

_DATA = pathlib.Path(__file__).parent / "data"


def _load(name: str) -> dict:
    return json.loads((_DATA / name).read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Reverse transliteration (dialect path): Tamil-script English → Latin.
#
# HISTORY: the original implementation in aravam-voice substring-matched the
# reversal dict anywhere in the text (re.escape only, no boundaries), which
# shredded ordinary Tamil words mid-word: பாடசாலைக்கு → "பாடசா, likeகு",
# பின்னர் → "PINனர்" — measured 5.5 corruptions per 1,000 words on the
# ThaiVeedu corpus. This implementation is WHOLE-TOKEN anchored: a reversal
# fires only when an entire Tamil token is the loanword, or the loanword plus
# one enclitic from a CLOSED suffix list. A prefix before the match
# (பாடசா|லைக்கு) can never fire.
# ---------------------------------------------------------------------------

_TAMIL_TOKEN = re.compile(r"[஀-௿]+")

# Closed list of case/enclitic continuations allowed after a loanword.
# Consonant-final loanwords (…்) drop the pulli before a vowel-sign suffix,
# so both "suffix after full form" and "vowel-sign suffix after de-pulli
# form" are tried. பின்னர்-style continuations (னர், வருமாறு…) are NOT here —
# that is the point.
_SUFFIXES = (
    "ை", "ையும்", "ுக்கு", "ுக்குப்", "ுக்கும்", "ுக்காக", "ில்", "ிலும்",
    "ின்", "ினை", "ால்", "ாலும்", "ுடன்", "ோடு", "ாக", "ாகவும்", "ும்",
    "ா", "ே", "ஸ்",
)


def _reverse_table() -> dict[str, str]:
    # reverse_tamil overrides tamil when the reversible transliteration differs
    # from the forward rendering (e.g. இமெயில்→email reverses, but the real
    # Tamil word மின்னஞ்சல் must never be Anglicized).
    return {e.get("reverse_tamil", e["tamil"]): e["term"]
            for e in _load("english_exceptions.json")["entries"] if e.get("reverse")}


def reverse_transliterate(text: str) -> str:
    """Whole-token Tamil-script→Latin loanword reversal. Never touches the
    interior of a Tamil word."""
    table = _reverse_table()

    def sub(m: re.Match) -> str:
        tok = m.group(0)
        hit = table.get(tok)
        if hit:
            return hit
        for ta, en in table.items():
            if not tok.startswith(ta[:-1] if ta.endswith("்") else ta):
                continue
            # exact form + suffix
            if tok.startswith(ta) and tok[len(ta):] in _SUFFIXES:
                return en + tok[len(ta):]
            # de-pulli form + vowel-sign suffix (கம்ப்யூட்டர் + ில் = கம்ப்யூட்டரில்)
            if ta.endswith("்") and tok.startswith(ta[:-1]):
                rest = tok[len(ta) - 1:]
                if rest in _SUFFIXES:
                    return en + rest
        return tok

    return _TAMIL_TOKEN.sub(sub, text)


def apply_english_exceptions(text: str, engine: str | None = None,
                             report: list | None = None) -> str:
    table = _load("english_exceptions.json")["entries"]
    ekey = "v2" if engine in ("sarvam_v2", "bulbul:v2") else None
    for entry in table:
        policy = entry.get(ekey) if ekey and entry.get(ekey) else entry["policy"]
        if policy == "speak-as-english":
            continue
        target = entry["tamil"] if policy == "transliterate" else entry.get("spelled", entry["tamil"])
        text, n = re.subn(rf"(?<![A-Za-z]){re.escape(entry['term'])}(?![A-Za-z])",
                          target, text)
        if n and report is not None:
            report.append((f"LEX:{entry['term']}", entry["term"], target))
    return text
