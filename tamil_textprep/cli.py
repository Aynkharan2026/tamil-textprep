"""CLI: echo normalized text; --report prints audit rows to stderr.

Usage:  tamil-textprep "2024-ம் ஆண்டு ..." [--engine sarvam_v2] [--convention lakh] [--report]
        echo "..." | tamil-textprep -
"""
from __future__ import annotations

import argparse
import sys

from . import normalize


def main() -> None:
    p = argparse.ArgumentParser(prog="tamil-textprep")
    p.add_argument("text", help="text to normalize, or '-' for stdin")
    p.add_argument("--engine", default=None)
    p.add_argument("--convention", default="million", choices=["million", "lakh"])
    p.add_argument("--report", action="store_true")
    a = p.parse_args()
    text = sys.stdin.read() if a.text == "-" else a.text
    rows: list = []
    out = normalize(text, convention=a.convention, engine=a.engine,
                    report=rows if a.report else None)
    print(out)
    if a.report:
        for rule, orig, spoken in rows:
            print(f"  [{rule}] {orig!r} -> {spoken!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
