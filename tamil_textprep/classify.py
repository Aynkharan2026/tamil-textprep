"""Number/token classification: explicit tags first, then logged heuristics.

Tier 1 — EXPLICIT TAGS (the contract for machine-generated text):
    {{phone:4165487496}} {{year:2024}} {{date:2026-07-11}} {{time:14:30}}
    {{money:50 CAD}} {{pct:25}} {{ord:3}} {{count:65}} {{digits:90210}}
    {{num:1500000|convention=million}} {{en:VoxTN}}
  Voice agents and app code KNOW what a number is — they must say so.
  Tags are unambiguous and bypass every heuristic.

Tier 2 — DETERMINISTIC HEURISTICS for free text. Every match carries a
  rule id and is returned in the report for audit logging.

  KNOWN FAILURE MODES (deliberate, documented):
  * Bare 4-digit 1900–2099 without year context is read as a CARDINAL —
    "2040 டொலர்" stays a quantity; "2040-ல்" is caught as a year. A bare
    "2040 வரை" style year with no suffix will misread as cardinal.
  * Slash dates use the HOUSE RULE DD/MM/YYYY. US-formatted sources
    (MM/DD) will be misread — the engines themselves disagree on this
    (Sarvam v2 says Nov 7 where v3 says Jul 11 for 11/07), which is why
    an explicit rule beats engine defaults. Use {{date:YYYY-MM-DD}} tags
    to be safe.
  * Street addresses ("123 Main St") are read as cardinals.
  * Tamil-script numerals (௧௨௩) are not handled in v1.

Tier 3 — optional LLM fallback hook for tokens heuristics mark ambiguous.
  NEVER in the default path; see normalize(llm_fallback=...).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Span:
    start: int
    end: int
    cls: str          # phone|year|year_ord|date|time|money|pct|decimal|range|comma_num|ordinal|age|count|digits|en
    value: str
    rule: str         # rule id for audit logging
    opts: dict = field(default_factory=dict)


TAG_RE = re.compile(r"\{\{(\w+):([^}|]+)(?:\|([^}]*))?\}\}")

# Order matters: earlier rules win overlapping spans.
_H_RULES: list[tuple[str, str, re.Pattern]] = [
    ("H1_phone", "phone", re.compile(
        r"(?<!\d)(?:\+?1[-. ])?\d{3}[-. ]\d{3}[-. ]\d{4}(?!\d)|(?<!\d)\d{10}(?!\d)")),
    ("H2_date_iso", "date", re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")),
    ("H3_date_slash", "date_dmy", re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)")),
    ("H4_time", "time", re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")),
    ("H5_money", "money", re.compile(
        r"[$£€]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?(?=\s?(?:டொலர்|டாலர்|ரூபா|ரூ\.))")),
    ("H6_pct", "pct", re.compile(r"(?<!\d)\d+(?:\.\d+)?\s?%|(?<!\d)\d+(?:\.\d+)?(?=\s?(?:வீதம|சதவீதம))")),
    ("H7_range", "range", re.compile(r"(?<!\d)(\d{1,4})\s?[–—-]\s?(\d{1,4})(?!\d)(?=\s|$|[.,)])")),
    ("H8_year_suffixed", "year_ord", re.compile(
        r"(?<!\d)((?:19|20)\d{2})(?=\s?(?:-ம்|-ஆம்|ஆம்|ம்)\s?ஆண்டு|(?:-இல்|-ல்|இல்)|\s?ஆண்டு)")),
    ("H9_decimal", "decimal", re.compile(r"(?<!\d)\d+\.\d+(?!\d)")),
    ("H10_comma_num", "comma_num", re.compile(r"(?<!\d)\d{1,3}(?:,\d{2,3})+(?!\d)")),
    ("H11_ordinal", "ordinal", re.compile(r"(?<!\d)(\d+)(?=\s?(?:வது|ஆவது|-வது|-ஆவது))")),
    ("H12_age", "age", re.compile(r"(?<!\d)(\d{1,3})(?=\s?வயது)")),
    ("H13_cardinal", "count", re.compile(r"(?<!\d)\d+(?!\d)")),
]


def parse_tags(text: str) -> tuple[str, list[Span]]:
    """Extract {{...}} tags; returns text with placeholders and tag spans."""
    spans: list[Span] = []
    out: list[str] = []
    pos = 0
    for m in TAG_RE.finditer(text):
        out.append(text[pos:m.start()])
        cls, value, optstr = m.group(1), m.group(2).strip(), m.group(3) or ""
        opts = dict(kv.split("=", 1) for kv in optstr.split(",") if "=" in kv)
        start = sum(len(s) for s in out)
        marker = f"\x00{len(spans)}\x00"
        out.append(marker)
        spans.append(Span(start, start + len(marker), cls, value, "TAG", opts))
        pos = m.end()
    out.append(text[pos:])
    return "".join(out), spans


def heuristic_spans(text: str) -> list[Span]:
    """Run ordered heuristics; earlier rules claim their span first."""
    taken: list[tuple[int, int]] = []
    spans: list[Span] = []

    def overlaps(a: int, b: int) -> bool:
        return any(not (b <= s or a >= e) for s, e in taken)

    for rule_id, cls, rx in _H_RULES:
        for m in rx.finditer(text):
            if overlaps(m.start(), m.end()):
                continue
            taken.append((m.start(), m.end()))
            spans.append(Span(m.start(), m.end(), cls, m.group(0), rule_id))
    return sorted(spans, key=lambda s: s.start)
