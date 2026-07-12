# tamil-textprep

**Eelam (also written Eezham) Tamil — Sri Lankan Tamil — text preparation for speech and language systems.**

Turns raw text into fully-verbalized Tamil that a TTS engine can speak correctly — with Eezham forms preserved, not normalized away.

---

## Why this exists

Every major AI model is trained on **Indian Tamil**. Eelam Tamil — the Tamil of Sri Lanka and its diaspora (தமிழீழம், Tamil Eelam) — is a different variant. And the models do not merely fail to recognize it.

**They silently normalize it into Indian Tamil.**

These are not errors. They are *corrections*. The model believes it is helping. That is what makes them dangerous: they pass every automated check, and only a Tamil reader notices.

Measured, reproducibly, across four independent capabilities:

| Source (Eezham) | What the model produced | Where |
|---|---|---|
| `வைக்கப்பெற்றன` | `வைக்கப்பட்டன` | OCR |
| `எம்கண்ணில்` | `எங்கண்ணில்` | OCR |
| `எமது` | `நமது` | generation |
| `எம்மை` | `நம்மை` | speech-to-text |
| `கதைப்பம்` | `கதைப்போம்` | TTS round-trip |
| `அம்மாட்டைச் சொல்லுங்கோ…` | *dropped entirely* | translation |

And speech systems get the basics wrong. A Tamil TTS engine handed `2024` will happily say **"இரண்டு பூச்சியம் இரண்டு நான்கு"** — reciting four digits, not speaking a year. Another will code-switch to English mid-sentence. Neither is Tamil.

This library is the floor beneath all of that.

---

## What it does

```
sanitize → classify → verbalize → Eezham lexicon → emit
```

- **Numerals, context-aware.** `2024` → `இரண்டாயிரத்து இருபத்து நான்காம் ஆண்டு` (year), not four digits. `65` → `அறுபத்தைந்து வயது` (age) vs `அறுபத்தைந்து` (count) vs a digit-string (phone). Dates, currency, ordinals, percentages, decimals, ranges.
- **Eelam-correct forms.** `டொலர்`, not `டாலர்`. Proper sandhi. Verified against a real Eezham corpus, not assumed.
- **The dual convention, handled properly.** Diaspora Tamil uses *both*: **மில்லியன்** in Canadian/Western contexts, **லட்சம்/கோடி** for homeland contexts. This is not an ambiguity to resolve — it is a context rule, and both are correct.
- **English-in-Tamil, governed.** Brand names, proper nouns, acronyms — handled by an editable table, not by guesswork.
- **Every transformation is attributable.** Each change carries the rule ID that produced it. Nothing changes silently.

## The tag contract (recommended)

Machine-generated text *knows* what its numbers mean. Say so:

```
{{phone:416-548-7496}}  {{year:2024}}  {{date:11/07/2026}}  {{age:65}}
```

Explicit tags are the primary path. For free text, 13 ordered heuristics apply — each logging which rule fired, with the ambiguous cases (bare 4-digit year-vs-count, DD/MM vs MM/DD) documented as known failure modes rather than hidden.

## Install

```bash
pip install git+https://github.com/Aynkharan2026/tamil-textprep@v0.2.0
```

```python
from tamil_textprep import normalize
normalize("2024-ம் ஆண்டு")   # → இரண்டாயிரத்து இருபத்து நான்காம் ஆண்டு
```

A CLI and a FastAPI `/normalize` endpoint are included.

---

## Why word boundaries matter (a real bug, kept as a test)

An earlier reverse-transliteration pass substring-matched *inside* Tamil words. The entry `லைக் → like` turned:

- **பல்கலைக்கழகம்** (university) → `பல்க likeகழகம்`
- **தொலைக்காட்சி** (television) → mangled the same way

**8,690 corruptions per 1.578 million words** — one every 181 words. The word `பின்` was mapped to `PIN`.

All 13 real victim words are now permanent regression tests. Reverse transliteration operates on **whole tokens only**, against an explicit list, and a `reverse_tamil` field protects genuine Tamil words (`மின்னஞ்சல்`) from ever being Anglicized.

*A rule written by someone who does not speak the language will find a way to break it.*

---

## Scope — what this corpus does and does not cover

The evidence base is *ThaiVeedu*, a **Jaffna-weighted diaspora corpus**. Eelam Tamil is not monolithic: Jaffna and Batticaloa (Mattakkalappu) differ, and Malaiyaha (up-country) Tamil descends from Indian Tamil entirely — a different lineage. This library is **derived from a Jaffna-weighted diaspora corpus; contributions from other Eelam regions are welcome and needed.** We do not claim to speak for regions we have no corpus for.

## Evidence

Usage rulings are settled by **counting the corpus, not asking a model.** Drawn from *ThaiVeedu* (தாய்வீடு), a Tamil diaspora magazine — 1,030 structured articles:

```
டொலர்   178 : 11   (vs டாலர்)
புள்ளி   251 : 0
பூச்சியம்  44 : 0
```

Where the corpus is silent, the question is flagged for a human editor — never guessed.

---

## Contributing

**If you speak Eelam Tamil — any region — and something here sounds wrong, you are the authority. Please open an issue.**

Especially wanted:
- Words the library gets wrong
- Normalizations you have seen an AI make to *your* Tamil
- Regional and generational variation we have not captured

`english_exceptions.json` is a governed, human-editable table — deliberately data, not code, so that editors rather than engineers own it.

---

## Who

Built by **[VoxTN](https://voxtn.com)** — sovereign Tamil-first AI and telephony infrastructure.

> *AI is not a luxury item. Built by one of you, for all of you.*

Eelam Tamil survived a war. It should not be quietly edited out of existence by a text pipeline.

## License

MIT. Use it, fork it, ship it. The point is that the correct forms win.
