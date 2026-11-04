import os
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import JWTManager

socketio = SocketIO()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    
    # 1. ตั้งค่า Secret Key สำหรับ Session และ JWT
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'typeclass-super-secret-key')
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'typeclass-jwt-secret-key')

    # 2. เปิดใช้งาน Extensions
    CORS(app)
    jwt.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")

    # 3. ลงทะเบียน Route ฝั่งนักเรียน (ถอด url_prefix='/api' ออก เพื่อให้เข้าหน้าแรก / ได้ตามปกติ)
    from .route import api_bp, register_socket_events
    app.register_blueprint(api_bp)
    register_socket_events(socketio)

    # 4. ลงทะเบียน Route ฝั่งอาจารย์ และระบบ Auth
    try:
        from .auth_routes import auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
    except (ImportError, AttributeError):
        pass

    try:
        from .teacher_routes import teacher_bp
        app.register_blueprint(teacher_bp, url_prefix='/teacher')
    except (ImportError, AttributeError):
        pass

    return app