import bcrypt
import secrets
from datetime import datetime, timedelta
# pyrefly: ignore [untyped-import]
from jose import JWTError, jwt
from app.core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def generate_default_password(name: str, login_id: str) -> str:
    """
    Generates a default password from the user's first name + login_id.
    Example: name='John Doe', login_id='STU001' → 'John@STU001'
    """
    first_name = name.strip().split()[0].capitalize()
    return f"{first_name}@{login_id}"


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(data: dict, expires_days: int | None = None) -> str:
    to_encode = data.copy()
    if expires_days:
        expire = datetime.utcnow() + timedelta(days=expires_days)
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        # pyrefly: ignore [bad-return]
        return None


def create_remember_token() -> str:
    return secrets.token_urlsafe(32)

