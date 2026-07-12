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


def apply_english_exceptions(text: str, engine: str | None = None) -> str:
    table = _load("english_exceptions.json")["entries"]
    ekey = "v2" if engine in ("sarvam_v2", "bulbul:v2") else None
    for entry in table:
        policy = entry.get(ekey) if ekey and entry.get(ekey) else entry["policy"]
        if policy == "speak-as-english":
            continue
        target = entry["tamil"] if policy == "transliterate" else entry.get("spelled", entry["tamil"])
        text = re.sub(rf"(?<![A-Za-z]){re.escape(entry['term'])}(?![A-Za-z])",
                      target, text)
    return text
