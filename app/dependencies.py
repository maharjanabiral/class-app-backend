from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.user import User, Role
from app.core.security import decode_token

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.id == int(payload["sub"])))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
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
