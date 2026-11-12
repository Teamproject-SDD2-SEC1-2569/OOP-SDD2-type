import os
from app import create_app, socketio

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"🚀 Starting Typeclass Backend Server on http://127.0.0.1:{port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=True, allow_unsafe_werkzeug=True)
