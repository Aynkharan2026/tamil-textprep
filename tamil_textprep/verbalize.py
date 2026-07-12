"""Per-class verbalization → Eezham-correct spoken Tamil.

House rules (corpus-evidenced, flagged for Kumar Annai's ratification):
  * டொலர் not டாலர் (ThaiVeedu corpus 178:11), சதம் for cents
  * புள்ளி not பாயிண்ட் (251:0), பூச்சியம் not பூஜ்ஜியம் (44:0)
  * % → வீதம், dates → …ஆம் திகதி, months = corpus spellings (ஜூலை, ஒக்டோபர்)
  * Slash dates: DD/MM/YYYY house rule (documented failure mode in classify.py)
  * Large numbers: convention='million' for CAD/Canadian contexts,
    'lakh' for LKR/homeland — per-call, corpus proves both are house forms.
"""
from __future__ import annotations

import re

from . import numwords as nw
from .classify import Span

MONTHS = {
    1: "ஜனவரி", 2: "பெப்ரவரி", 3: "மார்ச்", 4: "ஏப்ரல்", 5: "மே", 6: "ஜூன்",
    7: "ஜூலை", 8: "ஓகஸ்ட்", 9: "செப்டெம்பர்", 10: "ஒக்டோபர்",
    11: "நவம்பர்", 12: "டிசம்பர்",
}

CURRENCY = {
    "$": ("டொலர்", "சதம்"), "CAD": ("கனடிய டொலர்", "சதம்"),
    "USD": ("அமெரிக்க டொலர்", "சதம்"), "£": ("பவுண்", "பென்ஸ்"),
    "€": ("யூரோ", "சதம்"), "LKR": ("ரூபா", "சதம்"), "ரூ.": ("ரூபா", "சதம்"),
    "INR": ("இந்திய ரூபாய்", "பைசா"),
}


def _int(s: str) -> int:
    return int(re.sub(r"[^\d]", "", s))


def _day_ordinal(d: int) -> str:
    return nw._am_suffix(nw.cardinal(d, "lakh")) + " திகதி"


def verbalize(span: Span, convention: str = "million") -> str:
    cls, v = span.cls, span.value
    conv = span.opts.get("convention", convention)

    if cls == "digits":
        return nw.digits(v, group=int(span.opts.get("group", 0)))
    if cls == "phone":
        return nw.digits(v, group=0 if re.search(r"\D", v.strip("+")) else 3)
    if cls == "year":
        return nw.year(_int(v))
    if cls == "year_ord":
        return nw.year_ordinal(_int(v))
    if cls == "date":  # ISO YYYY-MM-DD
        y, mo, d = (int(x) for x in v.split("-"))
        return f"{MONTHS[mo]} {_day_ordinal(d)} {nw.year(y)}"
    if cls == "date_dmy":  # house rule DD/MM/YYYY
        d, mo, y = (int(x) for x in re.split(r"/", v))
        return f"{MONTHS[mo]} {_day_ordinal(d)} {nw.year(y)}"
    if cls == "time":
        h, mi = (int(x) for x in v.split(":"))
        ampm = "காலை" if h < 12 else ("பிற்பகல்" if h < 17 else "இரவு" if h >= 20 else "மாலை")
        h12 = h % 12 or 12
        if mi == 0:
            return f"{ampm} {nw.cardinal(h12)} மணி"
        if mi == 30:
            return f"{ampm} {nw.cardinal(h12)} மணி முப்பது"
        return f"{ampm} {nw.cardinal(h12)} மணி {nw.cardinal(mi)}"
    if cls == "money":
        m = re.match(r"([$£€]|CAD|USD|LKR|INR|ரூ\.)?\s?([\d,]+(?:\.\d+)?)\s?([$£€]|CAD|USD|LKR|ரூ\.)?", v.strip())
        cur = (m.group(1) or m.group(3) or "$").strip()
        unit, sub = CURRENCY.get(cur, ("டொலர்", "சதம்"))
        amt = m.group(2)
        # currency convention: LKR/INR homeland → lakh; else million
        cconv = "lakh" if cur in ("LKR", "ரூ.", "INR") else "million"
        if "." in amt:
            whole, fr = amt.split(".")
            return f"{nw.cardinal(_int(whole), cconv)} {unit} {nw.cardinal(_int(fr))} {sub}"
        return f"{nw.cardinal(_int(amt), cconv)} {unit}"
    if cls == "pct":
        num = re.sub(r"[%\s]", "", v)
        if "." in num:
            return nw.decimal(_int(num.split(".")[0]), num.split(".")[1]) + " வீதம்"
        return nw.cardinal(_int(num), "lakh") + " வீதம்"
    if cls == "decimal":
        whole, fr = v.split(".")
        return nw.decimal(int(whole), fr, conv)
    if cls == "range":
        a, b = (x.strip() for x in re.split(r"\s?[–—-]\s?", v))
        # Year ranges (16xx–20xx, historical corpus needs pre-1900):
        # abbreviated second years expand — 1937–45 means 1937–1945,
        # 1870–1 means 1870–1871 (Layer-1 corpus-audit find: the literal
        # reading produced "from 1870 to one").
        if re.fullmatch(r"(1[6-9]|20)\d{2}", a):
            ai = int(a)
            if re.fullmatch(r"(1[6-9]|20)\d{2}", b):
                return f"{nw.year(ai)} முதல் {nw.year(int(b))} வரை"
            if re.fullmatch(r"\d{1,2}", b):
                bi = ai - ai % (10 ** len(b)) + int(b)
                if bi >= ai:
                    return f"{nw.year(ai)} முதல் {nw.year(bi)} வரை"
        return f"{nw.cardinal(_int(a), conv)} முதல் {nw.cardinal(_int(b), conv)} வரை"
    if cls == "comma_num":
        return nw.cardinal(_int(v), conv)
    if cls == "ordinal":
        return nw.ordinal(_int(v))
    if cls in ("age", "count", "num"):
        return nw.cardinal(_int(v), conv if cls == "num" else "lakh")
    if cls == "en":
        return v  # resolved by the lexicon/exception layer
    return v
