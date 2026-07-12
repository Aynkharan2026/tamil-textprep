# tamil-textprep

Shared **Eezham-Tamil text-preparation layer** for every VoxTN Tamil voice
surface: Aravam Voice, ThaiVeedu archive audio, VoxVoIP Tamil voice agents.

```
sanitize → classify (tags → heuristics) → verbalize → Eezham lexicon → emit
```

Output is **fully-verbalized Tamil — no digits reach any TTS engine.**
Why: the 2026-07-12 engine matrix showed Sarvam v3 reads years digit-by-digit
("இரண்டு பூச்சியம் இரண்டு நான்கு"), Sarvam v2 code-switches to English
("ட்வென்டி ட்வென்டி ஃபோர்", phone numbers as English *hundreds*) and reads
`11/07/2026` as **November 7 where v3 says July 11** — and Sarvam TTS exposes
no working normalization control (unknown params are silently accepted).

## Usage

```python
from tamil_textprep import normalize

normalize("2024-ம் ஆண்டு அவருக்கு 65 வயது.")
# → "இரண்டாயிரத்து இருபத்து நான்காம் ஆண்டு அவருக்கு அறுபத்தைந்து வயது."

# The CONTRACT for machine-generated text (voice agents): explicit tags.
normalize("{{phone:4165487496}} ஐ அழையுங்கள், {{time:14:30}} மணிக்கு.")
```

CLI: `tamil-textprep "text" --report` · HTTP: `uvicorn tamil_textprep.api:app`
(the `/normalize` JSON contract is the stable surface a future `voxtn-mcp`
tool wraps).

## The three tiers of number-context (honest by design)

1. **Explicit tags** `{{phone:…}} {{year:…}} {{date:YYYY-MM-DD}} {{money:50 CAD}}
   {{pct:…}} {{ord:…}} {{count:…}} {{digits:…}} {{time:HH:MM}} {{num:…|convention=…}}`
   — zero ambiguity; REQUIRED for voice-agent/app-generated text.
2. **Deterministic heuristics** for free text — ordered rules `H1…H13`, every
   match logged with its rule id (`normalize(report=[])`). Known failure modes
   are documented in `classify.py` and are deliberate: bare 4-digit
   year-without-context reads as cardinal; slash dates use the **house rule
   DD/MM/YYYY** (US-formatted sources will misread — tag them); street
   addresses read as cardinals; Tamil-script numerals (௧௨௩) unsupported in v1.
3. **LLM fallback hook** (`llm_fallback=`) for flagged ambiguities only.
   Never default; never for archive audio.

## Eezham rules (corpus-evidenced, ThaiVeedu 1,030-article corpus)

| Rule | Evidence |
|---|---|
| டொலர் never டாலர் | 178:11 |
| புள்ளி never பாயிண்ட் (decimals) | 251:0 |
| பூச்சியம் never பூஜ்ஜியம் (zero) | 44:0 |
| % → வீதம்; dates → …ஆம் திகதி | house style |
| **Large numbers: DUAL convention** — மில்லியன்/பில்லியன் in Canadian/CAD contexts, இலட்சம்/கோடி in homeland/LKR contexts | மில்லியன்-family 278 vs லட்சம்/கோடி ≈390 hits — both are house forms. Implemented per-call (`convention=`), currency spans auto-pick (LKR→lakh). Default `million`. **Awaiting Kumar Annai's ratification.** |

## English-in-Tamil exception table

`tamil_textprep/data/english_exceptions.json` — **data, not code; owned by
Karan / Kumar Annai.** Per-entry policy `speak-as-english | transliterate |
spell-out`, with per-engine overrides (bulbul:v2 garbles Latin — it said
"Voxel" for VoxTN and "போக்ஸ்" for PBX in testing, so v2 gets everything
transliterated).

## Core numeral engine

[`open-tamil`](https://pypi.org/project/open-tamil/) `tamil.numeral` — chosen
after property-testing 4,017 cases: forward generation is robust (zero
digit-leaks/exceptions), proper sandhi (அறுபத்தைந்து, தொன்னூற்றாறு), SL-literary
இலட்சம், and it ships both lakh- and million-based groupings. Wrapper fixes
(see `numwords.py`): பூஜ்ஜியம்→பூச்சியம், நூற்றி→நூற்று, whitespace, year-form
fusion (இரண்டு ஆயிரத்து→இரண்டாயிரத்து). `tamilstr2num` (reverse) fails on ~41%
of forward output — never used as a validator.

## Guarantees

- No ASCII digit survives `normalize()` (tested).
- Idempotent: `normalize(normalize(x)) == normalize(x)` (tested).
- User prose is never rewritten — only classified numeral/exception spans.
  Dialect drift in prose belongs to the dialect guard (flag-for-review),
  not here.
