import os
from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# สร้าง instance ของ SocketIO รองรับการเชื่อมต่อจากทุก Origin ในช่วงพัฒนา
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    
    # ตั้งค่า Secret Key (ใน production ควรดึงจากไฟล์ .env)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'typeclass-super-secret-key')
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")

    jwt = JWTManager(app)

    # เปิดใช้งาน CORS เพื่อให้ Frontend เรียก API ได้โดยไม่ติดบล็อก
    CORS(app)
    
    # ผูก SocketIO เข้ากับ Flask app
    socketio.init_app(app)

    # นำเข้าและลงทะเบียน Route ปกติ และ WebSocket Events
    from .route import api_bp, register_socket_events 
    from .teacher_routes import teacher_bp
    from .auth_routes import auth_bp

    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(
            teacher_bp,
            url_prefix='/api/teacher'
    )

    register_socket_events(socketio)

    return app