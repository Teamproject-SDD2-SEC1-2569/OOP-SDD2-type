"""
Compatibility shim for legacy imports: from app.auth_routes import ...
ย้ายไปยัง app.routes.auth_routes แล้ว
"""
from .routes.auth_routes import auth_bp, bcrypt, register, login

__all__ = ["auth_bp", "bcrypt", "register", "login"]