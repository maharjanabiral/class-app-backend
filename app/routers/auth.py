from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserRegister, UserLogin, OTPVerify, TokenResponse, UserOut
from app.core.security import hash_password, verify_password, create_access_token, create_remember_token, decode_token
from app.core.otp import generate_otp, verify_otp
from app.core.email import send_otp_email
from app.dependencies import get_current_user

from datetime import datetime, timedelta, timezone

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserOut)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# @router.post("/login")
# async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.email == payload.email))
#     user = result.scalar_one_or_none()
#
#     if not user or not verify_password(payload.password, user.hashed_password):
#         raise HTTPException(status_code=401, detail="Invalid credentials")
#
#     otp = generate_otp(payload.email)
#
#     try:
#         await send_otp_email(email=payload.email, otp=otp, name=user.name)
#     except Exception as exc:
#         # Don't leak SMTP internals to the client
#         raise HTTPException(
#             status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
#             detail="Could not send OTP email. Please try again later.",
#         ) from exc
#
#     return {"message": "OTP sent to your email"}


@router.post("/login")
async def login(request: Request, payload: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()

    print("cookies received:", request.cookies)

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Valid 30-day token in cookie → skip OTP
    token = request.cookies.get("token")
    print("token from cookie:", token)
    if token:
        payload_data = decode_token(token)
        if payload_data and payload_data.get("sub") == str(user.id):
            return {"message": "Login successful", "skip_otp": True}

    # No valid token → send OTP
    otp = generate_otp(payload.email)
    try:
        await send_otp_email(email=payload.email, otp=otp, name=user.name)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Could not send OTP email.") from exc

    return {"message": "OTP sent to your email", "skip_otp": False}

@router.post("/verify-otp")
async def verify_otp_route(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_otp(payload.email, payload.otp):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    print(f"--------------------------------Remember ME: {payload.remember_me}---------------------------")

    expires_days = 30 if payload.remember_me else 1
    token = create_access_token({"sub": str(user.id), "role": user.role}, expires_days=expires_days)

    response = JSONResponse(content={"message": "Login successful"})
    response.set_cookie("token", token, httponly=True, samesite="lax",
                        path="/",secure=False, max_age=60 * 60 * 24 * expires_days)
    return response
# @router.post("/verify-otp", response_model=TokenResponse)
# async def verify_otp_route(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.email == payload.email))
#     user = result.scalar_one_or_none()
#
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     if not verify_otp(payload.email, payload.otp):
#         raise HTTPException(status_code=400, detail="Invalid or expired OTP")
#
#     token = create_access_token({"sub": str(user.id), "role": user.role})
#
#     response = JSONResponse(content={"message": "Login successful", "access_token": token})
#     response.set_cookie(
#         key="token",
#         value=token,
#         httponly=True,
#         samesite="lax",
#         path="/",
#     )
#
#     return response



# @router.post("/verify-otp", response_model=TokenResponse)
# async def verify_otp_route(payload: OTPVerify, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.email == payload.email))
#     user = result.scalar_one_or_none()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#     if not verify_otp(payload.email, payload.otp):
#         raise HTTPException(status_code=400, detail="Invalid or expired OTP")
#
#     # Short-lived JWT (1 day)
#     token = create_access_token({"sub": str(user.id), "role": user.role})
#
#     # Long-lived remember token (30 days)
#     remember_token = create_remember_token()
#     user.remember_token = remember_token
#     user.remember_token_expiry = datetime.now(timezone.utc) + timedelta(days=30)
#     await db.commit()
#
#     response = JSONResponse(content={"message": "Login successful", "access_token": token})
#     response.set_cookie("token", token, httponly=True, samesite="lax", path="/",
#                         max_age=86400)                        # 1 day
#     response.set_cookie("remember_token", remember_token, httponly=True, samesite="lax",
#                         path="/", max_age=60 * 60 * 24 * 30) # 30 days
#     return response

@router.get("/me")
async def me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "role": current_user.role}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("token", path="/")
    return {"message": "Logged out"}
