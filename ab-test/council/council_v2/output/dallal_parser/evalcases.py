"""Shared case matcher (D11) used by tests/test_cases.py and eval_cases.py.

Case format: {"id": ..., "input": str, "expected": {field: value}}.
Comparison (charter): exact string match after stripping whitespace (internal
runs of whitespace are collapsed and NFKC applied, but case is significant).  A value starting
with "~" means "field must contain the rest"; null means the field must be None.
"""
import unicodedata

FIELDS = ("name", "phone", "governorate", "address", "alt_phone", "needs_review")


def _norm(v):
    return " ".join(unicodedata.normalize("NFKC", str(v)).split())


def match_field(actual, expected):
    if expected is None:
        return actual is None
    if isinstance(expected, bool):
        return actual is expected
    if actual is None:
        return False
    if isinstance(expected, str) and expected.startswith("~"):
        return _norm(expected[1:]) in _norm(actual)
    return _norm(actual) == _norm(expected)


def check_case(output, expected):
    """Return list of (field, expected, actual) mismatches."""
    bad = []
    for f, exp in (expected or {}).items():
        act = output.get(f)
        if not match_field(act, exp):
            bad.append((f, exp, act))
    return bad
