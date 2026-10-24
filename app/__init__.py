from flask import Flask
from flask_socketio import SocketIO
from flask_cors import CORS

socketio = SocketIO()

def create_app():
    # เมื่อไม่ระบุอะไรเลย Flask จะหาโฟลเดอร์ templates ในโฟลเดอร์ app/ โดยอัตโนมัติ
    app = Flask(__name__) 
    CORS(app)
    
    from .route import api_bp
    app.register_blueprint(api_bp) 
    
    socketio.init_app(app, cors_allowed_origins="*")
    
    return app