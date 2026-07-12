#!/usr/bin/env python3
"""Register split: ELUTHU (literary narration) vs PECHU (quoted speech).

Tamil prose keeps narration in the literary register and quoted speech in
the spoken register — so a magazine corpus already contains BOTH, and the
pechu is inside the quotation marks.

HONESTY NOTE (do not trust blindly): quote detection is a FIRST-PASS
HEURISTIC. Quotes also wrap emphasis, book/film titles (‘கலசம்’ எனும்
பத்திரிகை), and borrowed terms — so the PECHU sub-corpus is
"quoted spans", of which true spoken-register speech is a subset.
The Jaffna-marker density check below measures exactly how impure it is;
human review decides before any register-conditional rule fires.

Usage: register_split.py CORPUS.jsonl [--out-prefix PATH]
Writes PATH_pechu.jsonl / PATH_eluthu.jsonl and prints sizes + marker stats.
"""
from __future__ import annotations

import argparse
import json
import re

# Quote pairs seen in the ThaiVeedu corpus (raw, pre-sanitize).
_QUOTE_SPAN = re.compile(
    r"‘([^’‘]{2,600})’|“([^”“]{2,600})”|\"([^\"]{2,600})\"|'([^'']{2,600})'"
)

# Spoken-Jaffna markers: should concentrate in PECHU if the heuristic works.
PECHU_MARKERS = ["எண்டு", "எண்டால்", "எங்கட", "உப்பிடி", "இண்டைக்கு",
                 "சொல்லுங்கோ", "வாறன்", "கதைப்பம்", "நிக்கிறியள்", "கண்டியோ",
                 "எண்ட", "அப்பு", "ஆச்சி", "கிடக்கு", "போட்டு", "எக்கச்சக்க"]


def split_text(body: str) -> tuple[list[str], str]:
    pechu: list[str] = []

    def grab(m: re.Match) -> str:
        span = next(g for g in m.groups() if g)
        pechu.append(span)
        return " "

    eluthu = _QUOTE_SPAN.sub(grab, body)
    return pechu, eluthu


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--out-prefix", default=None)
    args = ap.parse_args()

    pechu_chars = eluthu_chars = 0
    n_spans = 0
    marker_hits = {"pechu": 0, "eluthu": 0}
    pechu_f = open(f"{args.out_prefix}_pechu.jsonl", "w", encoding="utf-8") if args.out_prefix else None
    eluthu_f = open(f"{args.out_prefix}_eluthu.jsonl", "w", encoding="utf-8") if args.out_prefix else None

    for line in open(args.corpus, encoding="utf-8"):
        rec = json.loads(line)
        spans, rest = split_text(rec["body"])
        n_spans += len(spans)
        p = " ".join(spans)
        pechu_chars += len(re.sub(r"\s", "", p))
        eluthu_chars += len(re.sub(r"\s", "", rest))
        for mk in PECHU_MARKERS:
            marker_hits["pechu"] += p.count(mk)
            marker_hits["eluthu"] += rest.count(mk)
        if pechu_f and spans:
            pechu_f.write(json.dumps({"id": rec.get("id"), "spans": spans},
                                     ensure_ascii=False) + "\n")
        if eluthu_f:
            eluthu_f.write(json.dumps({"id": rec.get("id"), "body": rest},
                                      ensure_ascii=False) + "\n")

    tot = pechu_chars + eluthu_chars
    print(f"quoted spans: {n_spans}")
    print(f"PECHU  (quoted): {pechu_chars:,} chars ({100*pechu_chars/tot:.1f}%)")
    print(f"ELUTHU (rest)  : {eluthu_chars:,} chars ({100*eluthu_chars/tot:.1f}%)")
    pd = 1e6 * marker_hits["pechu"] / max(1, pechu_chars)
    ed = 1e6 * marker_hits["eluthu"] / max(1, eluthu_chars)
    print(f"Jaffna-marker density: pechu {pd:.0f}/M chars vs eluthu {ed:.0f}/M chars "
          f"(ratio {pd/max(ed,0.01):.1f}x — higher = heuristic separating registers; "
          f"markers in eluthu = leakage or unquoted speech, review)")


if __name__ == "__main__":
    main()
