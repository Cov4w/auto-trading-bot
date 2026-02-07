# Login System Setup Guide

This guide will help you set up and use the authentication system for the Trading Bot application.

## Overview

The login system includes:
- **JWT-based authentication** - Secure token-based authentication
- **User registration** - New users can create accounts
- **Password hashing** - Bcrypt password security
- **Protected routes** - All bot endpoints require authentication
- **Session management** - Persistent login with localStorage
- **Beautiful UI** - Modern login/register interface

## Backend Components

### 1. Database (`backend/core/database.py`)
- SQLite database for user management
- User table with username, email, hashed password
- Admin and active status flags

### 2. Authentication (`backend/core/auth.py`)
- JWT token generation and validation
- Password hashing with bcrypt
- Token expiration (24 hours by default)

### 3. API Endpoints (`backend/routers/auth.py`)
- `POST /api/auth/register` - Create new user account
- `POST /api/auth/login` - Login with username/password
- `POST /api/auth/login/json` - Alternative JSON login
- `GET /api/auth/me` - Get current user profile
- `GET /api/auth/verify` - Verify token validity

### 4. Protected Routes
All bot and data endpoints now require authentication:
- `/api/bot/*` - Bot control endpoints
- `/api/data/*` - Data retrieval endpoints

## Frontend Components

### 1. Auth Context (`frontend/src/contexts/AuthContext.tsx`)
- Global authentication state management
- Login/logout functions
- Token persistence with localStorage
- Axios interceptor for automatic token inclusion

### 2. Login Page (`frontend/src/pages/Login.tsx`)
- Beautiful gradient design
- Login/Register tabs
- Form validation
- Error handling

### 3. Protected Routes (`frontend/src/components/ProtectedRoute.tsx`)
- Automatic redirect to login for unauthenticated users
- Loading state while checking authentication

### 4. Dashboard Integration
- User info display in header
- Logout button

## Installation & Setup

### Step 1: Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `python-jose[cryptography]` - JWT token handling
- `passlib[bcrypt]` - Password hashing
- `pydantic[email]` - Email validation

### Step 2: Create Admin User

Run the admin creation script:

```bash
cd backend
python create_admin.py
```

Follow the prompts to create your first admin user:
- Username
- Email
- Password (min 6 characters)
- Full Name (optional)

### Step 3: Start Backend Server

```bash
cd backend
python main.py
```

The server will start on `http://localhost:8000`

### Step 4: Install Frontend Dependencies (if needed)

```bash
cd frontend
npm install
```

### Step 5: Start Frontend

```bash
cd frontend
npm run dev
```

The frontend will start on `http://localhost:3000`

## Usage

### For Users

1. **First Time Setup**
   - Navigate to `http://localhost:3000`
   - Click "Register here" on the login page
   - Fill in username, email, password
   - Click "Register"

2. **Logging In**
   - Enter your username and password
   - Click "Login"
   - You'll be redirected to the Dashboard

3. **Logging Out**
   - Click the "Logout" button in the top-right corner of the Dashboard

### For Developers

#### Making Authenticated API Calls

The frontend automatically includes the JWT token in all requests via axios interceptors. In the backend, protect routes by adding the `current_user` dependency:

```python
from routers.auth import get_current_user
from models.schemas import User

@router.get("/protected-endpoint")
async def protected_route(current_user: User = Depends(get_current_user)):
    # Only authenticated users can access this
    return {"message": f"Hello {current_user.username}"}
```

#### Token Storage

Tokens are stored in localStorage:
- Key: `token` - JWT access token
- Key: `user` - User information (JSON)

#### Token Validation

Tokens are valid for 24 hours by default. Change this in `backend/core/auth.py`:

```python
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
```

## Security Configuration

### Important: Change Secret Key

⚠️ **CRITICAL**: Before deploying to production, change the JWT secret key in `backend/core/auth.py`:

```python
SECRET_KEY = "your-secret-key-change-this-in-production-use-env-variable"
```

Recommended approach:
1. Generate a strong secret key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Store it in an environment variable:
   ```bash
   export JWT_SECRET_KEY="your-generated-secret-key"
   ```

3. Update code to use environment variable:
   ```python
   import os
   SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-dev-key")
   ```

### CORS Configuration

The backend allows CORS from:
- `http://localhost:3000` - React Dev Server
- `http://localhost:5173` - Vite Dev Server
- `http://localhost:8080` - Generic local server

Update `backend/main.py` to add production URLs:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://yourdomain.com",  # Add your production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Test the authentication endpoints directly from the Swagger UI.

## Troubleshooting

### Backend Issues

**Problem**: Import errors after installing dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall
```

**Problem**: Database not found
- The database is auto-created in `data/users.db`
- Make sure the `data/` directory exists and has write permissions

**Problem**: Token validation fails
- Check that the secret key matches between token creation and validation
- Verify token hasn't expired (default 24 hours)

### Frontend Issues

**Problem**: Login page not showing
- Check that `AuthProvider` wraps your app in `App.tsx`
- Verify `ProtectedRoute` is wrapping the Dashboard

**Problem**: 401 Unauthorized on API calls
- Check that token is being stored in localStorage
- Verify axios interceptor is setting Authorization header
- Check token hasn't expired

**Problem**: CORS errors
- Ensure backend CORS middleware includes your frontend URL
- Restart backend server after changing CORS settings

## Database Management

### View Users

```bash
cd backend
python -c "from core.database import user_db; import json; print(json.dumps(user_db.list_users(), indent=2))"
```

### Reset Database

```bash
rm data/users.db
python create_admin.py
```

### Make User Admin

```python
from core.database import user_db
import sqlite3

with sqlite3.connect('data/users.db') as conn:
    conn.execute("UPDATE users SET is_admin = 1 WHERE username = 'your_username'")
    conn.commit()
```

## Next Steps

1. **Add Password Reset** - Implement email-based password reset
2. **Add Email Verification** - Verify emails on registration
3. **Add User Roles** - Implement role-based access control
4. **Add Session Management** - Track active sessions
5. **Add 2FA** - Add two-factor authentication
6. **Add Rate Limiting** - Prevent brute force attacks
7. **Add Audit Logging** - Log all authentication events

## File Structure

```
backend/
├── core/
│   ├── database.py          # User database management
│   └── auth.py              # JWT and password utilities
├── routers/
│   ├── auth.py              # Authentication endpoints
│   ├── bot.py               # Protected bot endpoints
│   └── data.py              # Protected data endpoints
├── models/
│   └── schemas.py           # Pydantic models (User, Token, etc.)
├── create_admin.py          # Admin user creation script
└── main.py                  # FastAPI app with auth router

frontend/
├── src/
│   ├── contexts/
│   │   └── AuthContext.tsx  # Auth state management
│   ├── components/
│   │   └── ProtectedRoute.tsx  # Route protection
│   ├── pages/
│   │   ├── Login.tsx        # Login/Register page
│   │   └── Dashboard.tsx    # Protected dashboard
│   └── styles/
│       ├── login.css        # Login page styles
│       └── dashboard.css    # Dashboard styles (logout button)
```

## Support

For issues or questions:
1. Check this documentation
2. Review the code comments
3. Check API docs at `/docs`
4. Open an issue in the repository
