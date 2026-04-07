"""
メールテンプレート

3種類のHTMLメールテンプレートを提供する:
  1. welcome_email       - 新規登録の確認・ウェルカムメール
  2. upgrade_email       - 無料ユーザーへのアップグレード案内メール
  3. payment_success_email - 決済完了・ありがとうメール
"""

import os

FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://crypto-tax-frontend.vercel.app")

# ========================================
# 共通スタイル（インライン化のベース）
# ========================================
_BASE_STYLE = """
<style>
  body { margin: 0; padding: 0; background: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
  .container { max-width: 560px; margin: 0 auto; padding: 40px 20px; }
  .card { background: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
  .logo { text-align: center; margin-bottom: 24px; }
  .logo-icon { display: inline-block; width: 48px; height: 48px; line-height: 48px; background: #2563eb; color: white; border-radius: 12px; font-size: 24px; font-weight: bold; text-align: center; }
  h1 { color: #0f172a; font-size: 20px; margin: 0 0 16px; text-align: center; }
  p { color: #475569; font-size: 14px; line-height: 1.7; margin: 0 0 12px; }
  .btn { display: inline-block; background: #2563eb; color: #ffffff !important; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 600; margin: 16px 0; }
  .btn:hover { background: #1d4ed8; }
  .btn-gold { background: linear-gradient(135deg, #f59e0b, #d97706); }
  .btn-gold:hover { background: #b45309; }
  .feature-list { padding: 0; margin: 16px 0; list-style: none; }
  .feature-list li { padding: 8px 0; color: #334155; font-size: 14px; border-bottom: 1px solid #f1f5f9; }
  .feature-list li:last-child { border-bottom: none; }
  .highlight { background: #eff6ff; border-radius: 8px; padding: 16px; margin: 16px 0; }
  .highlight-gold { background: #fffbeb; border: 1px solid #fde68a; }
  .price { font-size: 28px; font-weight: 800; color: #0f172a; }
  .price-unit { font-size: 14px; color: #64748b; font-weight: 400; }
  .footer { text-align: center; margin-top: 24px; }
  .footer p { color: #94a3b8; font-size: 12px; }
  .footer a { color: #64748b; text-decoration: underline; }
  .divider { border: none; border-top: 1px solid #e2e8f0; margin: 20px 0; }
  .badge { display: inline-block; background: #f0fdf4; color: #16a34a; border: 1px solid #86efac; border-radius: 20px; padding: 2px 10px; font-size: 11px; font-weight: 600; }
  .badge-premium { background: linear-gradient(135deg, #fef3c7, #fde68a); color: #92400e; border-color: #fbbf24; }
</style>
"""


def welcome_email(user_email: str) -> tuple[str, str]:
    """
    新規登録ウェルカムメール
    Returns: (subject, html)
    """
    subject = "ご登録ありがとうございます - 暗号資産損益計算ツール"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">{_BASE_STYLE}</head>
<body>
<div class="container">
  <div class="card">
    <div class="logo"><div class="logo-icon">₿</div></div>
    <h1>ご登録ありがとうございます！</h1>
    <p>暗号資産損益計算ツールへようこそ。アカウントの登録が完了しました。</p>
    <p>さっそく取引履歴CSVをアップロードして、損益計算を始めましょう。</p>

    <div style="text-align: center;">
      <a href="{FRONTEND_URL}" class="btn">損益計算をはじめる</a>
    </div>

    <hr class="divider">

    <div class="highlight highlight-gold">
      <p style="margin: 0 0 8px; font-weight: 600; color: #92400e;">
        <span class="badge badge-premium">Premium</span> プレミアムプランのご案内
      </p>
      <p style="margin: 0 0 12px;">年間たったの <span class="price">980</span><span class="price-unit">円</span> で、もっと便利に使えます。</p>
      <ul class="feature-list" style="margin: 8px 0;">
        <li>✅ 広告なしでストレスフリー</li>
        <li>✅ 損益計算書のPDF出力</li>
        <li>✅ 取引データのCSV出力</li>
      </ul>
      <div style="text-align: center;">
        <a href="{FRONTEND_URL}" class="btn btn-gold">プレミアムプランを見る</a>
      </div>
    </div>

    <hr class="divider">
    <p style="font-size: 12px; color: #94a3b8;">対応取引所：Coincheck・SBI VC Trade・bitbank</p>
  </div>

  <div class="footer">
    <p>暗号資産損益計算ツール</p>
    <p><a href="{FRONTEND_URL}">crypto-tax-frontend.vercel.app</a></p>
    <p>このメールは {user_email} 宛に送信されています。</p>
  </div>
