from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

socketio = SocketIO()

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # 1. นำเข้า register_socket_events เพิ่มเติม
    from .route import api_bp, register_socket_events  # 👈 แก้ไขบรรทัดนี้
    app.register_blueprint(api_bp)
    
    socketio.init_app(app, cors_allowed_origins="*")
    
    # 2. สั่งให้ Socket.IO เริ่มรับฟัง Event ต่างๆ (start_typing, submit_score)
    register_socket_events(socketio)  # 👈 เพิ่มบรรทัดนี้
    
    return app