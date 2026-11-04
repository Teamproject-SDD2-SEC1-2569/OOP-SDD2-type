from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt


def require_role(required_role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()

            claims = get_jwt()
            user_role = claims.get("role")

            if user_role != required_role:
                return jsonify({
                    "error": "คุณไม่มีสิทธิ์เข้าถึงส่วนนี้"
                }), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator