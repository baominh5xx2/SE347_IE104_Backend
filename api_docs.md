# API Documentation

**Base URL:** `http://localhost:8000`  
**Version:** 1.0.0

---

## 🔐 Authentication APIs

**Base URL:** `/api/v1/auth`

### 1. Register User
**Method:** `POST /register`

**Request:**
```json
{
  "full_name": "Nguyen Van A",
  "email": "a.nguyen@example.com",
  "password": "password123",
  "phone_number": "0123456789"
}
```

**Response:**
```json
{
  "EC": 0,
  "EM": "User registered successfully",
  "user": {
    "user_id": "bcde5ff1-5fd7-49e0-8790-05463092d54e",
    "email": "a.nguyen@example.com",
    "full_name": "Nguyen Van A",
    "phone_number": "0123456789"
  }
}
```

**Error Codes:**
- `0` = Success
- `1` = Email already exists
- `2` = Failed to create user

---

### 2. Login
**Method:** `POST /login`

**Request:**
```json
{
  "email": "a.nguyen@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "EC": 0,
  "EM": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "bcde5ff1-5fd7-49e0-8790-05463092d54e",
    "email": "a.nguyen@example.com",
    "full_name": "Nguyen Van A",
    "phone_number": "0123456789"
  }
}
```

**Error Codes:**
- `0` = Success
- `1` = User not found
- `2` = Invalid password
- `3` = Account not activated

---

### 3. Verify Token
**Method:** `POST /verify-token`

**Request (Option 1 - Body):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Request (Option 2 - Header):**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Response:**
```json
{
  "EC": 0,
  "EM": "Token is valid",
  "data": {
    "email": "a.nguyen@example.com",
    "full_name": "Nguyen Van A",
    "user_id": "bcde5ff1-5fd7-49e0-8790-05463092d54e",
    "exp": 1730361234
  }
}
```

**Error Codes:**
- `0` = Success
- `1` = Token expired
- `2` = Token invalid

---

### 4. Get Google OAuth URL
**Method:** `GET /google/auth-url`

**Response:**
```json
{
  "EC": 0,
  "EM": "Google OAuth URL generated",
  "auth_url": "https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=..."
}
```

---

### 5. Google OAuth Callback
**Method:** `GET /google/callback`

**Query Parameters:**
- `code` (required) - Authorization code from Google
- `state` (optional) - CSRF protection
- `format` (optional) - `json` (default) or `redirect`

**Response (Default - JSON):**
```json
{
  "EC": 0,
  "EM": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "6f7b1fb4-9aad-4753-9bdd-9fcee0b49ef2",
    "email": "user@gmail.com",
    "full_name": "User Name",
    "phone_number": "0123456789",
    "profile_picture": "https://lh3.googleusercontent.com/..."
  }
}
```

**Response (format=redirect):**
- Success: Redirect to `http://localhost:3000/auth/callback?token=ACCESS_TOKEN`
- Error: Redirect to `http://localhost:3000/login?error=ERROR_MESSAGE`

**Error Codes:**
- `0` = Success
- `1` = OAuth error
- `6` = Failed to exchange token

---

### 6. Login with Google ID Token
**Method:** `POST /google/login`

