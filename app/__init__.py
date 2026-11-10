import logging
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from .config import Config

socketio = SocketIO()
jwt = JWTManager()


def create_app():
    """
    Application Factory สำหรับสร้างและตั้งค่า Flask Application
    สอดคล้องกับหลัก Modular Architecture และ Separation of Concerns
    """
    app = Flask(__name__)

    # 1. โหลดการตั้งค่าระบบจาก Config Object
    app.config.from_object(Config)

    # 2. เปิดใช้งาน Extensions
    CORS(app)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*", async_mode="threading")

    # 3. ลงทะเบียน Route Blueprints (Presentation Layer)
    from .routes import auth_bp, teacher_bp, student_bp
    app.register_blueprint(student_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(teacher_bp, url_prefix='/teacher')

    # 4. ลงทะเบียน WebSocket Event Listeners (Real-time Layer)
    from .sockets import register_socket_events
    register_socket_events(socketio)

    logging.info("Typeclass Application Initialized Successfully")
    return app