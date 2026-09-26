.PHONY: help install install-dev run dev seed-embed test lint format clean docker-build docker-run docker-stop compose-up compose-down compose-logs pre-commit-install pre-commit-run

PYTHON ?= .venv/bin/python
PIP ?= .venv/bin/pip
UVICORN ?= .venv/bin/uvicorn
PYTEST ?= .venv/bin/pytest
RUFF ?= .venv/bin/ruff
PRE_COMMIT ?= .venv/bin/pre-commit

IMAGE_NAME ?= sam-ai:latest
CONTAINER_NAME ?= sam_ai_api

help: ## Hiển thị danh sách các lệnh hữu ích
	@echo "Các lệnh khả dụng trong dự án:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

venv: ## Khởi tạo môi trường ảo Python
	python3 -m venv .venv
	@echo "Môi trường .venv đã được tạo. Chạy 'source .venv/bin/activate' để kích hoạt."

install: ## Cài đặt dependencies chính
	$(PIP) install -r requirements.txt

install-dev: ## Cài đặt toàn bộ dependencies (bao gồm dev, test, lint)
	$(PIP) install -r requirements-dev.txt

dev: ## Chạy server FastAPI ở chế độ development (auto-reload)
	$(UVICORN) app.main:app --reload --host 0.0.0.0 --port 8000

run: ## Chạy server FastAPI production
	$(PYTHON) main.py

seed-embed: ## Chạy all-in-one pipeline: tạo embedding Ollama và seed vào MongoDB
	$(PYTHON) scripts/seed_and_embed_chunks.py

test: ## Chạy test suite với pytest
	$(PYTEST) -v

lint: ## Kiểm tra định dạng code với ruff
	$(RUFF) check .
	$(RUFF) format --check .

format: ## Tự động sửa định dạng code với ruff
	$(RUFF) check --fix .
	$(RUFF) format .

pre-commit-install: ## Cài đặt pre-commit git hook
	$(PRE_COMMIT) install

pre-commit-run: ## Chạy pre-commit kiểm tra toàn bộ files
	$(PRE_COMMIT) run --all-files

docker-build: ## Build Docker image cho API
	docker build -t $(IMAGE_NAME) .

docker-run: ## Chạy Docker container đơn lẻ
	docker rm -f $(CONTAINER_NAME) 2>/dev/null || true
	docker run -d --name $(CONTAINER_NAME) -p 8000:8000 --env-file .env $(IMAGE_NAME)

docker-stop: ## Dừng và xóa Docker container
	docker stop $(CONTAINER_NAME) || true
	docker rm $(CONTAINER_NAME) || true

compose-up: ## Khởi chạy dịch vụ bằng Docker Compose
	docker compose up -d --build

compose-down: ## Dừng dịch vụ Docker Compose
	docker compose down

compose-logs: ## Xem logs thời gian thực của Docker Compose
	docker compose logs -f

clean: ## Dọn dẹp cache và file tạm
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.py[cod]" -delete
	rm -rf .pytest_cache .ruff_cache htmlcov .coverage
