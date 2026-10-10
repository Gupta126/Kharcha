from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.settings import settings
from app.core.errors import UnauthorizedError, ForbiddenError
from app.db.session import get_db

router = APIRouter(prefix="/v1/auth", tags=["auth"])
security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str

class LoginResponse(BaseModel):
    token: str
    role: str
    employee_id: str

@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT id, role FROM employees WHERE email = :email"),
        {"email": request.email}
    )
    row = result.fetchone()
    
    if not row:
        raise UnauthorizedError("Unknown email")
        
    employee_id = str(row[0])
    role = row[1]
    
    # Generate token (12 hours) per SPEC §1
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=12)
    payload = {
        "sub": employee_id,
        "role": role,
        "exp": exp,
        "iat": now,
    }
    
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")
    
    return LoginResponse(
        token=token,
        role=role,
        employee_id=employee_id
    )


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token")


def require_role(allowed_roles: list[str]):
    async def role_checker(current_user: Dict[str, Any] = Depends(get_current_user)):
        user_role = current_user.get("role")
        if user_role not in allowed_roles:
            raise ForbiddenError("You do not have permission to access this resource")
        return current_user
    return role_checker

async def require_token(current_user: Dict[str, Any] = Depends(get_current_user)):
    return current_user
