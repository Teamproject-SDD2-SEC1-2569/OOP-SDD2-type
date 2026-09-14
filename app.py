from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Typeclass Server is running on Docker!"

if __name__ == '__main__':
    # จำเป็นต้องใช้ host='0.0.0.0' ใน Docker เพื่อให้สามารถเข้าถึงเว็บจากภายนอก Container ได้
    app.run(host='0.0.0.0', port=5000, debug=True)