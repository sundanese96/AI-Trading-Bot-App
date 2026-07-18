import os
import uuid
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from backend.config import BASE_DIR, DASHBOARD_USERNAME, DASHBOARD_PASSWORD
from backend.core.logger import logger

router = APIRouter()

# Persistent Session Management
SESSION_FILE = str(BASE_DIR / ".session_token")

def get_active_session_id():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Error reading session token: {e}")
            return None
    return None

def set_active_session_id(session_id: str):
    try:
        with open(SESSION_FILE, "w") as f:
            f.write(session_id)
    except Exception as e:
        logger.error(f"Error saving session token: {e}")

def clear_active_session_id():
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except Exception as e:
            logger.error(f"Error removing session token: {e}")

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/api/login")
async def login(data: LoginRequest, response: Response):
    if data.username == DASHBOARD_USERNAME and data.password == DASHBOARD_PASSWORD:
        session_id = uuid.uuid4().hex
        set_active_session_id(session_id)
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=3600 * 24 * 7, # 7 days
            path="/"
        )
        logger.info(f"User {data.username} logged in successfully.")
        return {"success": True}
    else:
        logger.warning(f"Failed login attempt for user: {data.username}")
        raise HTTPException(status_code=400, detail="Username atau password salah")

@router.get("/api/auth/status")
async def auth_status(request: Request):
    session_id = request.cookies.get("session_id")
    active_id = get_active_session_id()
    if session_id and session_id == active_id:
        return {"authenticated": True}
    return {"authenticated": False}

@router.post("/api/logout")
async def logout(response: Response):
    clear_active_session_id()
    response.delete_cookie(key="session_id", path="/")
    logger.info("User logged out successfully.")
    return {"success": True}
