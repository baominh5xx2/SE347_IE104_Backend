# Authentication API Documentation

## Overview

This authentication system provides user registration, login, and token verification endpoints using JWT (JSON Web Tokens) and bcrypt for password hashing.

## Architecture

### File Structure

```
app/v1/
├── api/
│   └── endpoints/
│       └── auth.py          # Authentication endpoints
├── schema/
│   └── auth_schema.py       # Pydantic schemas for request/response
├── services/
│   └── auth_service.py      # Business logic for authentication
└── core/
    ├── config.py            # JWT configuration
    └── supabase.py          # Database connection
```

## Database Schema

### Users Table

The authentication system uses the existing `users` table in Supabase with the following fields:

```sql
users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    phone_number VARCHAR(20),
    is_activate BOOLEAN DEFAULT TRUE,
    role_id UUID,
    login_type VARCHAR(20) DEFAULT 'TRADITIONAL',
    social_id VARCHAR(255),
    security_2fa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
)
```

## API Endpoints

### Base URL

```
http://localhost:8000/api/v1/auth
```

### 1. Register User

**Endpoint:** `POST /api/v1/auth/register`

**Request Body:**

```json
{
    "full_name": "Nguyen Van A",
    "email": "a.nguyen@example.com",
    "password": "password123",
    "phone_number": "0123456789"
}
```

**Success Response (200):**

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

**Error Response:**

```json
{
    "EC": 1,
    "EM": "Email already exists"
}
```

### 2. Login

**Endpoint:** `POST /api/v1/auth/login`

**Request Body:**

```json
{
    "email": "a.nguyen@example.com",
    "password": "password123"
}
```

**Success Response (200):**

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

**Error Responses:**

```json
// Wrong credentials
{
    "EC": 1,
    "EM": "Email/Password is incorrect"
}
```

### 3. Verify Token

**Endpoint:** `POST /api/v1/auth/verify-token`

**Request Body (Option 1):**

```json
{
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Request Header (Option 2):**

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Success Response (200):**

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

**Error Responses:**

```json
// Token expired
{
    "EC": 1,
    "EM": "Token has expired"
}

// Invalid token
{
    "EC": 2,
    "EM": "Token is invalid: ..."
}
```

## Error Codes (EC)

| Code | Description                                                     |
| ---- | --------------------------------------------------------------- |
| 0    | Success                                                         |
| 1    | General error (email exists, wrong credentials, token required) |
| 2    | Password mismatch or invalid token                              |
| 3    | Account not activated or verification error                     |
| 4    | Server error                                                    |

## Security Features

1. **Password Hashing:** Uses bcrypt with 10 salt rounds
2. **JWT Tokens:** HS256 algorithm with configurable expiration
3. **Token Verification:** Validates signature and expiration
4. **Account Activation:** Checks `is_activate` flag before login
5. **Login Type:** Supports TRADITIONAL login (email/password)

## Usage Examples

### URL Examples

**Register:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Nguyen Van A",
    "email": "a.nguyen@example.com",
    "password": "password123",
    "phone_number": "0123456789"
  }'
```

**Login:**

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "a.nguyen@example.com",
    "password": "password123"
  }'
```

**Verify Token (Body):**

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-token \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_jwt_token_here"
  }'
```

**Verify Token (Header):**

```bash
curl -X POST http://localhost:8000/api/v1/auth/verify-token \
  -H "Authorization: Bearer your_jwt_token_here"
```

## Notes

- Password minimum length: 6 characters
- JWT token expires after 1 day (configurable via `JWT_EXPIRE`)
- The system uses the existing Supabase `users` table
- No additional database tables are created
- Passwords are hashed using bcrypt before storage
- Never store or log plain text passwords
