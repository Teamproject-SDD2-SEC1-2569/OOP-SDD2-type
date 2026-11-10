"""
Compatibility shim for legacy imports: from app.teacher_routes import ...
ย้ายไปยัง app.routes.teacher_routes แล้ว
"""
from .routes.teacher_routes import (
    teacher_bp,
    room_settings,
    active_rooms,
    generate_room_code,
    get_current_teacher,
    get_room_settings,
    create_room,
    list_rooms,
    update_room_status,
    validate_room
)

__all__ = [
    "teacher_bp",
    "room_settings",
    "active_rooms",
    "generate_room_code",
    "get_current_teacher",
    "get_room_settings",
    "create_room",
    "list_rooms",
    "update_room_status",
    "validate_room"
]