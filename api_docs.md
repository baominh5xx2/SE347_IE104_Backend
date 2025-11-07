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