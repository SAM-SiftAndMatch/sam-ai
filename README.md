# Sam AI

Dự án FastAPI đơn giản phục vụ kiểm tra health check và làm nền tảng ban đầu.

## 📦 Cài đặt thư viện

Môi trường ảo (virtualenv) `.venv` đã được khởi tạo và cài đặt sẵn:
- `fastapi`
- `uvicorn`
- `pydantic`
- `python-dotenv`

Nếu cần cài đặt lại thủ công:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 🚀 Chạy server

Chạy trực tiếp bằng python:
```bash
python main.py
```
Hoặc dùng uvicorn:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🔍 Kiểm tra API

- Trang chủ: `http://localhost:8000/`
- Kiểm tra Health: `http://localhost:8000/health`
- Swagger UI (Docs tương tác): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
