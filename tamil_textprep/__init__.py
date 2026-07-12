"""tamil-textprep — the shared Eelam-Tamil text-preparation layer.

One pipeline for every Tamil voice surface (Aravam Voice, ThaiVeedu
archive audio, VoxVoIP voice agents):

    sanitize → classify (tags → heuristics) → verbalize → lexicon → emit

Output is FULLY-VERBALIZED Tamil: no ASCII digits survive. We never rely
on a TTS engine to read numbers (engine matrix 2026-07-12: Sarvam v3
reads years digit-by-digit; v2 code-switches to English and reads 11/07
as November 7 where v3 says July 11; no engine-side control exists —
Sarvam TTS silently accepts and ignores unknown params).

Design rule: we verbalize ONLY spans we classified. The user's own Tamil
words are never rewritten here — dialect drift in prose is the dialect
guard's job (flag-for-review), not textprep's.
"""
from __future__ import annotations

import dataclasses
import logging
import re
import unicodedata

from . import numwords as nw
from .classify import Span, heuristic_spans, parse_tags
from .lexicon import apply_english_exceptions
from .verbalize import verbalize

__version__ = "0.2.1"
logger = logging.getLogger("tamil_textprep")

_ZW = re.compile(r"[​‌‍⁠﻿]")
_SMART = {"‘": "'", "’": "'", "“": '"', "”": '"',
          "–": "-", "—": "-", "−": "-"}

_ORD_SUFFIX = re.compile(r"^\s?-?(ஆவது|வது)")
_YEAR_AM = re.compile(r"^\s?-?(ஆம்|ம்)(?=\s?ஆண்டு)")
_YEAR_LOC = re.compile(r"^\s?-?(இல்|ல்)")


def sanitize(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = _ZW.sub("", text)
    for k, v in _SMART.items():
        text = text.replace(k, v)
    return re.sub(r"[ \t]+", " ", text)


def _consume_suffix(text: str, span: Span) -> tuple[Span, int]:
    """Extend a span over its grammatical suffix; returns (span, new_end)."""
    tail = text[span.end:]
    if span.cls == "ordinal":
        m = _ORD_SUFFIX.match(tail)
        if m:
            return span, span.end + m.end()
    if span.cls == "year_ord":
        m = _YEAR_AM.match(tail)
        if m:
            return span, span.end + m.end()
        m = _YEAR_LOC.match(tail)
        if m:
            span = dataclasses.replace(span, cls="year_loc")
            return span, span.end + m.end()
        # bare "2024 ஆண்டு" — no suffix to consume
        span = dataclasses.replace(span, cls="year_ord_bare")
    if span.cls == "pct" and "%" in span.value:
        # redundant source "25% வீதம்" — drop our வீதம், keep the writer's word
        if re.match(r"^\s?(சத)?வீத", text[span.end:]):
            span = dataclasses.replace(span, cls="pct_bare")
    return span, span.end


def _render(span: Span, convention: str) -> str:
    if span.cls == "year_loc":
        y = nw.year(int(re.sub(r"\D", "", span.value)))
        return y[:-1] + "ில்" if y.endswith("ு") else y + "இல்"
    if span.cls == "year_ord_bare":
        return nw.year_ordinal(int(re.sub(r"\D", "", span.value))) + " "
    if span.cls == "year_ord":
        return nw.year_ordinal(int(re.sub(r"\D", "", span.value)))
    if span.cls in ("pct", "pct_bare"):
        num = re.sub(r"[%\s]", "", span.value)
        if "%" in span.value and span.cls == "pct":
            return verbalize(span, convention)
        # source already carries வீதம்/சதவீதம் — cardinal only
        if "." in num:
            return nw.decimal(int(num.split(".")[0]), num.split(".")[1])
        return nw.cardinal(int(num))
    if span.cls == "money" and not re.search(r"[$£€]|CAD|USD|LKR|INR|ரூ\.", span.value):
        # unit word follows in source text — cardinal only
        return nw.cardinal(int(re.sub(r"[^\d]", "", span.value.split(".")[0])),
                           "million")
    return verbalize(span, convention)


def normalize(
    text: str,
    *,
    convention: str = "million",
    engine: str | None = None,
    llm_fallback=None,
    report: list | None = None,
) -> str:
    """Full pipeline. `report` (a list) collects (rule, original, spoken) audit rows.

    convention: default grouping for large numbers when context doesn't
    decide ('million' for Canadian surfaces; currency spans override —
    LKR/INR always lakh). engine: 'sarvam_v2' additionally transliterates
    Latin exception-table entries (v2 garbles English brands).
    llm_fallback: optional callable(text, spans)->spans, Tier-3 hook;
    OFF unless provided. Never used for archive audio.
    """
    text = sanitize(text)

    # Tier 1: explicit tags
    text, tag_spans = parse_tags(text)
    for i, sp in enumerate(tag_spans):
        spoken = verbalize(sp, convention)
        marker = f"\x00{i}\x00"
        text = text.replace(marker, spoken)
        if report is not None:
            report.append(("TAG:" + sp.cls, sp.value, spoken))

    # Tier 2: heuristics over remaining free text
    spans = heuristic_spans(text)
    if llm_fallback is not None:
        spans = llm_fallback(text, spans)  # Tier 3 (opt-in only)

    out: list[str] = []
    pos = 0
    for sp in spans:
        if sp.start < pos:
            continue
        sp, end = _consume_suffix(text, sp)
        spoken = _render(sp, convention)
        out.append(text[pos:sp.start])
        out.append(spoken)
        if report is not None:
            report.append((sp.rule + ":" + sp.cls, text[sp.start:end], spoken))
        logger.debug("textprep %s %r -> %r", sp.rule, text[sp.start:end], spoken)
        pos = end
    out.append(text[pos:])
    result = "".join(out)

    # Lexicon / English-exception layer
    result = apply_english_exceptions(result, engine=engine, report=report)

    return re.sub(r"[ \t]+", " ", result).strip()
