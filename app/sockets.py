"""
Compatibility shim for legacy imports: from app.sockets import register_socket_events
ย้ายไปยัง app.sockets.events แล้ว
"""
from .sockets.events import register_socket_events

__all__ = ["register_socket_events"]