</div>
</body>
</html>"""
    return subject, html


def upgrade_email(user_email: str) -> tuple[str, str]:
    """
    無料ユーザー向けアップグレード案内メール
    Returns: (subject, html)
    """
    subject = "【年間980円】広告なし＋PDF出力で、もっと快適に - 暗号資産損益計算ツール"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">{_BASE_STYLE}</head>
<body>
<div class="container">
  <div class="card">
    <div class="logo"><div class="logo-icon">₿</div></div>
    <h1>プレミアムプランで<br>もっと快適に使いませんか？</h1>

    <p>いつも暗号資産損益計算ツールをご利用いただきありがとうございます。</p>
    <p>現在の無料プランでも損益計算は可能ですが、プレミアムプランにアップグレードすると以下の機能が使えるようになります。</p>

    <div class="highlight highlight-gold">
      <div style="text-align: center; margin-bottom: 12px;">
        <span class="badge badge-premium">Premium</span>
      </div>
      <div style="text-align: center; margin-bottom: 16px;">
        <span class="price">980</span><span class="price-unit">円 / 年</span>
        <p style="margin: 4px 0 0; font-size: 12px; color: #92400e;">一括払い（1年間有効）</p>
      </div>

      <ul class="feature-list">
        <li>🚫 <strong>広告の完全非表示</strong><br><span style="font-size: 12px; color: #64748b;">CSV取り込み時のカウントダウン広告がなくなります</span></li>
        <li>📄 <strong>損益計算書のPDF出力</strong><br><span style="font-size: 12px; color: #64748b;">確定申告の参考資料としてダウンロードできます</span></li>
        <li>📥 <strong>取引データのCSV出力</strong><br><span style="font-size: 12px; color: #64748b;">取引履歴を整理されたCSVでエクスポートできます</span></li>
      </ul>
    </div>

    <div style="text-align: center;">
      <a href="{FRONTEND_URL}" class="btn btn-gold">プレミアムプランにアップグレード</a>
    </div>

    <hr class="divider">

    <div class="highlight">
      <p style="margin: 0; font-size: 13px; color: #475569;">
        <strong>無料プランとの比較</strong>
      </p>
      <table style="width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px;">
        <tr style="border-bottom: 1px solid #e2e8f0;">
          <td style="padding: 6px 0; color: #64748b;">機能</td>
          <td style="padding: 6px 8px; text-align: center; color: #64748b;">無料</td>
          <td style="padding: 6px 8px; text-align: center; color: #92400e; font-weight: 600;">Premium</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 6px 0;">損益計算</td>
          <td style="padding: 6px 8px; text-align: center;">✅</td>
          <td style="padding: 6px 8px; text-align: center;">✅</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 6px 0;">広告</td>
          <td style="padding: 6px 8px; text-align: center;">あり</td>
          <td style="padding: 6px 8px; text-align: center; color: #16a34a; font-weight: 600;">なし</td>
        </tr>
        <tr style="border-bottom: 1px solid #f1f5f9;">
          <td style="padding: 6px 0;">PDF出力</td>
          <td style="padding: 6px 8px; text-align: center;">❌</td>
          <td style="padding: 6px 8px; text-align: center;">✅</td>
        </tr>
        <tr>
          <td style="padding: 6px 0;">CSV出力</td>
          <td style="padding: 6px 8px; text-align: center;">❌</td>
          <td style="padding: 6px 8px; text-align: center;">✅</td>
        </tr>
      </table>
    </div>
  </div>

  <div class="footer">
    <p>暗号資産損益計算ツール</p>
    <p><a href="{FRONTEND_URL}">crypto-tax-frontend.vercel.app</a></p>
    <p>このメールは {user_email} 宛に送信されています。</p>
    <p>配信停止をご希望の場合はこのメールに返信してください。</p>
  </div>
</div>
</body>
</html>"""
    return subject, html


