"""dallal_parser: extract delivery details from Iraqi Instagram DM orders.

>>> from dallal_parser import parse_order
>>> r = parse_order("احمد علي\\nبغداد الكرادة قرب جامع الرحمن\\n0770 123 4567")
>>> r["name"], r["phone"], r["governorate"], r["address"]
('احمد علي', '+9647701234567', 'Baghdad', 'الكرادة قرب جامع الرحمن')
"""

from .gazetteer import GOVERNORATES
from .parser import REQUIRED_FIELDS, parse_order
from .phone import extract_phones, normalize_phone

__all__ = ["parse_order", "normalize_phone", "extract_phones", "GOVERNORATES", "REQUIRED_FIELDS"]
__version__ = "1.0.0"
