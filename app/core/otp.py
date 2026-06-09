import pyotp
import time

# In production, store these secrets per-user in DB or Redis with TTL
# For now, a simple in-memory store
otp_store: dict = {}  # {email: {"secret": str, "timestamp": float}}

OTP_EXPIRY_SECONDS = 300  # 5 minutes

def generate_otp(email: str) -> str:
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret, interval=OTP_EXPIRY_SECONDS)
    otp = totp.now()
    otp_store[email] = {"secret": secret, "timestamp": time.time()}
    return otp

def verify_otp(email: str, otp: str) -> bool:
    record = otp_store.get(email)
    if not record:
        return False
    elapsed = time.time() - record["timestamp"]
    if elapsed > OTP_EXPIRY_SECONDS:
        del otp_store[email]
        return False
    totp = pyotp.TOTP(record["secret"], interval=OTP_EXPIRY_SECONDS)
    valid = totp.verify(otp)
    if valid:
        del otp_store[email]
    return valid
