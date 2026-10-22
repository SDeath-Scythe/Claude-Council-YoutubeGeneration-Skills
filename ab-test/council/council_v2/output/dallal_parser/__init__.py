"""Dallal order-details parser: turn an Instagram DM into a COD order record.

    >>> from dallal_parser import parse_order
    >>> parse_order("علي حسين 07701234567 بغداد الكرادة قرب جامع الرحمن")["governorate"]
    'Baghdad'
"""
from .core import parse_order  # noqa: F401
from .gazetteer import CANONICAL as GOVERNORATES  # noqa: F401

__all__ = ["parse_order", "GOVERNORATES"]
__version__ = "1.0.0"
