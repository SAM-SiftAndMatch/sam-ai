# Sam AI

Dự án FastAPI phục vụ kiểm tra health check, kết nối MongoDB Atlas, hỗ trợ Docker, CI/CD và Git Hooks theo mô hình cấu trúc phân tầng (Clean / Layered Architecture).

---

## 📁 Cấu trúc thư mục dự án

```text
sam-ai/
├── app/                      # Mã nguồn chính của ứng dụng
│   ├── api/                  # Tầng định tuyến (Routing)
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   └── health.py # Endpoint kiểm tra sức khỏe hệ thống
│   │   │   └── router.py     # Gom các endpoints v1
│   │   └── router.py         # Router tổng hợp toàn bộ API
│   ├── core/                 # Cấu hình hệ thống & bảo mật
│   │   └── config.py         # Quản lý cấu hình bằng pydantic-settings
│   ├── db/                   # Tầng kết nối cơ sở dữ liệu
│   │   └── mongodb.py        # Quản lý kết nối Motor Async MongoDB Atlas
│   ├── schemas/              # Pydantic schemas (Request / Response models)
│   │   └── health.py         # Schema HealthResponse
│   ├── services/             # Business Logic & AI Pipelines (sẵn sàng mở rộng)
│   ├── models/               # MongoDB Document Models (sẵn sàng mở rộng)
│   └── main.py               # Khởi tạo FastAPI App, CORS, Lifespan & Middleware
├── tests/                    # Unit tests tự động với pytest
│   └── test_main.py
├── .github/workflows/        # CI/CD pipelines (ci-pr.yml, ci-main.yml)
├── main.py                   # File entrypoint mỏng gọi server
├── pyproject.toml            # File cấu hình trung tâm (Project, Ruff, Pytest)
├── Makefile                  # Bộ phím tắt quản lý toàn bộ dự án
├── Dockerfile                # Image build tối ưu production
├── docker-compose.yml        # Điều phối container
└── requirements.txt          # Danh sách thư viện chính
```

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
- **Core**: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `python-dotenv`, `motor`
- **Dev**: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `pre-commit`

Cài đặt bằng Makefile:
```bash
make install-dev
```

---

## ⚙️ Cấu hình MongoDB & CORS (.env)

Cấu hình lưu trong `.env`:
```env
APP_NAME="Sam AI"
HOST=0.0.0.0
PORT=8000
DEBUG=True

CORS_ORIGINS="*"

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
- **Kiểm tra Health**: `http://localhost:8000/health` hoặc `http://localhost:8000/api/v1/health`
- **Swagger UI (Docs tương tác)**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
