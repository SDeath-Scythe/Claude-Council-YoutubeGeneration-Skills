"""Order-details parser for Dallal (Instagram DM sales assistant, Iraq, COD).

    >>> from dallal_parser import parse_order
    >>> order = parse_order("علي حسين\\n07701234567\\nبغداد الكرادة قرب جامع براثا")
    >>> order["phone"], order["governorate"]
    ('+9647701234567', 'Baghdad')
"""

from .gazetteer import GOVERNORATES
from .parser import parse_order
from .phones import normalize_iraqi_mobile

__all__ = ["parse_order", "normalize_iraqi_mobile", "GOVERNORATES"]
__version__ = "1.0.0"