**Request:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjU5N..."
}
```

**Response:**
```json
{
  "EC": 0,
  "EM": "Login successful",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "user_id": "6f7b1fb4-9aad-4753-9bdd-9fcee0b49ef2",
    "email": "user@gmail.com",
    "full_name": "User Name",
    "phone_number": null,
    "profile_picture": "https://lh3.googleusercontent.com/..."
  }
}
```

**Error Codes:**
- `0` = Success
- `1` = Invalid token
- `2` = Email not verified
- `3` = Account not activated
- `4` = Failed to create user

---

## 🎫 Tour Package APIs

**Base URL:** `/api/v1/tour-packages`

⚠️ **LƯU Ý QUAN TRỌNG:** 
- Các endpoint GET/POST/PUT/DELETE đều cần **dấu `/` cuối cùng** hoặc có `{package_id}` cụ thể
- Header bắt buộc: `Content-Type: application/json` cho POST/PUT requests

---

### 1. Get All Tour Packages
**Method:** `GET /`

Lấy danh sách tất cả tour packages với các tùy chọn lọc và phân trang.

**Query Parameters (All Optional):**
- `is_active` (boolean): Lọc theo trạng thái kích hoạt
- `destination` (string): Lọc theo điểm đến (tìm kiếm gần đúng)
- `limit` (integer 1-100): Giới hạn số lượng kết quả
- `offset` (integer): Bỏ qua số lượng bản ghi

**Example Requests:**
```
GET /api/v1/tour-packages/
GET /api/v1/tour-packages/?is_active=true&limit=10
GET /api/v1/tour-packages/?destination=Đà Lạt
GET /api/v1/tour-packages/?is_active=true&destination=Hà Nội&limit=5&offset=0
```

**Response:**
```json
{
  "EC": 0,
  "EM": "Successfully retrieved tour packages",
  "total": 7,
  "packages": [
    {
      "package_id": "fe5d44aa-5435-4110-a2d2-947f716f0ebc",
      "package_name": "Ninh Bình - Tràng An UNESCO 2N1Đ",
      "destination": "Ninh Bình",
      "description": "Khám phá Ninh Bình...",
      "duration_days": 2,
      "price": 3200000.0,
      "available_slots": 10000,
      "departure_location": "Hà Nội",
      "start_date": "2025-11-22",
      "end_date": "2025-11-23",
      "includes": ["Xe ô tô", "Khách sạn 3 sao", "Ăn sáng buffet"],
      "excludes": ["Đồ uống ngoài bữa ăn", "Chi phí cá nhân"],
      "itinerary": {
        "day1": {
          "title": "HÀ NỘI - TRÀNG AN",
          "morning": "07:00 - Khởi hành...",
          "afternoon": "14:00 - Tham quan..."
        }
      },
      "image_url": "https://images.example.com/ninhbinh.jpg",
      "is_active": true,
      "created_at": "2025-10-15T16:45:34.445637",
      "updated_at": "2025-10-15T16:45:34.445637"
    }
  ]
}
```

**Error Codes:**
- `0` = Success
- `1` = Error retrieving packages

---

### 2. Get Tour Package by ID
**Method:** `GET /{package_id}`

Lấy thông tin chi tiết của một tour package cụ thể.

**Path Parameters:**
- `package_id` (UUID, required): ID của tour package

**Example Request:**
```
GET /api/v1/tour-packages/fe5d44aa-5435-4110-a2d2-947f716f0ebc
```

**Response:**
```json
{
  "EC": 0,
  "EM": "Successfully retrieved tour package",
  "package": {
    "package_id": "fe5d44aa-5435-4110-a2d2-947f716f0ebc",
    "package_name": "Ninh Bình - Tràng An UNESCO 2N1Đ",
    "destination": "Ninh Bình",
    "description": "Khám phá Ninh Bình - vùng đất địa linh nhân kiệt...",
    "duration_days": 2,
    "price": 3200000.0,
    "available_slots": 10000,
    "departure_location": "Hà Nội",
    "start_date": "2025-11-22",
    "end_date": "2025-11-23",
    "includes": ["Xe ô tô đời mới", "Khách sạn 3 sao", "Ăn sáng buffet"],
    "excludes": ["Đồ uống ngoài bữa ăn", "Chi phí cá nhân"],
    "itinerary": {
      "day1": {...},
      "day2": {...}
    },
    "image_url": "https://images.example.com/ninhbinh.jpg",
    "is_active": true,
    "created_at": "2025-10-15T16:45:34.445637",
    "updated_at": "2025-10-15T16:45:34.445637"
  }
}
```

**Error Codes:**
- `0` = Success
- `1` = Tour package not found
- `2` = Error retrieving package

---

### 3. Create Tour Package
**Method:** `POST /`

Tạo mới một tour package.

**Headers:**
```
Content-Type: application/json
```

**Request Body (All fields required except excludes, itinerary, image_url):**
```json
{
  "package_name": "Tour Đà Lạt 3N2Đ",
  "destination": "Đà Lạt",
  "description": "Tour khám phá thành phố ngàn hoa với khí hậu mát mẻ quanh năm",
  "duration_days": 3,
  "price": 2500000,
  "available_slots": 20,
  "departure_location": "TP.HCM",
  "start_date": "2024-12-01",
  "end_date": "2024-12-03",
  "includes": [
    "Khách sạn 4 sao",
    "Ăn 3 bữa/ngày",
    "Hướng dẫn viên"
  ],
  "excludes": [
    "Vé máy bay",
    "Chi phí cá nhân"
  ],
  "itinerary": {
    "day1": {
      "title": "TP.HCM - Đà Lạt",
      "morning": "Khởi hành từ TP.HCM",
      "afternoon": "Tham quan hồ Xuân Hương",
      "evening": "Khám phá chợ đêm"
    },
    "day2": {
      "title": "Thác Datanla - Hồ Tuyền Lâm",
      "morning": "Tham quan thác Datanla",
      "afternoon": "Đi cáp treo hồ Tuyền Lâm"
    },
    "day3": {
      "title": "Về TP.HCM",
      "morning": "Mua sắm đặc sản",
      "afternoon": "Về TP.HCM"
    }
  },
  "image_url": "https://images.example.com/dalat.jpg",
  "is_active": true
}
```

**Field Descriptions:**
- `package_name` (string, 1-255 chars): Tên gói tour
- `destination` (string, 1-255 chars): Điểm đến
- `description` (string): Mô tả chi tiết tour
- `duration_days` (integer > 0): Số ngày tour
- `price` (float > 0): Giá tour (VNĐ)
- `available_slots` (integer ≥ 0): Số chỗ còn trống
- `departure_location` (string, 1-255 chars): Điểm khởi hành
- `start_date` (date, format: YYYY-MM-DD): Ngày bắt đầu
- `end_date` (date, format: YYYY-MM-DD): Ngày kết thúc
- `includes` (array of strings): Các dịch vụ bao gồm
- `excludes` (array of strings, optional): Các dịch vụ không bao gồm
- `itinerary` (object, optional): Lịch trình chi tiết theo ngày (JSONB)
- `image_url` (string, optional, max 500 chars): URL hình ảnh
- `is_active` (boolean, default: true): Trạng thái kích hoạt

**Response (201 Created):**
```json
{
  "EC": 0,
  "EM": "Tour package created successfully",
  "package": {
    "package_id": "123e4567-e89b-12d3-a456-426614174000",
    "package_name": "Tour Đà Lạt 3N2Đ",
    "destination": "Đà Lạt",
    "price": 2500000.0,
    "available_slots": 20,
    "created_at": "2025-11-09T10:00:00.000000",
    "updated_at": "2025-11-09T10:00:00.000000",
    ...
  }
}
```

**Error Codes:**
- `0` = Success
- `1` = Failed to create tour package
- `2` = Validation error (invalid data)

---

### 4. Update Tour Package
**Method:** `PUT /{package_id}`

Cập nhật thông tin tour package. **Chỉ cần gửi các trường muốn cập nhật.**

**Path Parameters:**
- `package_id` (UUID, required): ID của tour package cần cập nhật

**Headers:**
```
Content-Type: application/json
```

**Request Body (All fields optional - chỉ gửi trường muốn update):**
```json
{
  "price": 2800000,
  "available_slots": 15,
  "is_active": true
}
```

**Example - Update nhiều trường:**
```json
{
  "package_name": "Tour Đà Lạt 3N2Đ [UPDATED]",
  "price": 2800000,
  "available_slots": 15,
  "start_date": "2024-12-15",
  "end_date": "2024-12-17",
  "includes": [
    "Khách sạn 5 sao",
    "Ăn 3 bữa/ngày cao cấp",
    "Hướng dẫn viên tiếng Anh"
  ],
  "is_active": true
}
```

**Example - Update itinerary:**
```json
{
  "itinerary": {
    "day1": {
      "title": "Ngày 1 - UPDATED",
      "morning": "Nội dung mới...",
      "afternoon": "Nội dung mới...",
      "evening": "Nội dung mới..."
    }
  }
}
```

**Response:**
```json
{
  "EC": 0,
  "EM": "Tour package updated successfully",
  "package": {
    "package_id": "123e4567-e89b-12d3-a456-426614174000",
    "package_name": "Tour Đà Lạt 3N2Đ",
    "price": 2800000.0,
    "available_slots": 15,
    "is_active": true,
    "updated_at": "2025-11-09T10:30:00.000000",
    ...
  }
}
```

**Error Codes:**
- `0` = Success
- `1` = Tour package not found / No fields to update
- `2` = Failed to update
- `3` = Error updating package

**💡 Tips:**
- Không cần gửi tất cả các trường, chỉ gửi những trường muốn thay đổi
- Ngày tháng phải dùng format: `YYYY-MM-DD` (ví dụ: `2024-12-15`)
- Số không dùng dấu nháy kép: `2800000` (không phải `"2800000"`)
- Boolean: `true`/`false` (chữ thường, không có dấu nháy kép)

---

### 5. Delete Tour Package
**Method:** `DELETE /{package_id}`

Xóa một tour package khỏi hệ thống.

**Path Parameters:**
- `package_id` (UUID, required): ID của tour package cần xóa

**Example Request:**
```
DELETE /api/v1/tour-packages/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "EC": 0,
  "EM": "Tour package deleted successfully"
}
```

**Error Codes:**
- `0` = Success
- `1` = Tour package not found
- `2` = Error deleting package

---

## 📝 Common Notes

### Date Format
Tất cả các trường ngày tháng phải dùng format ISO 8601:
- Request: `"2024-12-01"` (YYYY-MM-DD)
- Response: `"2025-11-09T10:00:00.000000"` (ISO datetime)

### UUID Format
Package ID là UUID v4:
- Example: `fe5d44aa-5435-4110-a2d2-947f716f0ebc`

### Price
Giá tour tính bằng VNĐ (Vietnamese Dong):
- `3200000` = 3,200,000 VNĐ = ~$130 USD

### Response Structure
Tất cả response đều có cấu trúc:
```json
{
  "EC": 0,           // Error Code (0 = success)
  "EM": "message",   // Error/Success Message
  "data": {...}      // Response data (tùy endpoint)
}
```

---

## 🧪 Testing with cURL

### Get all packages:
```bash
curl -X GET "http://localhost:8000/api/v1/tour-packages/"
```

### Get package by ID:
```bash
curl -X GET "http://localhost:8000/api/v1/tour-packages/fe5d44aa-5435-4110-a2d2-947f716f0ebc"
```

### Create package:
```bash
curl -X POST "http://localhost:8000/api/v1/tour-packages/" \
  -H "Content-Type: application/json" \
  -d '{
    "package_name": "Tour Test",
    "destination": "Hà Nội",
    "description": "Test tour",
    "duration_days": 3,
    "price": 1000000,
    "available_slots": 20,
    "departure_location": "TP.HCM",
    "start_date": "2024-12-01",
    "end_date": "2024-12-03",
    "includes": ["Hotel", "Meals"],
    "is_active": true
  }'
```

### Update package:
```bash
curl -X PUT "http://localhost:8000/api/v1/tour-packages/PACKAGE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "price": 1200000,
    "available_slots": 15
  }'
```

### Delete package:
```bash
curl -X DELETE "http://localhost:8000/api/v1/tour-packages/PACKAGE_ID"
```