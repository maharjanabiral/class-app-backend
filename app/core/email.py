from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from app.core.config import settings  # your existing settings/env loader

# ---------------------------------------------------------------------------
# Connection config — reads from environment variables via your settings obj.
# Add these keys to your .env (see bottom of file for the full list).
# ---------------------------------------------------------------------------
mail_config = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,           # plain address: no-reply@classplus.dev
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME, # display name: ClassPlus
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

_mailer = FastMail(mail_config)


def _build_otp_html(otp: str, recipient_name: str = "there") -> str:
    """Inline HTML template — no external files needed."""
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
      <title>Your OTP Code</title>
    </head>
    <body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
        <tr>
          <td align="center">
            <table width="480" cellpadding="0" cellspacing="0"
                   style="background:#ffffff;border-radius:10px;
                          box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden;">

              <!-- Header -->
              <tr>
                <td style="background:#4f46e5;padding:28px 32px;">
                  <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700;
                              letter-spacing:.5px;">ClassPlus</h1>
                </td>
              </tr>

              <!-- Body -->
              <tr>
                <td style="padding:36px 32px 24px;">
                  <p style="margin:0 0 12px;font-size:16px;color:#374151;">
                    Hi {recipient_name},
                  </p>
                  <p style="margin:0 0 28px;font-size:15px;color:#6b7280;line-height:1.6;">
                    Use the one-time code below to complete your login.
                    It expires in&nbsp;<strong>5&nbsp;minutes</strong>.
                  </p>

                  <!-- OTP box -->
                  <div style="text-align:center;margin:0 0 28px;">
                    <span style="display:inline-block;padding:16px 40px;
                                 background:#f0f0ff;border:2px dashed #4f46e5;
                                 border-radius:8px;font-size:36px;font-weight:800;
                                 letter-spacing:12px;color:#4f46e5;">
                      {otp}
                    </span>
                  </div>

                  <p style="margin:0;font-size:13px;color:#9ca3af;line-height:1.6;">
                    If you didn't request this code, you can safely ignore this email.
                    Someone may have entered your email by mistake.
                  </p>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding:16px 32px 28px;border-top:1px solid #f3f4f6;">
                  <p style="margin:0;font-size:12px;color:#d1d5db;text-align:center;">
                    &copy; 2025 ClassPlus. All rights reserved.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """


async def send_otp_email(email: EmailStr, otp: str, name: str = "there") -> None:
    """
    Send an OTP email asynchronously.

    Args:
        email:  Recipient address.
        otp:    The plain-text OTP string (e.g. "482931").
        name:   Recipient's display name for the greeting (optional).

    Raises:
        Exception: Propagates any SMTP/connection error so the caller can
                   convert it into an appropriate HTTP response.
    """
    message = MessageSchema(
        subject="Your ClassPlus login code",
        recipients=[email],
        body=_build_otp_html(otp, name),
        subtype=MessageType.html,
    )
    await _mailer.send_message(message)
