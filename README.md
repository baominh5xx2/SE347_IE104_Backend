# AI Assistant Backend - LangGraph Implementation

Backend API cho AI Assistant sử dụng **LangGraph** để orchestrate AI agent workflow.

## 🚀 Tính năng

- ✅ **LangGraph Integration**: Workflow-based AI agent với multi-step reasoning
- ✅ **FastAPI**: Modern, fast web framework
- ✅ **Conversation Management**: Quản lý lịch sử hội thoại
- ✅ **State Management**: Tracking trạng thái agent qua các bước
- ✅ **Modular Architecture**: Cấu trúc code rõ ràng, dễ mở rộng
- ✅ **Type Safety**: Pydantic schemas cho validation

## 📁 Cấu trúc dự án

```
Backend/
├── main.py                 # FastAPI application entry point
├── requirements.txt        # Python dependencies
├── agent.yaml             # Agent configuration
├── .env                   # Environment variables
└── app/
    └── v1/
        ├── api/
        │   ├── router.py           # Main API router
        │   └── endpoints/
        │       ├── chat.py         # Chat endpoints
        │       ├── agent.py        # Agent management
        │       └── health.py       # Health checks
        ├── core/
        │   └── config.py           # Configuration settings
        ├── schema/
        │   └── agent_schema.py     # Pydantic models
        └── services/
            └── agent_services/
                ├── langgraph_agent.py      # LangGraph agent
                └── conversation_manager.py  # Conversation management
```

## 🛠️ Cài đặt

### 1. Clone repository và di chuyển vào thư mục Backend

```bash
cd Backend
```

### 2. Cài đặt uv (nếu chưa có)

```powershell
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

hoặc

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Cài đặt dependencies với uv

```bash
uv sync
```

Lệnh này sẽ:
- Tự động tạo virtual environment
- Cài đặt tất cả dependencies từ `pyproject.toml`
- Tạo lock file để đảm bảo tính nhất quán

### 4. Cấu hình environment variables

Tạo file `.env` từ `.env.example`:

```bash
copy .env.example .env
```

Cập nhật các giá trị trong `.env`:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview
```

## 🚀 Chạy ứng dụng

### Development mode với uv (Recommended ⭐)

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

hoặc đơn giản hơn:

```bash
uv run python main.py
```

### Chạy với pip (Cách truyền thống)

```bash
python main.py
```

API sẽ chạy tại: `http://localhost:8000`

### Swagger Documentation

Truy cập API documentation tại: `http://localhost:8000/docs`

## 📡 API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Đăng ký (email, phone, password, full_name)
- `POST /api/v1/auth/login` - Đăng nhập (email/phone + password)
- `POST /api/v1/auth/verify-token` - Verify JWT token
- `GET /api/v1/auth/google` - Google OAuth URL
- `GET /api/v1/auth/google/callback` - Google OAuth callback

### Tour Packages
- `GET /api/v1/tour-packages` - Lấy danh sách tour (có pagination)
- `GET /api/v1/tour-packages/{id}` - Chi tiết tour
- `POST /api/v1/tour-packages` - Tạo tour mới
- `PUT /api/v1/tour-packages/{id}` - Cập nhật tour
- `DELETE /api/v1/tour-packages/{id}` - Xóa tour

### Bookings
- `GET /api/v1/bookings` - Lấy danh sách bookings (filter by user_id, status)
- `GET /api/v1/bookings/{id}` - Chi tiết booking
- `POST /api/v1/bookings` - Tạo booking mới
- `PUT /api/v1/bookings/{id}` - Cập nhật booking
- `DELETE /api/v1/bookings/{id}` - Xóa booking (hoàn trả slots)

### AI Chatbot
- `POST /api/v1/agent/chat` - Chat với AI assistant
- `GET /api/v1/agent/history/{user_id}` - Lịch sử chat

### Health Check
- `GET /health` - Health check
- `GET /api/v1/health/` - Detailed health status
- `GET /api/v1/health/ready` - Readiness check

## 💬 Ví dụ sử dụng

### Đăng ký tài khoản

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Nguyen Van A",
    "email": "a.nguyen@example.com",
    "phone_number": "0123456789",
    "password": "password123"
  }'
```

### Đăng nhập bằng email

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "a.nguyen@example.com",
    "password": "password123"
  }'
```

### Đăng nhập bằng phone

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "0123456789",
    "password": "password123"
  }'
