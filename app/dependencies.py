from fastapi import Depends, HTTPException, status, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.user import User, Role
from app.core.security import decode_token, create_access_token
from datetime import datetime, timezone

# async def get_current_user(
#     request: Request,
#     db: AsyncSession = Depends(get_db)
# ) -> User:
#     token = request.cookies.get("token")
#     if not token:
#         raise HTTPException(status_code=401, detail="Not authenticated")
#     payload = decode_token(token)
#     if not payload:
#         raise HTTPException(status_code=401, detail="Invalid or expired token")
#     result = await db.execute(select(User).where(User.id == int(payload["sub"])))
#     user = result.scalar_one_or_none()
#     if not user:
#         raise HTTPException(status_code=401, detail="User not found")
#     return user
async def get_current_user(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> User:
    user = None

    # 1. Try short-lived JWT first (your original logic)
    token = request.cookies.get("token")
    if token:
        payload = decode_token(token)
        if payload:
            result = await db.execute(select(User).where(User.id == int(payload["sub"])))
            user = result.scalar_one_or_none()

    # 2. JWT missing/expired — fall back to remember token
    if not user:
        remember_token = request.cookies.get("remember_token")
        if remember_token:
            result = await db.execute(
                select(User).where(User.remember_token == remember_token)
            )
            user = result.scalar_one_or_none()

            if user:
                if user.remember_token_expiry < datetime.now(timezone.utc):
                    # Expired — wipe it
                    user.remember_token = None
                    user.remember_token_expiry = None
                    await db.commit()
                    user = None
                else:
                    # Valid — silently reissue a fresh JWT
                    new_token = create_access_token({"sub": str(user.id), "role": user.role})
                    response.set_cookie("token", new_token, httponly=True,
                                        samesite="lax", path="/", max_age=86400)

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user

def require_role(*roles: Role):
    async def checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access forbidden")
        return current_user
    return checker

get_current_student = require_role(Role.student)
get_current_teacher = require_role(Role.teacher)
get_current_admin = require_role(Role.admin)
get_current_staff = require_role(Role.admin, Role.teacher)
