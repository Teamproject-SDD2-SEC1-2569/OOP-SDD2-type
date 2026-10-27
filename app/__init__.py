from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS
from flask_jwt_extended import JWTManager

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    
    # ตั้งค่า Secret Key (ใน production ควรดึงจากไฟล์ .env)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'typeclass-super-secret-key')

    # เปิดใช้งาน CORS เพื่อให้ Frontend เรียก API ได้โดยไม่ติดบล็อก
    CORS(app)
    
    # ผูก SocketIO เข้ากับ Flask app
    socketio.init_app(app)

    # นำเข้าและลงทะเบียน Route ปกติ และ WebSocket Events
    from .route import api_bp, register_socket_events
    app.register_blueprint(api_bp, url_prefix='/api')
    register_socket_events(socketio)

    return app