```

### Tạo tour mới

```bash
curl -X POST "http://localhost:8000/api/v1/tour-packages" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "Ha Long Bay 3N2D",
    "destination": "Ha Long",
    "description": "Explore the beautiful Ha Long Bay",
    "duration_days": 3,
    "price": 5000000,
    "available_slots": 20,
    "start_date": "2025-12-01",
    "end_date": "2025-12-03",
    "image_urls": "https://example.com/img1.jpg|https://example.com/img2.jpg",
    "cuisine": "Vietnamese seafood",
    "suitable_for": "Family, Couples"
  }'
```

### Tạo booking

```bash
# total_amount sẽ tự động tính = price * number_of_people
curl -X POST "http://localhost:8000/api/v1/bookings" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "package_id": "123e4567-e89b-12d3-a456-426614174000",
    "number_of_people": 2,
    "contact_name": "Nguyen Van A",
    "contact_phone": "0123456789",
    "special_requests": "Phòng view đẹp",
    "user_id": "bcde5ff1-5fd7-49e0-8790-05463092d54e"
  }'
```

## 🧪 Testing

```bash
# Chạy tất cả tests
pytest tests/ -v

# Test tour package service
pytest tests/test_tour_package.py -v

# Test booking service
pytest tests/test_booking.py -v

# Test authentication
pytest tests/test_auth/ -v
```

## 🔑 Database Schema

### users
- `user_id` (UUID, PK)
- `email` (unique)
- `phone_number` (unique, nullable)
- `full_name`
- `password_hash` (nullable, cho Google OAuth)
- `login_type` (TRADITIONAL/GOOGLE)
- `is_activate` (boolean)

### tour_packages
- `package_id` (UUID, PK)
- `package_name`, `destination`, `description`
- `duration_days`, `price`, `available_slots`
- `start_date`, `end_date`
- `image_urls` (pipe-separated URLs)
- `cuisine`, `suitable_for`
- `is_active` (boolean)

### bookings
- `booking_id` (UUID, PK)
- `package_id` (UUID, FK → tour_packages)
- `user_id` (UUID, FK → users)
- `number_of_people`, `total_amount`
- `contact_name`, `contact_phone`
- `special_requests` (optional)
- `status` (pending/confirmed/cancelled/completed)
- `created_at`, `updated_at`

### package_embeddings
- `package_id` (UUID, FK → tour_packages)
- `embedding` (vector[1536])
- Auto-generated bằng OpenAI text-embedding-3-small

## 🔄 Business Logic

### Booking Flow
1. **Create Booking**: 
   - Kiểm tra tour package tồn tại và active
   - Kiểm tra available_slots đủ
   - **Tự động tính total_amount** = package.price × number_of_people
   - Tạo booking với status="pending"
   - Trừ slots khỏi tour package

2. **Update Booking**:
   - Cho phép thay đổi number_of_people (cập nhật slots tương ứng)
   - **Tự động tính lại total_amount** khi thay đổi number_of_people
   - Cho phép thay đổi status (pending → confirmed → completed)
   - Không cho phép thay đổi package_id

3. **Delete Booking**:
   - Xóa booking khỏi database
   - Hoàn trả slots về tour package (nếu status là pending/confirmed)

## 📚 Tech Stack

- **Framework**: FastAPI 0.115+
- **Database**: Supabase (PostgreSQL + pgvector)
- **Authentication**: JWT, bcrypt, Google OAuth
- **AI**: OpenAI GPT-4, LangGraph, MCP
- **Embeddings**: OpenAI text-embedding-3-small (1536 dims)
- **Testing**: pytest, pytest-asyncio
- **Package Manager**: uv

## 🐛 Troubleshooting

**Lỗi Supabase connection:**  
Kiểm tra `SUPABASE_URL` và `SUPABASE_KEY` trong `.env`

**Lỗi embedding dimension:**  
Đảm bảo sử dụng model `text-embedding-3-small` (1536 dims), không phải `text-embedding-3-large` (3072 dims)

**Port 8000 đã sử dụng:**  
```bash
uv run uvicorn main:app --port 8001
```

**Test failures:**  
Đảm bảo đã mock các OpenAI API calls trong tests

**Booking không trừ slots:**  
Kiểm tra foreign key constraints giữa bookings và tour_packages

## 📝 License

MIT License

