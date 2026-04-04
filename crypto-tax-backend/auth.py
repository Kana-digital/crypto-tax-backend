"""
Supabase Auth 認証モジュール

JWTトークンをAuthorizationヘッダーから取得し、Supabase Auth で検証する。
FastAPI の Depends() として使用する。

使い方:
    from auth import get_current_user, get_optional_user, AuthUser

    @app.get("/protected")
    async def protected(user: AuthUser = Depends(get_current_user)):
        return {"user_id": user.id}

    @app.get("/optional-auth")
    async def optional(user: AuthUser | None = Depends(get_optional_user)):
        if user:
            return {"user_id": user.id}
        return {"anonymous": True}
"""

import os
import jwt
from typing import Optional
from dataclasses import dataclass
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Supabase JWT シークレット
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

security = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    """認証済みユーザー情報"""
    id: str
    email: Optional[str] = None
    role: str = "authenticated"


def _decode_token(token: str) -> dict:
    """Supabase JWTトークンをデコード・検証する"""
    if not SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="認証機能が設定されていません。SUPABASE_JWT_SECRETを確認してください。"
        )
    try:
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="トークンの有効期限が切れています。再ログインしてください。")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="無効な認証トークンです。")


def _extract_user(payload: dict) -> AuthUser:
    """JWTペイロードからAuthUserを生成する"""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="トークンにユーザー情報がありません。")
    return AuthUser(
        id=user_id,
        email=payload.get("email"),
        role=payload.get("role", "authenticated"),
    )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthUser:
    """
    認証必須のエンドポイント用。
    Authorizationヘッダーがない場合は401を返す。
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="認証が必要です。ログインしてください。")
    payload = _decode_token(credentials.credentials)
    return _extract_user(payload)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[AuthUser]:
    """
    認証任意のエンドポイント用。
    トークンがあれば検証してユーザーを返す。なければNoneを返す。
    """
    if not credentials:
        return None
    try:
        payload = _decode_token(credentials.credentials)
        return _extract_user(payload)
    except HTTPException:
        return None
