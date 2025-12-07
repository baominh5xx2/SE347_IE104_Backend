# Hướng Dẫn Chạy Docker

## Yêu Cầu
- Docker đã được cài đặt
- Docker Compose đã được cài đặt
- File `.env` đã được tạo với các biến môi trường cần thiết

## Các Lệnh Chạy Docker

### 1. Build và chạy container (lần đầu hoặc sau khi thay đổi code)
```bash
docker compose up -d --build
```

### 2. Chạy container (nếu đã build rồi)
```bash
docker compose up -d
```

### 3. Xem logs
```bash
# Xem logs real-time
docker compose logs -f backend

# Xem logs 100 dòng cuối
docker compose logs --tail=100 backend
```

### 4. Dừng container
```bash
docker compose down
```

### 5. Dừng và xóa volumes
```bash
docker compose down -v
```

### 6. Restart container
```bash
docker compose restart backend
```

### 7. Rebuild lại từ đầu (xóa image cũ)
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

### 8. Kiểm tra container đang chạy
```bash
docker compose ps
```

### 9. Vào trong container
```bash
docker compose exec backend bash
```

### 10. Kiểm tra health check
```bash
curl http://localhost:80/health
```

## Troubleshooting

### Container không start được
```bash
# Xem logs để biết lỗi
docker compose logs backend

# Kiểm tra xem port 80 có bị chiếm không
# Windows PowerShell:
netstat -ano | findstr :80

# Linux/Mac:
lsof -i :80
```

### Build bị lỗi
```bash
# Xóa cache và build lại
docker compose build --no-cache

# Xóa tất cả images và build lại
docker system prune -a
docker compose build --no-cache
docker compose up -d
```

### Container chạy nhưng API không hoạt động
```bash
# Kiểm tra container có đang chạy không
docker compose ps

# Kiểm tra logs
docker compose logs backend

# Test health endpoint từ trong container
docker compose exec backend curl http://localhost:8000/health
```

### Lỗi thiếu file .env
```bash
# Tạo file .env từ .env.example (nếu có)
cp .env.example .env

# Hoặc tạo file .env mới và điền các biến môi trường cần thiết
nano .env
```

## Các Port
- **Host port 80** → **Container port 8000**
- API sẽ accessible tại: `http://localhost:80` hoặc `http://localhost`

## Lưu Ý
- File `.env` phải có đầy đủ các biến môi trường cần thiết (xem `app/v1/core/config.py`)
- Nếu port 80 đã bị sử dụng, có thể đổi trong `docker-compose.yml`:
  ```yaml
  ports:
    - "8080:8000"  # Thay 80 thành 8080 hoặc port khác
  ```
