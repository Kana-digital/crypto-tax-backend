#!/usr/bin/env python3
"""
テストメール送信スクリプト

Resend API を使って3種類のテストメールを送信する。
使い方:
  python send_test_emails.py

必要な環境変数（未設定の場合はデフォルト値を使用）:
  RESEND_API_KEY  - Resend APIキー
  EMAIL_FROM      - 送信元
"""

import json
import urllib.request
import sys
import os

# 設定
API_KEY = os.environ.get("RESEND_API_KEY", "re_YrNqmJjD_KngCTxgknagEKk7SmJtAJEnz")
FROM_EMAIL = os.environ.get("EMAIL_FROM", "暗号資産損益計算ツール <noreply@crypto-zei.jp>")
TO_EMAIL = os.environ.get("TEST_EMAIL_TO", "9kana6@gmail.com")
FRONTEND_URL = "https://crypto-tax-frontend.vercel.app"


def send_email(to: str, subject: str, html: str) -> dict:
    """Resend API でメール送信"""
    data = json.dumps({
        "from": FROM_EMAIL,
        "to": [to],
        "subject": subject,
        "html": html,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))


# ── テンプレート ──────────────────────────────

def welcome_html():
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:560px;margin:0 auto;padding:40px 20px;">
  <div style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
    <div style="text-align:center;margin-bottom:24px;"><div style="display:inline-block;width:48px;height:48px;line-height:48px;background:#2563eb;color:white;border-radius:12px;font-size:24px;font-weight:bold;">₿</div></div>
    <h1 style="color:#0f172a;font-size:20px;text-align:center;">ご登録ありがとうございます！</h1>
    <p style="color:#475569;font-size:14px;line-height:1.7;">暗号資産損益計算ツールへようこそ。アカウントの登録が完了しました。</p>
    <p style="color:#475569;font-size:14px;line-height:1.7;">さっそく取引履歴CSVをアップロードして、損益計算を始めましょう。</p>
    <div style="text-align:center;"><a href="{FRONTEND_URL}" style="display:inline-block;background:#2563eb;color:#fff!important;text-decoration:none;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:600;">損益計算をはじめる</a></div>
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
    <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:16px;">
      <p style="margin:0 0 8px;font-weight:600;color:#92400e;"><span style="background:linear-gradient(135deg,#fef3c7,#fde68a);color:#92400e;border:1px solid #fbbf24;border-radius:20px;padding:2px 10px;font-size:11px;">Premium</span> プレミアムプランのご案内</p>
      <p style="margin:0;font-size:14px;color:#475569;">年間たったの <strong style="font-size:28px;color:#0f172a;">980</strong><span style="color:#64748b;">円</span> で、広告なし・PDF出力・CSV出力が使い放題！</p>
    </div>
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
    <p style="font-size:12px;color:#94a3b8;">対応取引所：Coincheck・SBI VC Trade・bitbank</p>
  </div>
  <div style="text-align:center;margin-top:24px;"><p style="color:#94a3b8;font-size:12px;">暗号資産損益計算ツール</p></div>
</div>
</body></html>"""


def upgrade_html():
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:560px;margin:0 auto;padding:40px 20px;">
  <div style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
    <div style="text-align:center;margin-bottom:24px;"><div style="display:inline-block;width:48px;height:48px;line-height:48px;background:#2563eb;color:white;border-radius:12px;font-size:24px;font-weight:bold;">₿</div></div>
    <h1 style="color:#0f172a;font-size:20px;text-align:center;">プレミアムプランで<br>もっと快適に使いませんか？</h1>
    <p style="color:#475569;font-size:14px;line-height:1.7;">いつも暗号資産損益計算ツールをご利用いただきありがとうございます。</p>
    <div style="background:#fffbeb;border:2px solid #f59e0b;border-radius:12px;padding:20px;margin:20px 0;">
      <div style="text-align:center;margin-bottom:12px;"><span style="background:linear-gradient(135deg,#fef3c7,#fde68a);color:#92400e;border:1px solid #fbbf24;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;">Premium</span></div>
      <div style="text-align:center;margin-bottom:16px;"><span style="font-size:28px;font-weight:800;color:#0f172a;">980</span><span style="font-size:14px;color:#64748b;">円 / 年</span><p style="margin:4px 0 0;font-size:12px;color:#92400e;">一括払い（1年間有効）</p></div>
      <div style="padding:0;margin:16px 0;">
        <div style="padding:8px 0;color:#334155;font-size:14px;border-bottom:1px solid #f1f5f9;">🚫 <strong>広告の完全非表示</strong><br><span style="font-size:12px;color:#64748b;">CSV取り込み時のカウントダウン広告がなくなります</span></div>
        <div style="padding:8px 0;color:#334155;font-size:14px;border-bottom:1px solid #f1f5f9;">📄 <strong>損益計算書のPDF出力</strong><br><span style="font-size:12px;color:#64748b;">確定申告の参考資料としてダウンロードできます</span></div>
        <div style="padding:8px 0;color:#334155;font-size:14px;">📥 <strong>取引データのCSV出力</strong><br><span style="font-size:12px;color:#64748b;">取引履歴を整理されたCSVでエクスポートできます</span></div>
      </div>
    </div>
    <div style="text-align:center;"><a href="{FRONTEND_URL}" style="display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff!important;text-decoration:none;padding:14px 40px;border-radius:8px;font-size:14px;font-weight:600;">プレミアムプランにアップグレード</a></div>
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
    <div style="background:#eff6ff;border-radius:8px;padding:16px;">
      <p style="margin:0 0 8px;font-size:13px;font-weight:600;color:#475569;">無料プランとの比較</p>
      <table style="width:100%;border-collapse:collapse;font-size:13px;">
        <tr style="border-bottom:1px solid #e2e8f0;"><td style="padding:6px 0;color:#64748b;">機能</td><td style="padding:6px 8px;text-align:center;color:#64748b;">無料</td><td style="padding:6px 8px;text-align:center;color:#92400e;font-weight:600;">Premium</td></tr>
        <tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:6px 0;">損益計算</td><td style="padding:6px 8px;text-align:center;">✅</td><td style="padding:6px 8px;text-align:center;">✅</td></tr>
        <tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:6px 0;">広告</td><td style="padding:6px 8px;text-align:center;">あり</td><td style="padding:6px 8px;text-align:center;color:#16a34a;font-weight:600;">なし</td></tr>
        <tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:6px 0;">PDF出力</td><td style="padding:6px 8px;text-align:center;">❌</td><td style="padding:6px 8px;text-align:center;">✅</td></tr>
        <tr><td style="padding:6px 0;">CSV出力</td><td style="padding:6px 8px;text-align:center;">❌</td><td style="padding:6px 8px;text-align:center;">✅</td></tr>
      </table>
    </div>
  </div>
  <div style="text-align:center;margin-top:24px;"><p style="color:#94a3b8;font-size:12px;">暗号資産損益計算ツール</p><p style="color:#94a3b8;font-size:12px;">配信停止をご希望の場合はこのメールに返信してください。</p></div>
</div>
</body></html>"""


