#!/usr/bin/env python3
"""Layer-1 Eezham corpus audit — the regression gate.

Runs every article of a corpus (jsonl with a 'body' field) through
tamil_textprep.normalize() and demands that EVERY word-level change be
CLAIMED by a rule: a classifier/verbalizer rule ID, an exceptions-table
LEX entry, or the deterministic sanitize whitelist.

**An unclaimed change to a Tamil word is a bug, full stop.**
(This is the check that would have caught பாடசாலைக்கு → "பாடசா, likeகு"
in seconds.)

Usage:
    corpus_audit.py CORPUS.jsonl [--out FINDINGS.json] [--max-show N]

Exit code 0 = no unclaimed diffs (gate passes); 1 = unclaimed diffs found.
Wire into CI/cron: any change to tamil-textprep or english_exceptions.json
re-runs this over the full corpus before merge.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import unicodedata

from tamil_textprep import normalize

# Deterministic sanitize-layer effects (claimable without a rule row):
# smart quotes/dashes → ASCII, zero-width removal, whitespace collapse.
_SANITIZE_MAP = {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "−": "-"}


def _sanitize_equiv(a: str, b: str) -> bool:
    """True if a→b is explainable by the sanitize layer alone."""
    a2 = unicodedata.normalize("NFC", a)
    for k, v in _SANITIZE_MAP.items():
        a2 = a2.replace(k, v)
    a2 = re.sub(r"[​‌‍⁠﻿]", "", a2)
    return re.sub(r"\s+", " ", a2).strip() == re.sub(r"\s+", " ", b).strip()


def audit_text(body: str, convention: str = "million"):
    rows: list = []
    out = normalize(body, convention=convention, report=rows)

    claimed_orig = [r[1] for r in rows]
    claimed_spoken = [r[2] for r in rows]

    src_w = body.split()
    out_w = out.split()
    sm = difflib.SequenceMatcher(None, src_w, out_w, autojunk=False)
    unclaimed = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        a = " ".join(src_w[i1:i2])
        b = " ".join(out_w[j1:j2])
        if _sanitize_equiv(a, b):
            continue
        # claimed if some rule row's original appears in the source side and
        # its spoken form appears in the output side of this hunk
        def _norm(x: str) -> str:
            # rows record post-sanitize text; hunks come from raw source —
            # normalize dashes/quotes/space on both sides before matching
            for k, vv in _SANITIZE_MAP.items():
                x = x.replace(k, vv)
            return re.sub(r"\s", "", x)

        na, nb = _norm(a), _norm(b)
        hit = any(
            o and s and _norm(o) in na and _norm(s)[:20] in nb
            for o, s in zip(claimed_orig, claimed_spoken)
        )
        if not hit:
            unclaimed.append({"src": a[:120], "out": b[:120]})
    return out, rows, unclaimed


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("corpus")
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-show", type=int, default=25)
    ap.add_argument("--allowlist", default=None,
                    help="reviewed-findings JSON; matching findings don't fail the gate")
    args = ap.parse_args()
    allow = []
    if args.allowlist:
        allow = json.load(open(args.allowlist, encoding="utf-8"))["entries"]

    n_articles = n_changed = n_rows = 0
    all_unclaimed: list = []
    rule_counts: dict[str, int] = {}
    for line in open(args.corpus, encoding="utf-8"):
        rec = json.loads(line)
        n_articles += 1
        out, rows, unclaimed = audit_text(rec["body"])
        n_rows += len(rows)
        if rows or unclaimed:
            n_changed += 1
        for r in rows:
            rule_counts[r[0].split(":")[0]] = rule_counts.get(r[0].split(":")[0], 0) + 1
        for u in unclaimed:
            u["article"] = rec.get("id", n_articles)
            all_unclaimed.append(u)

    blocking = [u for u in all_unclaimed
                if not any(e["article"] == str(u["article"]) and
                           u["src"].startswith(e["src_prefix"]) for e in allow)]
    print(f"articles={n_articles} touched={n_changed} claimed_changes={n_rows} "
          f"UNCLAIMED={len(all_unclaimed)} (allowlisted={len(all_unclaimed)-len(blocking)}, "
          f"BLOCKING={len(blocking)})")
    print("claims by rule:", json.dumps(rule_counts, sort_keys=True))
    for u in all_unclaimed[: args.max_show]:
        print(f"  UNCLAIMED [{u['article']}] {u['src']!r} -> {u['out']!r}")
    if args.out:
        json.dump({"articles": n_articles, "claimed": n_rows,
                   "rule_counts": rule_counts, "unclaimed": all_unclaimed},
                  open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sys.exit(1 if blocking else 0)


if __name__ == "__main__":
    main()
