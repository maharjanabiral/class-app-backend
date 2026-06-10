import bcrypt
from datetime import datetime, timedelta
# pyrefly: ignore [untyped-import]
from jose import JWTError, jwt
from app.core.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    # pyrefly: ignore [deprecated]
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        # pyrefly: ignore [bad-return]
        return None

def create_qr_token(session_id: int, expires_delta_seconds: int = 120) -> str:
    to_encode = {
        "sub": str(session_id),
        "type": "attendance_qr",
        # pyrefly: ignore [deprecated]
        "exp": datetime.utcnow() + timedelta(seconds=expires_delta_seconds)
    }
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_qr_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "attendance_qr":
            return None
        return payload
    except JWTError:
        return None