def payment_html():
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:560px;margin:0 auto;padding:40px 20px;">
  <div style="background:#fff;border-radius:12px;padding:32px;box-shadow:0 1px 3px rgba(0,0,0,.08);">
    <div style="text-align:center;margin-bottom:24px;"><div style="display:inline-block;width:48px;height:48px;line-height:48px;background:#2563eb;color:white;border-radius:12px;font-size:24px;font-weight:bold;">₿</div></div>
    <h1 style="color:#0f172a;font-size:20px;text-align:center;">🎉 プレミアムプランの<br>ご購入ありがとうございます！</h1>
    <p style="color:#475569;font-size:14px;line-height:1.7;">暗号資産損益計算ツールのプレミアムプランが有効になりました。以下のすべての機能がご利用いただけます。</p>
    <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:8px;padding:16px;margin:16px 0;">
      <div style="text-align:center;margin-bottom:8px;"><span style="background:linear-gradient(135deg,#fef3c7,#fde68a);color:#92400e;border:1px solid #fbbf24;border-radius:20px;padding:2px 10px;font-size:11px;font-weight:600;">Premium 有効</span></div>
      <div style="padding:8px 0;color:#334155;font-size:14px;border-bottom:1px solid #f1f5f9;">✅ 広告なしでストレスフリーに利用</div>
      <div style="padding:8px 0;color:#334155;font-size:14px;border-bottom:1px solid #f1f5f9;">✅ 損益計算書のPDF出力</div>
      <div style="padding:8px 0;color:#334155;font-size:14px;">✅ 取引データのCSV出力</div>
    </div>
    <div style="background:#eff6ff;border-radius:8px;padding:16px;margin:16px 0;">
      <p style="margin:0 0 8px;font-weight:600;color:#0f172a;font-size:14px;">ご利用明細</p>
      <table style="width:100%;font-size:14px;">
        <tr><td style="padding:4px 0;color:#64748b;">プラン</td><td style="padding:4px 0;text-align:right;color:#0f172a;font-weight:600;">プレミアムプラン</td></tr>
        <tr><td style="padding:4px 0;color:#64748b;">料金</td><td style="padding:4px 0;text-align:right;color:#0f172a;font-weight:600;">980円 / 年</td></tr>
        <tr><td style="padding:4px 0;color:#64748b;">お支払い方法</td><td style="padding:4px 0;text-align:right;color:#0f172a;">クレジットカード（Stripe）</td></tr>
        <tr><td style="padding:4px 0;color:#64748b;">有効期限</td><td style="padding:4px 0;text-align:right;color:#0f172a;">購入日から1年間</td></tr>
      </table>
    </div>
    <div style="text-align:center;"><a href="{FRONTEND_URL}" style="display:inline-block;background:#2563eb;color:#fff!important;text-decoration:none;padding:12px 28px;border-radius:8px;font-size:14px;font-weight:600;">さっそく使ってみる</a></div>
    <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
    <p style="font-size:12px;color:#94a3b8;">決済に関するお問い合わせはサポートチャット（画面右下の💬ボタン）からお気軽にどうぞ。解約はいつでも可能です。</p>
  </div>
  <div style="text-align:center;margin-top:24px;"><p style="color:#94a3b8;font-size:12px;">暗号資産損益計算ツール</p></div>
</div>
</body></html>"""


# ── メイン処理 ──────────────────────────────

EMAILS = [
    ("welcome",  "ご登録ありがとうございます - 暗号資産損益計算ツール",            welcome_html()),
    ("upgrade",  "【年間980円】広告なし＋PDF出力で、もっと快適に - 暗号資産損益計算ツール", upgrade_html()),
    ("payment",  "プレミアムプランへようこそ！ - 暗号資産損益計算ツール",            payment_html()),
]

if __name__ == "__main__":
    print(f"送信先: {TO_EMAIL}")
    print(f"送信元: {FROM_EMAIL}")
    print(f"API Key: {API_KEY[:10]}...")
    print("-" * 50)

    for name, subject, html in EMAILS:
        try:
            result = send_email(TO_EMAIL, subject, html)
            print(f"✅ {name}: 送信成功 (id: {result.get('id', 'N/A')})")
        except Exception as e:
            print(f"❌ {name}: 送信失敗 - {e}")

    print("-" * 50)
    print("完了！Gmailの受信ボックスを確認してください。")
