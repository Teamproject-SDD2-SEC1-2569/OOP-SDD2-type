"""
Compatibility shim for legacy imports: from app.route import ...
ย้ายไปยัง app.routes.student_routes และ app.sockets แล้ว
"""
from .routes.student_routes import student_bp as api_bp
from .sockets import register_socket_events
from .utils.constants import GENERAL_WORDS, CODING_WORDS
from .models.typing_session import StandardTypingSession
from .database import get_db_connection
from .services.typing_service import typing_service

active_sessions = typing_service.active_sessions
room_leaderboards = typing_service.room_leaderboards

__all__ = [
    "api_bp",
    "register_socket_events",
    "GENERAL_WORDS",
    "CODING_WORDS",
    "active_sessions",
    "room_leaderboards",
    "StandardTypingSession",
    "get_db_connection"
]