import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import jwt

# Без лимита 72 байта (в отличие от bcrypt)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_me")
JWT_ALG = "HS256"
JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "43200"))  # 30 дней

def _clean_password(p: str) -> str:
    # убираем невидимые пробелы/переносы, которые иногда прилетают из UI
    return (p or "").strip()

def hash_password(password: str) -> str:
    return pwd_context.hash(_clean_password(password))

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(_clean_password(password), password_hash)

def create_access_token(sub: str, role: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MIN)
    payload = {"sub": sub, "role": role, "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
