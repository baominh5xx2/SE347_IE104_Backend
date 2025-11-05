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

### Health Check
- `GET /health` - Health check
- `GET /api/v1/health/` - Detailed health status
- `GET /api/v1/health/ready` - Readiness check

### Chat
- `POST /api/v1/chat/` - Gửi tin nhắn
- `GET /api/v1/chat/conversation/{conversation_id}` - Lấy lịch sử hội thoại
- `DELETE /api/v1/chat/conversation/{conversation_id}` - Xóa hội thoại

### Agent Management
- `GET /api/v1/agent/status` - Trạng thái agent
- `GET /api/v1/agent/graph` - Cấu trúc LangGraph
- `GET /api/v1/agent/info` - Thông tin chi tiết agent

## 💬 Ví dụ sử dụng

### Gửi tin nhắn chat

```bash
curl -X POST "http://localhost:8000/api/v1/chat/" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is LangGraph?",
    "conversation_id": null,
    "user_id": "user_123"
  }'
```

Response:

```json
{
  "conversation_id": "conv_abc123",
  "message": "LangGraph is a library for building stateful, multi-actor applications...",
  "metadata": {
    "iterations": 1,
    "final_step": "validating_response",
    "validated": true
  },
  "timestamp": "2025-10-10T10:30:00.000Z"
}
```

### Lấy lịch sử hội thoại

```bash
curl -X GET "http://localhost:8000/api/v1/chat/conversation/conv_abc123"
```

## 🔄 LangGraph Workflow

Agent sử dụng workflow sau:

```
[Start] 
   ↓
[Process Input] - Xử lý input và chuẩn bị context
   ↓
[Generate Response] - Tạo response bằng LLM
   ↓
[Validate Response] - Kiểm tra chất lượng response
   ↓
Decision:
  - Valid → [End]
  - Invalid & iterations < max → [Generate Response]
  - Max iterations → [End]
```

## 🧩 Các component chính

### 1. LangGraphAgent
- Orchestrate workflow của AI agent
- Multi-step reasoning với validation
- State management qua các bước

### 2. ConversationManager
- Quản lý lịch sử hội thoại
- In-memory storage (có thể mở rộng với Redis/Database)
- Context tracking

### 3. Schemas
- Type-safe models với Pydantic
- Request/Response validation
- State definitions

## 🔧 Mở rộng

### Thêm node mới vào workflow

Trong `langgraph_agent.py`:

```python
def _build_graph(self):
    workflow = StateGraph(AgentState)
    
    # Thêm node mới
    workflow.add_node("your_new_node", self._your_new_function)
    
    # Thêm edge
    workflow.add_edge("previous_node", "your_new_node")
    
    return workflow.compile()
```

### Thêm tools cho agent

1. Tạo tool function trong `langgraph_agent.py`
2. Register tool với agent
3. Update workflow để sử dụng tool

## 📚 Tài liệu tham khảo

- [LangGraph Documentation](https://python.langchain.com/docs/langgraph)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangChain Documentation](https://python.langchain.com/)

## 🐛 Troubleshooting

### Lỗi OpenAI API Key
Đảm bảo đã set `OPENAI_API_KEY` trong file `.env`

### Lỗi import modules
Chạy `pip install -r requirements.txt` để cài đặt đầy đủ dependencies

### Port đã được sử dụng
Thay đổi port trong `.env` hoặc khi chạy uvicorn:
```bash
uvicorn main:app --port 8001
```

## 📝 License

MIT License
