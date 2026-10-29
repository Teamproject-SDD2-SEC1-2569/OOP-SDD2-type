import eventlet
eventlet.monkey_patch()
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    print("🚀 Starting Typeclass Backend Server...")
    # รันผ่าน socketio.run แทน app.run แบบปกติ เพื่อให้ระบบ WebSocket ทำงานได้
    socketio.run(app, host='127.0.0.1', port=5000, debug=True)