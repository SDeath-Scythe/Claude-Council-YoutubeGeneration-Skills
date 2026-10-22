"""Output contract: keys, warning codes, invalid-phone reasons."""

SCHEMA_VERSION = "1"

SCHEMA_KEYS = (
    "schema_version",
    "name",
    "phone",
    "phones",
    "invalid_phones",
    "governorate",
    "governorate_source",
    "governorate_raw",
    "address",
    "landmark",
    "notes",
    "missing",
    "warnings",
    "confidence",
    "needs_followup",
)

CORE_FIELDS = ("name", "phone", "governorate", "address")

# Closed set: the bot can branch on these codes.
WARNING_CODES = (
    "empty_input",
    "input_truncated",
    "multiple_phones",
    "invalid_phone",
    "uncommon_prefix",
    "phone_adjacent_digits",
    "multiple_governorates",
    "governorate_inferred",
    "name_uncertain",
    "name_single_word",
    "name_unverified",
    "address_short",
)

INVALID_PHONE_REASONS = (
    "too_short",
    "too_long",
    "not_mobile",
    "foreign",
    "unknown_prefix",
    "ambiguous_grouping",
)

GOVERNORATE_SOURCES = ("label", "explicit", "city", "district", "reference")

CONFIDENCE_LEVELS = ("high", "medium", "low")


def empty_result():
    return {
        "schema_version": SCHEMA_VERSION,
        "name": None,
        "phone": None,
        "phones": [],
        "invalid_phones": [],
        "governorate": None,
        "governorate_source": None,
        "governorate_raw": None,
        "address": None,
        "landmark": None,
        "notes": [],
        "missing": list(CORE_FIELDS),
        "warnings": [],
        "confidence": {field: None for field in CORE_FIELDS},
        "needs_followup": True,
    }
