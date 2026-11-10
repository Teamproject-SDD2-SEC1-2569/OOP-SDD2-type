"""
Compatibility shim for legacy imports: from app.constants import ...
ย้ายไปยัง app.utils.constants แล้ว
"""
from .utils.constants import GENERAL_WORDS, CODING_WORDS, MAX_WPM_THRESHOLD

__all__ = ["GENERAL_WORDS", "CODING_WORDS", "MAX_WPM_THRESHOLD"]
