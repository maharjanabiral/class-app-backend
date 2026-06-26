from os import getenv

from fastapi import WebSocket
from jose import JWTError, jwt
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dotenv import load_dotenv

load_dotenv()


SECRET_KEY = getenv("SECRET_KEY")
ALGORITHM = getenv("ALGORITHM")


async def get_websocket_user(
    websocket: WebSocket,
    db: AsyncSession,
):
    token = websocket.cookies.get("token")

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        result = await db.execute(
            select(User).where(User.id == int(user_id))
        )

        user = result.scalar_one_or_none()

        return user

    except JWTError as e:
        print("JWT ERROR:", e)
        return None

    except Exception as e:
        print("OTHER ERROR:", e)
        return None
