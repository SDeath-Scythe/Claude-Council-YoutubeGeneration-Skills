"""Closed template table for the follow-up message to the customer (D9).

Invariant: followup_ar is None  <=>  needs_review is False.
"""
from .gazetteer import GOVERNORATES

OPENER = "هلا بيك 🌹"
CLOSER = "وشكراً"

TEMPLATES = {
    "phone_missing": "ممكن رقم موبايلك؟",
    "phone_invalid": "الرقم ناقص أو غلط، ممكن ترسله مرة ثانية (11 رقم يبدي بـ 07)؟",
    "phone_foreign": "نحتاج رقم عراقي يبدي بـ 07 حتى المندوب يتصل بيك",
    "governorate_missing": "بيا محافظة حضرتك؟",
    "governorate_choice": "نوصل الطلب لـ {a} لو {b}؟",
    "address_missing": "ممكن العنوان بالتفصيل: المنطقة وأقرب نقطة دالة؟",
    "name_missing": "ممكن الاسم الكامل؟",
}

BLOCKING = {"phone_invalid_length", "phone_invalid_prefix", "phone_invalid_chars", "phone_foreign",
            "phone_ambiguous_prefix", "phone_ambiguous_join", "multiple_governorates",
            "governorate_conflict", "internal_error"}
NON_BLOCKING = {"governorate_inferred_from_city", "phone_trunk_zero_removed",
                "extra_phones", "input_truncated", "landline_ignored", "phone_corrected"}
PHONE_BAD = {"phone_invalid_length", "phone_invalid_prefix", "phone_invalid_chars",
             "phone_ambiguous_prefix", "phone_ambiguous_join"}

# warning -> (meaning, blocking?, template key) -- used by the README table
WARNING_DOCS = {
    "phone_invalid_length": ("a phone-like digit run (>= 9 digits) is not 10/11/12-13 digits of a valid form", True, "phone_invalid"),
    "phone_invalid_prefix": ("an 11-digit number starting 070/071/072 (not a mobile prefix)", True, "phone_invalid"),
    "phone_foreign": ("a +/00 number with a country code other than 964", True, "phone_foreign"),
    "phone_ambiguous_prefix": ("a bare 10-digit number could be formed only by dropping a leading digit group; phone left empty", True, "phone_invalid"),
    "phone_ambiguous_join": ("a valid number was formed only by joining a long digit group with a 1-2 digit group (e.g. '0770123456 4'); phone left empty", True, "phone_invalid"),
    "phone_invalid_chars": ("a phone attempt contains letter look-alikes (O for 0, l for 1); not repaired", True, "phone_invalid"),
    "multiple_governorates": ("two governorates (or capitals) named and no single delivery cue", True, "governorate_choice"),
    "governorate_conflict": ("a governorate and a city/district of another governorate", True, "governorate_choice"),
    "internal_error": ("unexpected exception; empty record returned", True, None),
    "governorate_inferred_from_city": ("governorate deduced from a city/district name", False, None),
    "phone_trunk_zero_removed": ("+964 0 7XX... written; redundant 0 removed", False, None),
    "extra_phones": ("more than two distinct valid mobiles; only two kept", False, None),
    "input_truncated": ("input longer than 20,000 characters was truncated", False, None),
    "phone_corrected": ("the customer corrected the number (غلط/الصحيح/اقصد/sorry wrong); the retracted number was discarded", False, None),
    "landline_ignored": ("an Iraqi landline (01-06 area code) was written; only mobiles are used", False, None),
}


def _ar(gov):
    d = GOVERNORATES.get(gov)
    return d["ar"] if d else str(gov)


def build_followup(record, conflict_govs=None):
    """Return the Arabic follow-up text, or None when no review is needed."""
    if not record.get("needs_review"):
        return None
    w = set(record.get("warnings") or [])
    parts = []
    if record.get("phone") is None:
        if "phone_foreign" in w:
            parts.append(TEMPLATES["phone_foreign"])
        elif w & PHONE_BAD:
            parts.append(TEMPLATES["phone_invalid"])
        else:
            parts.append(TEMPLATES["phone_missing"])
    elif w & (PHONE_BAD | {"phone_foreign"}):
        parts.append(TEMPLATES["phone_invalid"])
    if w & {"multiple_governorates", "governorate_conflict"} and conflict_govs and len(conflict_govs) >= 2:
        parts.append(TEMPLATES["governorate_choice"].format(a=_ar(conflict_govs[0]), b=_ar(conflict_govs[1])))
    elif record.get("governorate") is None:
        parts.append(TEMPLATES["governorate_missing"])
    if record.get("address") is None:
        parts.append(TEMPLATES["address_missing"])
    if record.get("name") is None:
        parts.append(TEMPLATES["name_missing"])
    if not parts:  # e.g. internal_error with fields present: ask to resend
        parts.append(TEMPLATES["address_missing"])
    return "\n".join([OPENER] + parts + [CLOSER])
