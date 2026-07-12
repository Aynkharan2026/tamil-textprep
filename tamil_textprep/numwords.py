"""Eezham-Tamil number verbalization.

Core cardinal engine is open-tamil's ``tamil.numeral`` (proper sandhi,
SL-literary இலட்சம் spelling, both lakh- and million-based groupings).
This wrapper exists because property testing (4,017 cases, 2026-07-12)
found the raw library needs:

  * பூஜ்ஜியம் → பூச்சியம்   (0 — ThaiVeedu corpus uses பூச்சியம் 44:0)
  * நூற்றி    → நூற்று      (101 → "நூற்றி ஒன்று" is the colloquial-Indian form)
  * whitespace: trailing space on lakh forms, double spaces in the
    million-based variant ("ஒரு  மில்லியன்")
  * tamilstr2num (reverse) fails on ~41% of forward output — do NOT use
    it as a validator; golden tests validate the forward direction.
"""
from __future__ import annotations

import re

from tamil import numeral as _numeral

# Post-fixes applied to every open-tamil output, in order.
_FIXES: list[tuple[str, str]] = [
    ("பூஜ்ஜியம்", "பூச்சியம்"),
    ("நூற்றி ", "நூற்று "),
    # Layer-1 corpus-audit finds (2026-07-12), corpus-evidenced:
    ("நாநூறு", "நானூறு"),        # 400 — corpus 65:0
    ("பனிரண்டு", "பன்னிரண்டு"),   # 12  — corpus 36:0
    ("தொன்னூ", "தொண்ணூ"),        # 90s — corpus 24:2 (covers தொன்னூறு/தொன்னூற்று-)
]

# Digit words for digit-by-digit reading (phone numbers, codes).
DIGIT_WORDS = {
    "0": "பூச்சியம்",
    "1": "ஒன்று",
    "2": "இரண்டு",
    "3": "மூன்று",
    "4": "நான்கு",
    "5": "ஐந்து",
    "6": "ஆறு",
    "7": "ஏழு",
    "8": "எட்டு",
    "9": "ஒன்பது",
}

# Ordinals 1–10 are irregular enough to table; above that the generic
# rule (final ு → ாவது) holds for open-tamil's cardinal endings.
_ORDINAL_TABLE = {
    1: "முதலாவது",
    2: "இரண்டாவது",
    3: "மூன்றாவது",
    4: "நான்காவது",
    5: "ஐந்தாவது",
    6: "ஆறாவது",
    7: "ஏழாவது",
    8: "எட்டாவது",
    9: "ஒன்பதாவது",
    10: "பத்தாவது",
}

MAX_N = 999_999_999_999  # beyond this, fall back to digit-by-digit


def _clean(s: str) -> str:
    for old, new in _FIXES:
        s = s.replace(old, new)
    return re.sub(r"\s+", " ", s).strip()


def cardinal(n: int, convention: str = "lakh") -> str:
    """Cardinal number in Tamil words.

    convention: 'lakh' (இலட்சம்/கோடி — homeland/LKR contexts) or
    'million' (மில்லியன்/பில்லியன் — Canadian/CAD contexts).
    ThaiVeedu's own pages use BOTH, by context (மில்லியன் 193 / லட்சம்-family
    194 hits) — so this is a per-call decision, never a global constant.
    """
    if n < 0:
        return "கழித்தல் " + cardinal(-n, convention)
    if n > MAX_N:
        return digits(str(n))
    if convention == "million":
        return _clean(_numeral.num2tamilstr_american(n))
    return _clean(_numeral.num2tamilstr(n))


def year(n: int) -> str:
    """Year form: 2024 → இரண்டாயிரத்து இருபத்து நான்கு (caller adds ஆம்/ஆண்டு).

    Fuses open-tamil's "இரண்டு ஆயிரத்து" / "ஓர் ஆயிரத்து" openings into the
    written year idiom (இரண்டாயிரத்து / ஆயிரத்து).
    """
    s = cardinal(n, "lakh")
    s = re.sub(r"^இரண்டு ஆயிரத்து", "இரண்டாயிரத்து", s)
    s = re.sub(r"^இரண்டு ஆயிரம்$", "இரண்டாயிரம்", s)
    s = re.sub(r"^ஓர் ஆயிரத்து", "ஆயிரத்து", s)
    return s


def year_ordinal(n: int) -> str:
    """2024 → இரண்டாயிரத்து இருபத்து நான்காம் (for '…ஆம் ஆண்டு')."""
    return _am_suffix(year(n))


def _am_suffix(s: str) -> str:
    """Attach the -ஆம் ordinal suffix with sandhi: நான்கு→நான்காம், ஐந்து→ஐந்தாம்."""
    if s.endswith("ு"):
        return s[:-1] + "ாம்"
    return s + " ஆம்"


def ordinal(n: int) -> str:
    """3 → மூன்றாவது."""
    if n in _ORDINAL_TABLE:
        return _ORDINAL_TABLE[n]
    s = cardinal(n, "lakh")
    if s.endswith("ு"):
        return s[:-1] + "ாவது"
    return s + " ஆவது"


def digits(ds: str, group: int = 0) -> str:
    """Digit-by-digit reading (phone numbers, codes): '416' → 'நான்கு ஒன்று ஆறு'.

    group>0 inserts a comma (a TTS pause) every `group` digits when the
    input has no separators of its own.
    """
    ds = re.sub(r"\D", "", ds)
    words = [DIGIT_WORDS[d] for d in ds]
    if group and len(words) > group:
        out = []
        for i, w in enumerate(words):
            if i and i % group == 0:
                out.append(",")
            out.append(w)
        return re.sub(r" ,", ",", " ".join(out))
    return " ".join(words)


def decimal(int_part: int, frac: str, convention: str = "lakh") -> str:
    """9.8 → ஒன்பது புள்ளி எட்டு (புள்ளி per corpus 251:0 over பாயிண்ட்)."""
    return f"{cardinal(int_part, convention)} புள்ளி {digits(frac)}"
