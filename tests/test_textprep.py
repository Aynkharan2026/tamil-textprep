# -*- coding: utf-8 -*-
"""Golden tests: every numeral class, tags, suffix consumption, lexicon."""
import re

import pytest

from tamil_textprep import normalize, numwords as nw


def test_no_digits_survive_pipeline():
    src = ("2024-ம் ஆண்டு அவர் கனடா வந்தார். அவருக்கு 65 வயது. "
           "என் இலக்கம் 416-548-7496. விலை $50. 11/07/2026 அன்று. "
           "அவர் 3வது இடம். விலை 25% உயர்ந்தது. வெப்பநிலை 9.8 பாகை. "
           "1,50,000 மக்கள். 2026–2028 காலப்பகுதி. நேரம் 14:30.")
    out = normalize(src)
    assert not re.search(r"[0-9]", out), out


def test_year_ordinal_suffix_consumed():
    out = normalize("2024-ம் ஆண்டு வந்தார்.")
    assert "இரண்டாயிரத்து இருபத்து நான்காம் ஆண்டு" in out
    assert "-ம்" not in out and "நான்காம்ம்" not in out


def test_year_locative():
    out = normalize("2040-ல் அதிகரிக்கும்.")
    assert "இரண்டாயிரத்து நாற்பதில்" in out


def test_age_vs_count_vs_phone():
    assert "அறுபத்தைந்து வயது" in normalize("அவருக்கு 65 வயது.")
    assert "அறுபத்தைந்து பேர்" in normalize("65 பேர் வந்தனர்.")
    phone = normalize("இலக்கம் 416-548-7496 ஆகும்.")
    assert "நான்கு ஒன்று ஆறு ஐந்து நான்கு எட்டு ஏழு நான்கு ஒன்பது ஆறு" in phone


def test_ordinal_suffix_consumed():
    out = normalize("அவர் 3வது இடம் பெற்றார்.")
    assert "மூன்றாவது இடம்" in out
    assert "மூன்றாவதுவது" not in out


def test_percent_no_duplicate_veetham():
    assert normalize("விலை 25% உயர்ந்தது.").count("வீதம்") == 1
    # source already says வீதம் — must not double it
    out = normalize("இது 25 வீதமாக அதிகரிக்கும்.")
    assert out.count("வீத") == 1 and "இருபத்தைந்து" in out
    # pathological redundant source "25% வீதம்" — keep the writer's word only
    out2 = normalize("விலை 25% வீதம் உயர்ந்தது.")
    assert out2.count("வீத") == 1


def test_decimal_pulli():
    out = normalize("வெப்பநிலை 9.8 பாகை.")
    assert "ஒன்பது புள்ளி எட்டு" in out
    assert "பாயிண்ட்" not in out


def test_lakh_comma_number():
    out = normalize("1,50,000 மக்கள் வாழ்கின்றனர்.", convention="lakh")
    assert "ஒரு இலட்சத்து ஐம்பது ஆயிரம்" in out


def test_million_convention():
    out = normalize("{{num:1500000|convention=million}} டொலர் ஒதுக்கீடு")
    assert "மில்லியன்" in out


def test_currency_symbol_and_unit_word():
    out = normalize("விலை $50 மட்டுமே.")
    assert "ஐம்பது டொலர்" in out and "டாலர்" not in out
    out2 = normalize("விலை 50 டொலர் மட்டுமே.")
    assert out2.count("டொலர்") == 1 and "ஐம்பது" in out2


def test_money_unit_word_keeps_space():
    out = normalize("1,50,000 டொலர் பெறுமதியான வீடு")
    assert "ஆயிரம் டொலர்" in out and "ஆயிரம்டொலர்" not in out


def test_date_house_rule_ddmm():
    out = normalize("11/07/2026 அன்று நடைபெறும்.")
    assert "ஜூலை" in out and "பதினொன்றாம் திகதி" in out
    assert "நவம்பர்" not in out  # the v2 MM/DD hazard, closed


def test_iso_date_tag():
    out = normalize("{{date:2026-07-11}} அன்று")
    assert "ஜூலை பதினொன்றாம் திகதி இரண்டாயிரத்து இருபத்தாறு" in out


def test_time():
    out = normalize("நேரம் 14:30 மணிக்கு")
    assert "பிற்பகல் இரண்டு மணி முப்பது" in out


def test_abbreviated_year_range():
    # Layer-1 corpus-audit finds: 1937–45 = 1937–1945; 1870–1 = 1870–1871
    out = normalize("(1937–45) காலப்பகுதி")
    assert "நாற்பத்தைந்து வரை" in out and "தொள்ளாயிரத்து முப்பத்தேழு" in out
    out2 = normalize("(1870–1) யுத்தம்")
    assert "எழுபத்தொன்று வரை" in out2  # NOT "ஒன்று வரை"


def test_score_chains_not_ranges():
    # asymmetric dash = tally/negative, not a range
    out = normalize("வாக்குகள் 10 -7 -3 பதிவாகின.")
    assert "முதல்" not in out


def test_corpus_evidenced_spellings():
    assert nw.cardinal(400) == "நானூறு"
    assert nw.cardinal(12) == "பன்னிரண்டு"
    assert nw.cardinal(95) == "தொண்ணூற்றைந்து"


def test_year_range():
    out = normalize("2026–2028 காலப்பகுதியில்")
    assert "இரண்டாயிரத்து இருபத்தாறு முதல் இரண்டாயிரத்து இருபத்தெட்டு வரை" in out


def test_tags_beat_heuristics():
    out = normalize("{{digits:2024}} என்பதை அழுத்துங்கள்")
    assert "இரண்டு பூச்சியம் இரண்டு நான்கு" in out


def test_phone_tag():
    out = normalize("{{phone:4165487496}} ஐ அழையுங்கள்")
    words = out.split("ஐ அழையுங்கள்")[0]
    assert "நான்கு ஒன்று ஆறு" in words and "," in words  # grouped pauses


def test_zero_is_poochchiyam():
    assert nw.cardinal(0) == "பூச்சியம்"
    assert "பூஜ்ஜியம்" not in nw.digits("101")


def test_hundred_form_not_colloquial():
    assert "நூற்றி" not in nw.cardinal(101)


def test_english_exceptions_default_and_v2():
    src = "VoxTN நிறுவனம் Toronto நகரில் AI மற்றும் PBX சேவை"
    out = normalize(src)
    assert "வொக்ஸ் ரி என்" in out and "ரொறன்ரோ" in out
    assert "ஏ ஐ" in out and "பி பி எக்ஸ்" in out
    out_v2 = normalize(src, engine="sarvam_v2")
    assert "VoxTN" not in out_v2


def test_idempotent():
    src = "2024-ம் ஆண்டு அவருக்கு 65 வயது. விலை 25% உயர்ந்தது."
    once = normalize(src)
    assert normalize(once) == once


def test_report_audit_rows():
    rows = []
    normalize("அவருக்கு 65 வயது.", report=rows)
    assert rows and rows[0][0].startswith("H12_age")


def test_user_prose_untouched():
    src = "எமது பாடசாலை மிகவும் சிறந்தது. துவங்கிய வேலை."  # textprep must NOT touch dialect words
    assert normalize(src) == src
