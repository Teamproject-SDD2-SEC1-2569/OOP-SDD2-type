# Typeclass WebSocket & Real-time Typing API Specification

เอกสารระบุรายละเอียดสัญญาข้อมูล (Contract) ระหว่าง **Backend Typing Engine** กับ **Frontend (Student & Teacher)** สำหรับการเชื่อมต่อแบบ Real-time ด้วย Socket.IO

---

## 1. การเชื่อมต่อและการยืนยันตัวตน (Handshake & Authentication)

* **Protocol / Host:** `ws://<server-host>:5000` (หรือ `http://<server-host>:5000`)
* **Transport:** `websocket`, `polling`
* **Authentication (TM-02):** ต้องแนบ JWT Token เข้ามาในอ็อบเจกต์ `auth` ตอนเชื่อมต่อครั้งแรก

### ตัวอย่างการเชื่อมต่อ (Frontend Client - JavaScript / TypeScript)
```javascript
import { io } from "socket.io-client";

const socket = io("http://localhost:5000", {
  auth: {
    token: localStorage.getItem("accessToken") // JWT Token ที่ได้จากการล็อกอิน
  },
  transports: ["websocket"]
});
```

---

## 2. เหตุการณ์ที่ส่งจาก Frontend ไปหา Backend (Client -> Server Events)

| Event Name | Parameter (Payload) | คำอธิบายและจังหวะการทำงาน |
| :--- | :--- | :--- |
| `join_classroom` | `{ "room_code": "SEC01" }` | เรียกทันทีที่นักเรียนใส่รหัสห้องสำเร็จ เพื่อเข้าห้อง Socket Room ร่วมกับเพื่อน |
| `start_typing` | *ไม่มี Payload* | เรียกเมื่อนักเรียนกดแป้นพิมพ์ตัวอักษรแรก เพื่อเริ่มจับเวลาและขอชุดคำศัพท์ |
| `keystroke` | `{ "is_correct": boolean }` | เรียกทุกครั้งที่มีการกดแป้นพิมพ์ 1 ตัวอักษร เพื่อส่งสถานะความถูกต้อง |
| `submit_score` | *ไม่มี Payload* | เรียกเมื่อเวลานับถอยหลังหมด (เช่น 60 วินาที) หรือพิมพ์คำศัพท์ครบ เพื่อสรุปและบันทึกคะแนน |

---

## 3. เหตุการณ์ที่ Frontend ต้องดักรับจาก Backend (Server -> Client Events)

### 3.1 `typing_started`
ทำงานเมื่อส่ง `start_typing` สำเร็จ Backend จะส่งชุดคำศัพท์สำหรับพิมพ์มาให้
```json
{
  "status": "success",
  "text_data": "the def python import return value ..." // ข้อความคละคำ 500 คำ
}
```
* **Frontend Action:** นำสตริง `text_data` ไปแยกด้วยเว้นวรรค (`.split(' ')`) เพื่อจัดเรียงลงในกล่อง Monkeytype UI

---

### 3.2 `live_stats`
ส่งกลับมาให้ผู้เรียนคนปัจจุบันทุกครั้งที่มีการส่ง `keystroke`
```json
{
  "wpm": 68,
  "accuracy": 97.5,
  "is_flagged": false
}
```
* **Frontend Action:** 
  * แสดงตัวเลข WPM และ Accuracy บนหน้าจอแบบสด
  * หาก `is_flagged: true` (พิมพ์เร็วเกิน 320 WPM เข้าข่ายบอท) ให้ขึ้นแจ้งเตือนหรือเตรียมปรับคะแนน

---

### 3.3 `room_leaderboard_update`
ส่งบรอดแคสต์ให้ผู้เรียนและอาจารย์ทุกคนในห้องเดียวกัน (`room_code`) แบบ Real-time
```json
[
  {
    "username": "Somchai_S",
    "wpm": 84,
    "accuracy": 98.2
  },
  {
    "username": "Ratsamee_K",
    "wpm": 72,
    "accuracy": 99.0
  }
]
```
* **Frontend Action:** นำ Array นี้ไปวนลูปแสดงแถบอันดับสด (Live Leaderboard) ข้างจอ โดยข้อมูลเรียงตาม WPM จากมากไปน้อยให้อัตโนมัติ

---

### 3.4 `score_finalized`
ส่งกลับมาเมื่อส่ง `submit_score` และประมวลผลคะแนนเสร็จสิ้น
```json
{
  "wpm": 70,
  "accuracy": 98.0,
  "score": 686,
  "user_id": "std_1001",
  "username": "Somchai_S",
  "is_flagged": false
}
```
* **Frontend Action:** นำข้อมูลไปแสดงผลในการ์ดสรุปคะแนน (Result Modal/Page) และนำทางไปยังหน้า Dashboard

---

### 3.5 `error`
ส่งข้อความแจ้งเตือนข้อผิดพลาด
```json
{
  "msg": "Unauthorized: Invalid or expired token."
}
```
* **Frontend Action:** แสดง Toast แจ้งเตือน หรือพากลับไปหน้า Login หาก Token ไม่ถูกต้อง