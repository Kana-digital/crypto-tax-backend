"""
メール送信サービス

Resend API を使用してトランザクションメールを送信する。
環境変数:
  RESEND_API_KEY  - Resend の API キー（https://resend.com で取得）
  EMAIL_FROM      - 送信元メールアドレス（デフォルト: onboarding@resend.dev）
  FRONTEND_URL    - フロントエンドURL（メール内リンク用）
"""

import os
import httpx

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "暗号資産損益計算ツール <onboarding@resend.dev>")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://crypto-tax-frontend.vercel.app")


async def send_email(to: str, subject: str, html: str) -> dict:
    """Resend API でメールを送信する"""
    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY が設定されていません。Render の環境変数に追加してください。")

    async with httpx.AsyncClient() as client:
        res = await client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": EMAIL_FROM,
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        res.raise_for_status()
        return res.json()
