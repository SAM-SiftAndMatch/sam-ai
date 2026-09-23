# Sam AI

Dự án FastAPI phục vụ kiểm tra health check và kết nối MongoDB Atlas.

## 📦 Cài đặt thư viện

Môi trường ảo (virtualenv) `.venv` đã được cài đặt sẵn:
- `fastapi`
- `uvicorn[standard]`
- `pydantic`
- `python-dotenv`
- `motor` (Async MongoDB Driver)

Nếu cần cài đặt lại thủ công:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## ⚙️ Cấu hình MongoDB (.env)

Cấu hình kết nối tới MongoDB Atlas đã được lưu trong `.env`:
```env
MONGO_URI=mongodb+srv://<db_username>:<password>@ai-data.jkjhbcq.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=sam_ai_db
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

- **Trang chủ**: `http://localhost:8000/`
- **Kiểm tra Health & DB**: `http://localhost:8000/health` (sẽ trả về trạng thái `database: "connected"`)
- **Swagger UI (Docs tương tác)**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
