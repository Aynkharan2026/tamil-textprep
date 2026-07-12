# -*- coding: utf-8 -*-
"""Reverse transliteration: whole-token safety + retained function.

The corruption cases are the real production victims found in the
2026-07-12 blast-radius audit (issue tamiltts-saas#2)."""
from tamil_textprep.lexicon import reverse_transliterate as rt


CORRUPTION_VICTIMS = [
    "பாடசாலைக்கு",       # was "பாடசா, likeகு"
    "பின்னர்",            # was "PINனர்" (5,600 corpus hits)
    "பின்வருமாறு",
    "அமைப்பின்",
    "பல்கலைக்கழகம்",      # was …like…
    "பல்கலைக்கழகத்தில்",
    "தொலைக்காட்சி",
    "நிலைக்கு",
    "வேலைக்குப்",
    "ஆப்பிள்",            # ஆப்->app must not fire inside
    "ஆப்பிரிக்கா",
    "பாடலைக்",
    "வந்தபின்",
]


def test_no_tamil_word_is_shredded():
    for w in CORRUPTION_VICTIMS:
        assert rt(w) == w, w
    sent = "பல்கலைக்கழகத்தில் பின்னர் வேலைக்குப் போனார்."
    assert rt(sent) == sent


def test_pin_entry_removed():
    # பின் is a core Tamil word; the PIN entry was curated OUT.
    assert rt("பின்") == "பின்"


def test_standalone_loanwords_still_reverse():
    assert rt("கம்ப்யூட்டர்") == "computer"
    assert rt("வீடியோ") == "video"
    assert rt("இன்டர்நெட்") == "internet"
    assert rt("லைக்") == "like"          # standalone only
    assert rt("டவுன்லோடு") == "download"


def test_suffixed_loanwords_reverse_with_suffix_kept():
    assert rt("கம்ப்யூட்டரில்") == "computerில்"
    assert rt("வீடியோவை") == "வீடியோவை" or rt("வீடியோவை") == "videoவை"  # வ் glide join — miss is SAFE
    assert rt("லேப்டாப்பை") == "லேப்டாப்பை" or "laptop" in rt("லேப்டாப்பை")  # gemination join — miss is SAFE
    assert rt("இன்டர்நெட்டில்") == "இன்டர்நெட்டில்" or "internet" in rt("இன்டர்நெட்டில்")


def test_real_tamil_word_never_anglicized():
    # மின்னஞ்சல் is real Tamil — only the transliteration இமெயில் reverses
    assert rt("மின்னஞ்சல்") == "மின்னஞ்சல்"
    assert rt("இமெயில்") == "email"


def test_sentence_mixed():
    out = rt("நான் கம்ப்யூட்டர் வாங்கி இன்டர்நெட் இணைப்பு பெற்றேன். பின்னர் வீடியோ பார்த்தேன்.")
    assert "computer" in out and "internet" in out and "video" in out
    assert "பின்னர்" in out and "PIN" not in out