def payment_success_email(user_email: str) -> tuple[str, str]:
    """
    決済完了・プレミアムプラン開始メール
    Returns: (subject, html)
    """
    subject = "プレミアムプランへようこそ！ - 暗号資産損益計算ツール"
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8">{_BASE_STYLE}</head>
<body>
<div class="container">
  <div class="card">
    <div class="logo"><div class="logo-icon">₿</div></div>
    <h1>🎉 プレミアムプランの<br>ご購入ありがとうございます！</h1>

    <p>暗号資産損益計算ツールのプレミアムプランが有効になりました。以下のすべての機能がご利用いただけます。</p>

    <div class="highlight highlight-gold">
      <div style="text-align: center; margin-bottom: 8px;">
        <span class="badge badge-premium">Premium 有効</span>
      </div>
      <ul class="feature-list">
        <li>✅ 広告なしでストレスフリーに利用</li>
        <li>✅ 損益計算書のPDF出力</li>
        <li>✅ 取引データのCSV出力</li>
      </ul>
    </div>

    <div class="highlight">
      <p style="margin: 0 0 8px; font-weight: 600; color: #0f172a;">ご利用明細</p>
      <table style="width: 100%; font-size: 14px;">
        <tr>
          <td style="padding: 4px 0; color: #64748b;">プラン</td>
          <td style="padding: 4px 0; text-align: right; color: #0f172a; font-weight: 600;">プレミアムプラン</td>
        </tr>
        <tr>
          <td style="padding: 4px 0; color: #64748b;">料金</td>
          <td style="padding: 4px 0; text-align: right; color: #0f172a; font-weight: 600;">980円 / 年</td>
        </tr>
        <tr>
          <td style="padding: 4px 0; color: #64748b;">お支払い方法</td>
          <td style="padding: 4px 0; text-align: right; color: #0f172a;">クレジットカード（Stripe）</td>
        </tr>
        <tr>
          <td style="padding: 4px 0; color: #64748b;">有効期限</td>
          <td style="padding: 4px 0; text-align: right; color: #0f172a;">購入日から1年間</td>
        </tr>
      </table>
    </div>

    <div style="text-align: center;">
      <a href="{FRONTEND_URL}" class="btn">さっそく使ってみる</a>
    </div>

    <hr class="divider">
    <p style="font-size: 12px; color: #94a3b8;">
      決済に関するお問い合わせはサポートチャット（画面右下の💬ボタン）からお気軽にどうぞ。
      解約はいつでも可能です。解約後も有効期限までプレミアム機能をご利用いただけます。
    </p>
  </div>

  <div class="footer">
    <p>暗号資産損益計算ツール</p>
    <p><a href="{FRONTEND_URL}">crypto-tax-frontend.vercel.app</a></p>
    <p>このメールは {user_email} 宛に送信されています。</p>
  </div>
</div>
</body>
</html>"""
    return subject, html


# ========================================
# Supabase 確認メール用テンプレート
# ========================================
SUPABASE_CONFIRM_TEMPLATE = f"""
<div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 40px 20px; background: #f8fafc;">
  <div style="background: #ffffff; border-radius: 12px; padding: 32px; box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
    <div style="text-align: center; margin-bottom: 24px;">
      <div style="display: inline-block; width: 48px; height: 48px; line-height: 48px; background: #2563eb; color: white; border-radius: 12px; font-size: 24px; font-weight: bold;">₿</div>
    </div>
    <h1 style="color: #0f172a; font-size: 20px; text-align: center; margin: 0 0 16px;">メールアドレスの確認</h1>
    <p style="color: #475569; font-size: 14px; line-height: 1.7; text-align: center;">
      暗号資産損益計算ツールへの登録ありがとうございます。<br>
      以下のボタンをクリックして、メールアドレスを確認してください。
    </p>
    <div style="text-align: center; margin: 24px 0;">
      <a href="{{{{ .ConfirmationURL }}}}" style="display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-size: 14px; font-weight: 600;">メールアドレスを確認する</a>
    </div>
    <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
    <div style="background: #fffbeb; border: 1px solid #fde68a; border-radius: 8px; padding: 16px; margin: 16px 0;">
      <p style="margin: 0 0 4px; font-weight: 600; color: #92400e; font-size: 13px;">プレミアムプラン（年間980円）のご案内</p>
      <p style="margin: 0; font-size: 12px; color: #92400e;">広告なし・PDF出力・CSV出力が使い放題になります。</p>
    </div>
    <p style="color: #94a3b8; font-size: 11px; text-align: center;">
      このメールに心当たりがない場合は、無視してください。
    </p>
  </div>
</div>
"""
