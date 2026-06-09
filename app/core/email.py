from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from app.core.config import settings

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
)

async def send_otp_email(email: str, name: str, otp: str):
    message = MessageSchema(
        subject="ClassPlus - Your Login OTP",
        recipients=[email],
        body=f"Hi {name},\n\nYour OTP is: {otp}\n\nValid for 5 minutes. Do not share it.",
        subtype=MessageType.plain
    )
    fm = FastMail(conf)
    await fm.send_message(message)
