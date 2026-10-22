"""dallal_parser — order details from Iraqi Instagram DMs (cash on delivery).

    >>> from dallal_parser import parse_order
    >>> parse_order("علي حسين\\nبغداد الكرادة قرب جامع براثا\\n07801234567")["phone"]
    '+9647801234567'
"""

from .gazetteer import GOVERNORATES
from .governorate import resolve_governorate
from .normalize import clean_text
from .parser import parse_order
from .phones import normalize_phone
from .schema import INVALID_PHONE_REASONS, SCHEMA_KEYS, WARNING_CODES

__all__ = [
    "parse_order",
    "normalize_phone",
    "resolve_governorate",
    "clean_text",
    "GOVERNORATES",
    "SCHEMA_KEYS",
    "WARNING_CODES",
    "INVALID_PHONE_REASONS",
]
__version__ = "1.0.0"
