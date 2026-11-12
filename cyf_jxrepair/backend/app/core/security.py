"""密码哈希与 JWT 令牌。

密码使用标准库 PBKDF2-HMAC-SHA256 + 随机盐，存储格式：
    pbkdf2_sha256$<迭代次数>$<盐hex>$<哈希hex>
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings
from app.core.exceptions import Unauthorized

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 120_000


def hash_password(raw: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), _ITERATIONS).hex()
    return f"{_ALGO}${_ITERATIONS}${salt}${digest}"


def verify_password(raw: str, stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$")
    except ValueError:
        return False
    if algo != _ALGO:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", raw.encode(), salt.encode(), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)  # 常量时间比较，防止时序攻击


def create_token(user_id: int, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> int:
    """解析令牌，返回用户 ID。过期或被篡改统一抛 401。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise Unauthorized("登录已过期，请重新登录") from exc
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise Unauthorized("登录凭证无效") from exc
