"""
認証ミドルウェア
================
APIキーベースの認証とJWTトークン認証を提供します。
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from backend.models.database import User, get_db

# JWT設定（本番ではシークレットキーを環境変数から読み込む）
import os
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def generate_api_key() -> str:
    """ランダムなAPIキーを生成します。"""
    return f"xm_{secrets.token_hex(32)}"


def hash_password(password: str) -> str:
    """パスワードをハッシュ化します。"""
    try:
        import bcrypt
        return bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")
    except ImportError:
        # bcryptがない場合はSHA-256（本番ではbcrypt推奨）
        return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, hashed: str) -> bool:
    """パスワードを検証します。"""
    try:
        import bcrypt
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed.encode("utf-8")
        )
    except ImportError:
        return hashlib.sha256(password.encode("utf-8")).hexdigest() == hashed


def create_jwt_token(user_id: int) -> str:
    """JWTトークンを生成します。"""
    try:
        import jwt
    except ImportError:
        raise ImportError("PyJWTパッケージが必要です: pip install PyJWT")

    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRE_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt_token(token: str) -> Optional[dict]:
    """JWTトークンをデコードします。"""
    try:
        import jwt
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None


async def get_current_user_by_api_key(
    x_api_key: str = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> User:
    """
    APIキーからユーザーを認証します。
    VPS上のPythonスクリプトからの呼び出し用。
    """
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="APIキーが必要です（X-API-Keyヘッダー）"
        )

    user = db.query(User).filter(
        User.api_key == x_api_key,
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なAPIキーです"
        )

    return user


async def get_current_user_by_jwt(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    JWTトークンからユーザーを認証します。
    Laravelダッシュボードからの呼び出し用。
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証トークンが必要です"
        )

    token = authorization.replace("Bearer ", "")
    payload = decode_jwt_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです"
        )

    user = db.query(User).filter(
        User.id == payload["user_id"],
        User.is_active == True
    ).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません"
        )

    return user
