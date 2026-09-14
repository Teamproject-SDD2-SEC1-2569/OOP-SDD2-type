FROM python:3.11-slim

# ตั้งค่า Directory การทำงานใน Container
WORKDIR /app

# คัดลอกไฟล์ requirements.txt และติดตั้งไลบรารี
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกโค้ดทั้งหมดเข้า Container
COPY . .

# เปิดพอร์ต 5000 สำหรับ Flask
EXPOSE 5000

# รันแอปพลิเคชัน
CMD ["python", "app.py"]