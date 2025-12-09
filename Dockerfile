# Sử dụng Python 3.11 slim
FROM python:3.11-slim

# Cài đặt các thư viện hệ thống cần thiết
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Cài đặt uv
RUN pip install uv

# Thiết lập thư mục làm việc
WORKDIR /app

# Copy file cấu hình package
COPY pyproject.toml .

# Cài đặt package bằng uv (cài thẳng vào system python cho lẹ, khỏi venv lằng nhằng)
RUN uv pip install --system --no-cache-dir .

# Copy toàn bộ code vào
COPY . .

# Runtime env (không set secrets ở build-time; override khi docker run/compose)
ENV OPENAI_API_KEY=""
ENV OPENAI_API_KEY_EXPORT=""

# Tạo user để chạy cho an toàn (optional, nhưng tốt)
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (Backend bạn chạy port mấy thì sửa số này, ví dụ 8000)
EXPOSE 8000

# Lệnh chạy server (Sửa lại cho đúng lệnh start của bạn)
# Ví dụ nếu dùng FastAPI:
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
# Hoặc nếu dùng Python thường:
# CMD ["python", "main.py"]
