"""
Compatibility shim for legacy imports: from app.auth_utils import require_role
ย้ายไปยัง app.utils.auth_utils แล้ว
"""
from .utils.auth_utils import require_role

__all__ = ["require_role"]