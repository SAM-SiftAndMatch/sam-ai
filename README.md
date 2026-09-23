# Sam AI

Dự án FastAPI phục vụ kiểm tra health check, kết nối MongoDB Atlas, hỗ trợ Docker, CI/CD và Git Hooks.

---

## 🛠️ Lệnh nhanh với Makefile

Dự án hỗ trợ `Makefile` giúp thao tác nhanh:
```bash
make help               # Xem danh sách tất cả các lệnh khả dụng
make dev                # Chạy server FastAPI ở chế độ development (auto-reload)
make test               # Chạy test suite với pytest
make lint               # Kiểm tra format & lint với ruff
make format             # Tự động sửa format với ruff
make pre-commit-run     # Chạy pre-commit kiểm tra toàn bộ files
make docker-build       # Build Docker image
make compose-up         # Khởi chạy toàn bộ hệ thống bằng Docker Compose
make compose-down       # Dừng Docker Compose
```

---

## 📦 Cài đặt thư viện

Môi trường ảo (virtualenv) `.venv` đã được cài đặt sẵn:
- **Core**: `fastapi`, `uvicorn[standard]`, `pydantic`, `python-dotenv`, `motor`
- **Dev**: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `pre-commit`

Cài đặt bằng Makefile:
```bash
make install-dev
```

---

## ⚙️ Cấu hình MongoDB (.env)

Cấu hình kết nối tới MongoDB Atlas đã được lưu trong `.env`:
```env
MONGO_URI=mongodb+srv://<username>:<password>@ai-data.jkjhbcq.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=sam_ai_db
```

---

## 🐳 Docker & Docker Compose

### 1. Build & Chạy Docker Image
```bash
make docker-build
make docker-run
```

### 2. Sử dụng Docker Compose
```bash
# Khởi chạy dịch vụ API
make compose-up

# Xem logs
make compose-logs

# Dừng dịch vụ
make compose-down
```

*(Nếu muốn chạy kèm MongoDB local trên máy thay vì Atlas, dùng: `docker compose --profile local-db up -d`)*

---

## 🔄 CI/CD & Pre-commit

- **Pre-commit**: Tự động kiểm tra cú pháp, loại bỏ trailing whitespace, phát hiện private key, kiểm tra và format code bằng `ruff` trước mỗi commit.
  - Cài đặt hook vào git: `make pre-commit-install`
  - Chạy thủ công: `make pre-commit-run`
- **GitHub Actions**:
  - `.github/workflows/ci-pr.yml`: Kích hoạt khi tạo Pull Request (kiểm tra lint, format, chạy unit test và build test Docker).
  - `.github/workflows/ci-main.yml`: Kích hoạt khi push lên nhánh `main` (chạy test, build image và kiểm tra container healthcheck).

---

## 🔍 Kiểm tra API

- **Trang chủ**: `http://localhost:8000/`
- **Kiểm tra Health & DB**: `http://localhost:8000/health` (trả về trạng thái `database: "connected"`)
- **Swagger UI (Docs tương tác)**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
