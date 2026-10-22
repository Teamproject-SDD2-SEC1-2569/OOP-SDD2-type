import socketio
import time

sio = socketio.Client()

@sio.event
def connect():
    print("🟢 [Client] Connected successfully!")
    # จำลองการเข้าห้องเรียน
    sio.emit('join_classroom', {'room_code': 'ROOM101'})
    time.sleep(0.5)
    print("👉 Starting typing...")
    sio.emit('start_typing')

@sio.on('server_message')
def on_server_message(data):
    print(f"💬 [Server]: {data['msg']}")

@sio.on('typing_started')
def on_typing_started(data):
    print(f"✅ [Typing Started]: Received {len(data['text_data'].split())} words.")
    for i in range(5):
        sio.emit('keystroke', {'is_correct': True})
        time.sleep(0.6)
    sio.emit('submit_score')

@sio.on('live_stats')
def on_live_stats(data):
    print(f"📊 [Live Stats]: WPM: {data['wpm']} | Acc: {data['accuracy']}% | Flagged: {data['is_flagged']}")

@sio.on('room_leaderboard_update')
def on_leaderboard(data):
    print(f"🏆 [Leaderboard Update]: {data}")

@sio.on('score_finalized')
def on_score_finalized(data):
    print(f"🎯 [Final Score]: {data}")
    sio.disconnect()

if __name__ == '__main__':
    # จำลองการส่ง Token ไปใน handshake auth
    sio.connect('http://localhost:5000', auth={'token': None})
    sio.wait()