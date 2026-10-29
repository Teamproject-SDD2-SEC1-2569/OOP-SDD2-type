# 🚀 Typeclass - Project Setup Guide (สำหรับทีม Developer)

คู่มือนี้สำหรับสมาชิกในทีม (Backend, Teacher Feature หรือผู้ทดสอบ) ที่ต้องการ Clone โปรเจกต์นี้ไปพัฒนาต่อในเครื่องของตัวเอง

## 1. การเตรียมความพร้อม (Prerequisites)
* สิ่งที่ต้องมีในเครื่อง: **Python 3.8+** และ **Git**
* ขอข้อมูลไฟล์ `.env` (รหัสผ่าน Oracle Database และ JWT Secret Key) จากทีม

## 2. ขั้นตอนการติดตั้งและรันโปรเจกต์

**Step 1: Clone โปรเจกต์ และสลับไปยัง Branch ที่ต้องการทำงาน**
```bash
git clone [https://github.com/Teamproject-SDD2-SEC1-2569/OOP-SDD2-type.git](https://github.com/Teamproject-SDD2-SEC1-2569/OOP-SDD2-type.git)
cd OOP-SDD2-type
git checkout <ชื่อ-branch-ของคุณ>

Step 2: สร้างและเปิดใช้งาน Virtual Environment
เพื่อป้องกันไม่ให้แพ็กเกจของโปรเจกต์ตีกับระบบในเครื่อง

Windows:

Bash
python -m venv .venv
.venv\Scripts\activate

Mac/Linux:

Bash
python3 -m venv .venv
source .venv/bin/activate

Step 3: ติดตั้ง Libraries ที่จำเป็น

Bash
pip install -r requirements.txt

Step 4: ตั้งค่าตัวแปรสภาพแวดล้อม (Environment Variables)
เนื่องจากไฟล์ .env ถูก Ignore ไว้เพื่อความปลอดภัย ให้สร้างไฟล์ชื่อ .env ไว้ที่โฟลเดอร์นอกสุด (ระดับเดียวกับ run.py) และใส่ข้อมูลดังนี้:

Code snippet
# ตั้งค่า Oracle Database (สอบถาม Password จากทีม Database)
ORACLE_DB_USER=WEB_APP_USER
ORACLE_DB_PASSWORD=your_password_here
ORACLE_DB_DSN=(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.ap-singapore-1.oraclecloud.com))(connect_data=(service_name=gce18b24390782a_typeclass_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))

# ตั้งค่าความปลอดภัยสำหรับ Flask และ JWT
SECRET_KEY=typeclass-super-secret-key

Step 5: รันเซิร์ฟเวอร์

Bash
python run.py
เซิร์ฟเวอร์จะรันที่ http://127.0.0.1:5000 สามารถเปิดดูในเบราว์เซอร์ได้ทันที

📂 โครงสร้างโฟลเดอร์ที่ควรรู้ (Project Structure)
app/route.py: จัดการ Routing และ WebSocket (Socket.IO) ทั้งหมด

app/database.py: ฟังก์ชันเชื่อมต่อ Oracle Database

app/models.py: คลาสจัดการระบบพิมพ์ (เช่น StandardTypingSession)

app/templates/student/: ไฟล์ HTML ฝั่งนักเรียน (UI/UX หลัก)

app/static/css/style.css: ไฟล์จัดการธีมและหน้าตาเว็บทั้งหมด