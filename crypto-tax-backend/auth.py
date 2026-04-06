"""
Supabase Auth 認証モジュール

JWTトークンをAuthorizationヘッダーから取得し、Supabase Auth で検証する。
FastAPI の Depends() として使用する。

ES256 (ECC P-256) と HS256 (Legacy HMAC) の両方のJWT署名アルゴリズムに対応。
Supabase の JWKS エンドポイントから公開鍵を取得してES256トークンを検証する。

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
import httpx
import time
from typing import Optional
from dataclasses import dataclass
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient

# Supabase JWT シークレット (Legacy HS256 用)
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")

# Supabase URL から JWKS エンドポイントを構築
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json" if SUPABASE_URL else ""

# JWKS クライアント (ES256 公開鍵取得用)
_jwks_client: Optional[PyJWKClient] = None

security = HTTPBearer(auto_error=False)


def _get_jwks_client() -> Optional[PyJWKClient]:
    """JWKS クライアントをシングルトンで取得する"""
    global _jwks_client
    if _jwks_client is None and JWKS_URL:
        try:
            _jwks_client = PyJWKClient(JWKS_URL, cache_keys=True, lifespan=3600)
        except Exception:
            pass
    return _jwks_client


@dataclass
class AuthUser:
    """認証済みユーザー情報"""
    id: str
    email: Optional[str] = None
    role: str = "authenticated"


def _decode_token(token: str) -> dict:
    """Supabase JWTトークンをデコード・検証する (ES256 + HS256 対応)"""
    if not SUPABASE_JWT_SECRET and not JWKS_URL:
        raise HTTPException(
            status_code=503,
            detail="認証機能が設定されていません。SUPABASE_JWT_SECRETまたはSUPABASE_URLを確認してください。"
        )

    # まずトークンヘッダーを読んでアルゴリズムを確認
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.exceptions.DecodeError:
        raise HTTPException(status_code=401, detail="無効な認証トークンです。")

    alg = unverified_header.get("alg", "HS256")

    try:
        if alg == "ES256":
            # ES256: JWKS エンドポイントから公開鍵を取得して検証
            jwks_client = _get_jwks_client()
            if not jwks_client:
                raise HTTPException(
                    status_code=503,
                    detail="JWKS設定が不正です。SUPABASE_URLを確認してください。"
                )
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["ES256"],
                audience="authenticated",
            )
        else:
            # HS256: Legacy JWT Secret で検証
            if not SUPABASE_JWT_SECRET:
                raise HTTPException(
                    status_code=503,
                    detail="認証機能が設定されていません。SUPABASE_JWT_SECRETを確認してください。"
                )
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                audience="authenticated",
            )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="トークンの有効期限が切れています。再ログインしてください。")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"無効な認証トークンです。({str(e)[:50]})")


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
