import shutil
import tempfile
import os
import io
from anthropic import Anthropic
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.responses import HTMLResponse
from auth import get_current_user, get_optional_user, AuthUser
from parsers import coincheck, sbivc, bitbank, binance, exported
from email_service import send_email
from email_templates import welcome_email, upgrade_email, payment_success_email, registration_email, password_reset_email, SUPABASE_CONFIRM_TEMPLATE
from calculators import total_average, moving_average
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from supabase import create_client, Client
import stripe
from fastapi import Request

app = FastAPI()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
print(f"[Startup] ANTHROPIC_API_KEY set: {bool(ANTHROPIC_API_KEY)}, client initialized: {anthropic_client is not None}", flush=True)

# Supabase クライアント
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_URL and SUPABASE_ANON_KEY else None
supabase_admin: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY) if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY else None

# Stripe 設定
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://crypto-tax-frontend.vercel.app")

CHAT_SYSTEM_PROMPT = """あなたは「暗号資産損益計算ツール」のサポートAIです。
ユーザーからの質問・不具合報告に丁寧かつ簡潔に日本語で答えてください。
回答は3〜5文程度でコンパクトにまとめてください。

【ツールの概要】
暗号資産（仮想通貨）の取引履歴CSVをアップロードすると、年間の譲渡損益を自動計算するWebツールです。
確定申告の参考資料として利用できます。

【対応取引所とCSVの取得方法】
1. Coincheck
   - マイページ → 取引履歴 → CSV出力でダウンロード
   - 必要な列: 取引日時, 取引種別, 増加通貨名, 増加数量, 減少通貨名, 減少数量, 約定価格
   - ※残高行（取引日時が空の行）は自動スキップされます
2. SBI VC Trade
   - マイページ → 取引履歴 → CSV出力でダウンロード
   - 必要な列: 約定日時, 売買, 銘柄, 数量, 約定レート, 取引手数料
3. bitbank
   - マイページ → 取引履歴 → CSVダウンロード
   - 必要な列: 通貨ペア, 取引日時, 売/買, 数量, 価格
   - 日本語（買い/売り）と英語（buy/sell）の両方に対応
4. Binance
   - アカウント → 注文 → 取引履歴 → Export でCSVダウンロード
   - Spot Trade History / P2P / Convert など複数形式に対応
   - 通貨ペア形式: BTC/JPY, BTCJPY, ETHUSDT など自動認識
   - 対応Fiat/Stable: JPY, USDT, BUSD, FDUSD, USDC, BTC, ETH, BNB

【使い方の手順】
1. トップページで計算方法を選択（総平均法 or 移動平均法）
2. CSVファイルをドラッグ&ドロップ、またはファイル選択でアップロード
3. 「損益を計算する」ボタンをクリック
4. 取引所は自動判別されるので、取引所の選択は不要です
5. 複数の取引所のCSVを同時にアップロード可能（まとめて計算されます）
6. 計算結果が年度ごとに表示されます（収入・取得費・損益の内訳付き）

【計算方法の違い】
- 総平均法: 全取引の買い単価を平均して取得費を計算。計算がシンプルで初心者向き。
- 移動平均法: 買い取引のたびに平均取得費を更新。取引順序が重要。より正確な計算。
- どちらの方法でも、損益 =（売却単価 − 平均取得単価）× 数量 − 手数料 で算出されます。
- 迷ったら「総平均法」がおすすめです。

【料金プラン】
- 無料プラン（¥0）: CSV取り込み・損益計算・AIチャットサポートが利用可能。計算後に10秒間の広告が表示されます。
- プレミアムプラン（年間980円）: 広告なし＋取引履歴のPDF出力＋CSVエクスポートが可能。

【プレミアムプランについて】
- 登録方法: 画面上部の「⬆️ アップグレード」ボタン → クレジットカード決済（Stripe）
- 有効期間: 決済日から365日間
- 機能: 広告非表示、PDF帳票の出力、取引データのCSVエクスポート
- 解約方法: 設定画面の「解約」ボタンから。解約後も有効期間の終了まで機能は利用可能。
- 自動更新はありません。期限切れ後は無料プランに戻ります。

【新規登録・ログインの流れ】
- 新規登録: メールアドレスを入力 → 確認メールが届く → メール内のリンクから決済 → 決済完了メールのリンクからパスワード設定
- ログイン: メールアドレスとパスワードを入力
- パスワードを忘れた場合: ログイン画面の「パスワードを忘れた場合」→ メールでリセットリンク受信 → 新しいパスワード（8文字以上）を設定

【PDF出力について】
- プレミアムプラン限定機能です
- 計算結果画面でPDFボタンをクリックするとダウンロード可能
- 内容: 「暗号資産 譲渡損益計算書」（取引所・日時・通貨・数量・売却単価・取得単価・損益の一覧表）
- 確定申告の参考資料としてご利用ください

【セキュリティ・プライバシー】
- アップロードしたCSVはサーバーに一時的に処理され、計算後即座に削除されます
- CSVデータはデータベースに保存されません
- 決済情報はStripe（PCI DSS準拠）が安全に処理し、当サービスには保存されません

【よくあるエラーと対処法】
- 「CSVとして認識できません」→ 正しい取引所のCSVか確認してください。取引所のマイページから再ダウンロードをお試しください。
- 「CSVファイルの読み込みに失敗しました」→ ファイルが破損していないか確認してください。再ダウンロードをお試しください。
- 「メールアドレスまたはパスワードが正しくありません」→ パスワードをお忘れの場合はリセットできます。
- 「トークンの有効期限が切れています」→ ページを再読み込みして再ログインしてください。
- 「パスワードの更新に失敗しました」→ リセットリンクの有効期限が切れています。再度リセットメールを送信してください。
- 計算結果が0になる → CSVに売却取引が含まれているか確認してください。損益は売却時のみ発生します。

【確定申告について】
- 計算結果はあくまで参考値です。正式な確定申告には税理士への相談を推奨します。
- 暗号資産の所得は「雑所得」として総合課税の対象です。
- 年間の利益が20万円を超える給与所得者は確定申告が必要です。

【取引所追加リクエスト】
- トップページ下部の「対応取引所リクエスト」から希望の取引所名を送信できます。
- 3件以上のリクエストが集まった取引所は実装予定として検討されます。

不具合の報告を受けた場合は、「ご報告ありがとうございます。開発者に共有し改善いたします。詳しい状況（操作手順・エラーメッセージなど）を教えていただけると助かります。」と伝えてください。
わからない質問を受けた場合は、「申し訳ございませんが、詳しくお答えできません。画面下の「開発者に連絡」ボタンから直接お問い合わせいただけます。」と案内してください。"""

# FAQフォールバック（Anthropic API 使用不可時）
FAQ_RESPONSES = {
    # 対応取引所
    "対応取引所": "現在対応している取引所は Coincheck・SBI VC Trade・bitbank・Binance の4つです。取引所追加リクエストも受け付けています。",
    "取引所": "現在対応している取引所は Coincheck・SBI VC Trade・bitbank・Binance の4つです。",
    "coincheck": "Coincheckに対応しています。マイページ→取引履歴→CSV出力からダウンロードしたファイルをそのままアップロードしてください。",
    "sbi": "SBI VC Tradeに対応しています。マイページ→取引履歴→CSV出力からダウンロードしたファイルをそのままアップロードしてください。",
    "bitbank": "bitbankに対応しています。マイページ→取引履歴→CSVダウンロードからファイルを取得してアップロードしてください。",
    "binance": "Binanceに対応しています。アカウント→注文→取引履歴→Exportからダウンロードしたファイルをアップロードしてください。Spot・P2P・Convert形式に対応しています。",
    # CSV関連
    "csv": "各取引所のマイページ→取引履歴→CSV出力からダウンロードできます。ダウンロードしたCSVファイルをそのままアップロードしてください。取引所は自動判別されます。",
    "アップロード": "トップページでCSVファイルをドラッグ&ドロップするか、ファイル選択ボタンからアップロードできます。複数ファイルの同時アップロードにも対応しています。",
    "ドラッグ": "CSVファイルをページ上にドラッグ&ドロップするとアップロードできます。ファイル選択ボタンからも可能です。",
    "認識できません": "「CSVとして認識できません」エラーは、正しい取引所のCSVでない場合に発生します。取引所のマイページから取引履歴CSVを再ダウンロードしてお試しください。",
    "読み込み": "「読み込みに失敗しました」エラーは、ファイルが破損している可能性があります。取引所から再ダウンロードをお試しください。",
    "複数": "複数の取引所のCSVを同時にアップロードできます。すべての取引をまとめて損益計算します。",
    # 計算方法
    "計算方法": "「総平均法」と「移動平均法」の2つに対応しています。迷ったら「総平均法」がおすすめです。",
    "総平均法": "総平均法は全取引の買い単価を平均して取得費を計算します。計算がシンプルで初心者向きです。",
    "移動平均法": "移動平均法は買い取引のたびに平均取得費を更新する方法です。取引順序が重要で、より正確な計算ができます。",
    "どっちがいい": "迷ったら「総平均法」がおすすめです。計算がシンプルで初心者向きです。移動平均法はより正確ですが、取引順序が重要になります。",
    "結果が0": "損益が0になる場合、CSVに売却取引が含まれているか確認してください。損益は売却時のみ発生します。買い取引のみでは損益は計算されません。",
    # 料金・プレミアム
    "料金": "無料プランではCSV取り込み・損益計算が利用可能です（計算後に10秒間の広告あり）。プレミアムプラン（年間980円）では広告非表示＋PDF出力＋CSVエクスポートが可能です。",
    "いくら": "プレミアムプランは年間980円です。広告非表示・PDF出力・CSVエクスポートが利用可能になります。自動更新はありません。",
    "プレミアム": "プレミアムプラン（年間980円）では広告非表示＋PDF出力＋CSVエクスポートが可能です。画面上部の「⬆️ アップグレード」ボタンからクレジットカード決済で購入できます。",
    "アップグレード": "画面上部の「⬆️ アップグレード」ボタンをクリックし、クレジットカード決済（Stripe）で購入できます。決済完了後すぐに機能が使えます。",
    "広告": "無料プランでは計算後に10秒間の広告が表示されます。プレミアムプラン（年間980円）にアップグレードすると広告なしで利用できます。",
    "自動更新": "プレミアムプランに自動更新はありません。有効期間（365日間）が終了すると自動的に無料プランに戻ります。",
    # PDF
    "pdf": "PDF出力はプレミアムプラン限定の機能です。計算結果画面でPDFボタンをクリックするとダウンロードできます。「暗号資産 譲渡損益計算書」として出力されます。",
    # アカウント関連
    "登録": "新規登録はメールアドレスを入力→確認メール受信→メール内のリンクから決済→決済完了メールのリンクからパスワード設定、の流れです。",
    "ログイン": "画面上部のログインボタンからメールアドレスとパスワードを入力してログインできます。",
    "パスワード": "パスワードを忘れた場合は、ログイン画面の「パスワードを忘れた場合」からリセットできます。メールでリセットリンクが届きます。パスワードは8文字以上で設定してください。",
    "メールが届かない": "メールが届かない場合は、迷惑メールフォルダをご確認ください。それでも届かない場合は、画面下の「開発者に連絡」ボタンからお問い合わせください。",
    "リンク": "メール内のリンクの有効期限が切れている場合は、再度パスワードリセットをお試しください。ログイン画面の「パスワードを忘れた場合」から再送信できます。",
    "有効期限": "メール内のリンクには有効期限があります。期限切れの場合は、再度リセットメールを送信してください。プレミアムプランの有効期間は決済日から365日間です。",
    # 確定申告
    "確定申告": "計算結果はあくまで参考値です。確定申告の際は税理士への相談を推奨します。暗号資産の所得は「雑所得」として総合課税の対象で、年間利益20万円超の給与所得者は確定申告が必要です。",
    "税金": "暗号資産の利益は「雑所得」として確定申告の対象です。年間の利益が20万円を超える給与所得者は申告が必要です。詳しくは税理士にご相談ください。",
    "雑所得": "暗号資産の所得は「雑所得」として総合課税の対象です。詳しい申告方法は税理士にご相談ください。",
    # セキュリティ
    "セキュリティ": "アップロードしたCSVはサーバーで一時的に処理され、計算後即座に削除されます。データベースには保存されません。決済情報はStripe（PCI DSS準拠）が安全に処理します。",
    "保存": "アップロードしたCSVはサーバーに保存されません。計算処理後に即座に削除されます。安心してご利用ください。",
    "個人情報": "CSVデータはサーバーに保存されず、決済情報もStripeが安全に処理します。当サービスにクレジットカード情報は保存されません。",
    # 解約
    "解約": "設定画面の「解約」ボタンから解約できます。解約後も有効期間の終了まではプレミアム機能をご利用いただけます。自動更新はないので、放置しても課金は発生しません。",
    "退会": "解約は設定画面の「解約」ボタンから行えます。解約後も有効期間終了までは機能を利用できます。",
    "返金": "決済完了後の返金については、画面下の「開発者に連絡」ボタンからお問い合わせください。",
    # 不具合・エラー
    "不具合": "ご報告ありがとうございます。開発者に共有し改善いたします。詳しい状況（操作手順・エラーメッセージなど）を教えていただけると助かります。",
    "バグ": "ご報告ありがとうございます。開発者に共有し改善いたします。詳しい状況を教えていただけると助かります。",
    "エラー": "ご不便おかけして申し訳ございません。どのような操作でエラーが発生したか教えていただけますか？開発者に共有いたします。",
    "使い方": "トップページで計算方法を選択→CSVをアップロード→「損益を計算する」をクリックで計算できます。取引所は自動判別されるので選択不要です。",
    "手順": "① 計算方法を選択（総平均法 or 移動平均法）→ ② CSVをドラッグ&ドロップ → ③「損益を計算する」をクリック → ④ 結果が年度ごとに表示されます。",
    # リクエスト
    "リクエスト": "トップページ下部の「対応取引所リクエスト」から希望の取引所名を送信できます。3件以上のリクエストが集まると実装を検討します。",
    "追加": "新しい取引所の追加リクエストは、トップページ下部の「対応取引所リクエスト」から送信できます。",
}
FAQ_DEFAULT = "お問い合わせありがとうございます。こちらはサポートチャットです。使い方・対応取引所・料金プラン・CSV取り込み方法・エラーの対処法など、お気軽にご質問ください。解決しない場合は「開発者に連絡」ボタンをご利用ください。"

def faq_fallback(user_message: str) -> str:
    """キーワードマッチングによる簡易FAQ応答"""
    msg_lower = user_message.lower()
    for keyword, response in FAQ_RESPONSES.items():
        if keyword.lower() in msg_lower:
            return response
    return FAQ_DEFAULT

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"(http://localhost:\d+|https://.*\.vercel\.app|https://.*\.onrender\.com)",
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日本語フォント登録
pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))
FONT_NAME = "HeiseiKakuGo-W5"


def auto_detect_and_parse(tmp_path: str):
    """CSVの列名を見て取引所を自動判別してパースする"""
    errors = []
    for parser in [exported, coincheck, sbivc, bitbank, binance]:
        try:
            return parser.parse(tmp_path)
        except ValueError as e:
            errors.append(str(e))
        except Exception as e:
            errors.append(str(e))
    raise ValueError(
        "対応している取引所のCSVとして認識できませんでした。\n"
        "Coincheck・SBI VC Trade・bitbank のCSVファイルをアップロードしてください。"
    )


def parse_trades(tmp_path: str):
    return auto_detect_and_parse(tmp_path)


def run_calculator(trades, method: str):
    if method == "total_average":
        return total_average.calculate(trades)
    elif method == "moving_average":
        return moving_average.calculate(trades)
    return None


def generate_pdf(results: list, total_profit: float, method_label: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", fontName=FONT_NAME, fontSize=16, spaceAfter=6, alignment=1
    )
    sub_style = ParagraphStyle(
        "Sub", fontName=FONT_NAME, fontSize=11, spaceAfter=4
    )
    normal_style = ParagraphStyle(
        "Normal", fontName=FONT_NAME, fontSize=9
    )

    elements = []
    elements.append(Paragraph("暗号資産 譲渡損益計算書", title_style))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(f"計算方法：{method_label}", sub_style))
    total_color = "red" if total_profit >= 0 else "blue"
    elements.append(
        Paragraph(
            f'合計損益：<font color="{total_color}"><b>{total_profit:,.0f} 円</b></font>',
            sub_style,
        )
    )
    elements.append(Spacer(1, 6 * mm))

    # テーブルヘッダー
    header = ["取引所", "日時", "通貨", "数量", "売却単価(円)", "取得単価(円)", "損益(円)"]
    data = [header]
    for r in results:
        dt = str(r["datetime"])[:16] if r["datetime"] else "-"
        profit_str = f'{r["profit"]:,.0f}'
        data.append([
            str(r.get("exchange", "-")),
            dt,
            str(r.get("currency", "-")),
            f'{r["amount"]:.6f}',
            f'{r["sell_price"]:,.0f}',
            f'{r["avg_buy_price"]:,.0f}',
            profit_str,
        ])

    col_widths = [22 * mm, 32 * mm, 18 * mm, 26 * mm, 28 * mm, 28 * mm, 26 * mm]
    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), FONT_NAME),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#EFF6FF")]),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ])
    )
    elements.append(table)

    doc.build(elements)
    return buffer.getvalue()


@app.get("/")
def read_root():
    return {"message": "crypto-tax-backend 起動中！"}


# ==================== 新規登録 ====================

class RegisterRequest(BaseModel):
    email: str

@app.post("/register")
async def register_user(req: RegisterRequest):
    """メールアドレスで新規登録 → 確認メール（決済リンク＋パスワード設定リンク）を送信"""
    import re, uuid
    email = req.email.strip().lower()
    if not email or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise HTTPException(status_code=422, detail="正しいメールアドレスを入力してください。")

    if not supabase_admin:
        raise HTTPException(status_code=503, detail="サービスが設定されていません。")

    # 1. Supabase Admin API でユーザー作成
    temp_password = uuid.uuid4().hex[:16] + "Aa1!"
    try:
        user_res = supabase_admin.auth.admin.create_user({
            "email": email,
            "password": temp_password,
            "email_confirm": True,  # メール確認済みとして作成
        })
        user_id = user_res.user.id
    except Exception as e:
        error_msg = str(e)
        if "already" in error_msg.lower() or "duplicate" in error_msg.lower():
            raise HTTPException(status_code=409, detail="このメールアドレスは既に登録されています。ログインしてください。")
        raise HTTPException(status_code=500, detail=f"ユーザー作成に失敗しました: {error_msg}")

    # 2. Stripe Checkout セッションを作成
    checkout_url = None
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {
                        "name": "暗号資産損益計算ツール 年間プラン",
                        "description": "広告非表示・CSV/PDF出力機能（1年間有効）",
                    },
                    "unit_amount": 980,
                },
                "quantity": 1,
            }],
            mode="payment",
            customer_email=email,
            client_reference_id=str(user_id),
            billing_address_collection="required",
            success_url=f"{FRONTEND_URL}?payment=success",
            cancel_url=f"{FRONTEND_URL}?payment=cancel",
        )
        checkout_url = session.url
    except Exception as e:
        print(f"[Register] Stripe session作成失敗: {e}")

    # 3. Resend API で申し込み受付メールを送信（パスワード設定は決済完了後に案内）
    try:
        subject, html = registration_email(email, checkout_url)
        await send_email(email, subject, html)
        print(f"[Register] 登録確認メール送信成功: {email}")
    except Exception as e:
        print(f"[Register] メール送信失敗: {e}")
        # メール送信失敗でもユーザー作成は完了しているので200を返す
        return {"message": "登録は完了しましたが、メール送信に失敗しました。サポートにお問い合わせください。", "email_sent": False}

    return {"message": "登録確認メールを送信しました。メールをご確認ください。", "email_sent": True}


# ==================== パスワードリセット ====================

class ForgotPasswordRequest(BaseModel):
    email: str

@app.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """パスワードリセットメールをResend経由で送信"""
    import re
    email = req.email.strip().lower()
    if not email or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        raise HTTPException(status_code=422, detail="正しいメールアドレスを入力してください。")

    if not supabase_admin:
        raise HTTPException(status_code=503, detail="サービスが設定されていません。")

    # Supabase Admin API でパスワードリセットリンクを生成
    try:
        link_res = supabase_admin.auth.admin.generate_link({
            "type": "recovery",
            "email": email,
            "options": {"redirect_to": FRONTEND_URL},
        })
        reset_url = None
        if hasattr(link_res, 'properties') and hasattr(link_res.properties, 'action_link'):
            reset_url = link_res.properties.action_link
        elif hasattr(link_res, 'action_link'):
            reset_url = link_res.action_link

        if not reset_url:
            print(f"[ForgotPassword] generate_link response: {link_res}")
            # ユーザーが存在しなくても同じレスポンスを返す（セキュリティ）
            return {"message": "メールアドレスが登録されている場合、リセットメールを送信しました。"}

    except Exception as e:
        error_msg = str(e)
        print(f"[ForgotPassword] リンク生成失敗: {error_msg}")
        # ユーザー未登録でも同じレスポンスを返す（メールアドレスの存在を漏らさない）
        return {"message": "メールアドレスが登録されている場合、リセットメールを送信しました。"}

    # Resend API でリセットメールを送信
    try:
        subject, html = password_reset_email(email, reset_url)
        await send_email(email, subject, html)
        print(f"[ForgotPassword] リセットメール送信成功: {email}")
    except Exception as e:
        print(f"[ForgotPassword] メール送信失敗: {e}")
        raise HTTPException(status_code=500, detail="メール送信に失敗しました。しばらく待ってから再度お試しください。")

    return {"message": "メールアドレスが登録されている場合、リセットメールを送信しました。"}


# ==================== Auth ====================
@app.get("/me")
async def get_me(user: AuthUser = Depends(get_current_user)):
    """認証必須: 現在のユーザー情報を返す"""
    result = {"id": user.id, "email": user.email, "role": user.role}
    if supabase:
        try:
            profile = supabase_admin.table("user_profiles").select("is_paid,paid_until").eq("id", user.id).single().execute()
            if profile.data:
                result["is_paid"] = profile.data.get("is_paid", False)
                result["paid_until"] = profile.data.get("paid_until")
        except Exception:
            result["is_paid"] = False
    return result


def _is_user_paid(user: Optional[AuthUser]) -> bool:
    """ユーザーが有料プランかどうかを判定する"""
    if not user or not supabase_admin:
        return False
    try:
        from datetime import datetime, timezone
        profile = supabase_admin.table("user_profiles").select("is_paid,paid_until").eq("id", user.id).single().execute()
        if profile.data and profile.data.get("is_paid"):
            paid_until = profile.data.get("paid_until")
            if paid_until:
                expiry = datetime.fromisoformat(paid_until.replace("Z", "+00:00"))
                return expiry > datetime.now(timezone.utc)
            return True
        return False
    except Exception:
        return False


@app.post("/calculate")
async def calculate(
    files: List[UploadFile] = File(...),
    method: str = Form(...),
    user: Optional[AuthUser] = Depends(get_optional_user),
):
    all_trades = []
    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        try:
            trades = parse_trades(tmp_path)
        except ValueError as e:
            os.unlink(tmp_path)
            raise HTTPException(status_code=422, detail=f"{file.filename}：{str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        if trades is None:
            raise HTTPException(status_code=422, detail=f"{file.filename}：対応している取引所のCSVとして認識できませんでした。")
        all_trades.extend(trades)

    # 日時順に並び替え
    all_trades.sort(key=lambda t: str(t["datetime"]))

    results = run_calculator(all_trades, method)
    if results is None:
        raise HTTPException(status_code=422, detail="未対応の計算方法です。")

    total_profit = sum(r["profit"] for r in results)

    # 無料ユーザーにはCSV取り込み後に広告を表示
    is_paid = _is_user_paid(user)

    return {
        "total_profit": total_profit,
        "trades": results,
        "raw_trades": all_trades,
        "show_ad": not is_paid,
        "is_paid": is_paid,
    }


@app.post("/calculate/pdf")
async def calculate_pdf(
    files: List[UploadFile] = File(...),
    method: str = Form(...),
    user: AuthUser = Depends(get_current_user),
):
    # 有料プランのユーザーのみPDF出力可能
    if not _is_user_paid(user):
        raise HTTPException(
            status_code=403,
            detail="PDF出力は有料プラン（年間980円）の機能です。アップグレードしてご利用ください。"
        )

    all_trades = []
    for file in files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name
        try:
            trades = parse_trades(tmp_path)
        except ValueError as e:
            os.unlink(tmp_path)
            raise HTTPException(status_code=422, detail=f"{file.filename}：{str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        if trades is None:
            raise HTTPException(status_code=422, detail=f"{file.filename}：対応している取引所のCSVとして認識できませんでした。")
        all_trades.extend(trades)

    all_trades.sort(key=lambda t: str(t["datetime"]))

    results = run_calculator(all_trades, method)
    if results is None:
        raise HTTPException(status_code=422, detail="未対応の計算方法です。")

    total_profit = sum(r["profit"] for r in results)
    method_label = "総平均法" if method == "total_average" else "移動平均法"

    pdf_bytes = generate_pdf(results, total_profit, method_label)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=crypto_tax_report.pdf"},
    )


# ==================== Chat Support ====================
class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str

class ChatRequest(BaseModel):
    messages: List[ChatMessage]

@app.post("/chat")
async def chat(request: ChatRequest):
    # ユーザーの最新メッセージを取得
    user_messages = [m for m in request.messages if m.role == "user"]
    latest_user_msg = user_messages[-1].content if user_messages else ""

    # Anthropic API で応答を試みる
    print(f"[Chat] anthropic_client initialized: {anthropic_client is not None}", flush=True)
    if anthropic_client:
        try:
            response = anthropic_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=CHAT_SYSTEM_PROMPT,
                messages=[{"role": m.role, "content": m.content} for m in request.messages],
            )
            print(f"[Chat] AI response OK", flush=True)
            return {"reply": response.content[0].text}
        except Exception as e:
            import traceback
            print(f"[Chat] Anthropic API error: {type(e).__name__}: {e}", flush=True)
            traceback.print_exc()
    else:
        print("[Chat] ANTHROPIC_API_KEY is not set, using FAQ fallback", flush=True)

    # フォールバック: キーワードベースのFAQ応答
    reply = faq_fallback(latest_user_msg)
    return {"reply": reply}


class EscalateRequest(BaseModel):
    messages: List[ChatMessage]
    user_email: Optional[str] = None
    category: str = "bug"

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "9kana6@gmail.com")

@app.post("/escalate")
async def escalate_to_admin(request: EscalateRequest):
    """チャットで解決できない問題を管理者にエスカレーション（DB保存＋メール通知）"""
    chat_log = [{"role": m.role, "content": m.content} for m in request.messages]

    # 1. Supabase に保存
    ticket_id = None
    if supabase_admin:
        try:
            import json
            res = supabase_admin.table("support_tickets").insert({
                "user_email": request.user_email,
                "category": request.category,
                "chat_log": json.dumps(chat_log, ensure_ascii=False),
                "status": "open",
            }).execute()
            if res.data:
                ticket_id = res.data[0].get("id")
        except Exception as e:
            print(f"[Escalate] DB保存失敗: {e}")

    # 2. 管理者にメール通知
    try:
        chat_text = "\n".join([f"{'👤 ユーザー' if m.role == 'user' else '🤖 AI'}: {m.content}" for m in request.messages])
        subject = f"【サポート】{request.category} - {request.user_email or '匿名'}"
        html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="font-family:sans-serif;padding:20px;">
<h2>サポートチケット</h2>
<p><strong>カテゴリ:</strong> {request.category}</p>
<p><strong>ユーザー:</strong> {request.user_email or '未ログイン'}</p>
{f'<p><strong>チケットID:</strong> {ticket_id}</p>' if ticket_id else ''}
<hr>
<h3>チャット履歴</h3>
<pre style="background:#f5f5f5;padding:16px;border-radius:8px;white-space:pre-wrap;">{chat_text}</pre>
</body></html>"""
        await send_email(ADMIN_EMAIL, subject, html)
    except Exception as e:
        print(f"[Escalate] メール送信失敗: {e}")

    return {"message": "開発者に報告しました。ご連絡ありがとうございます。", "ticket_id": ticket_id}


# ==================== Exchange Requests ====================
@app.post("/request-exchange")
async def request_exchange(
    exchange_name: str = Form(...),
    email: str = Form(""),
    csv_file: UploadFile = File(None),  # 任意
    user: Optional[AuthUser] = Depends(get_optional_user),
):
    """認証任意: ログイン済みならJWTからメール取得、未ログインならフォーム入力"""
    if not supabase:
        raise HTTPException(status_code=503, detail="データベースに接続できません。")
    exchange_name = exchange_name.strip()
    # 認証済みユーザーのメールを優先使用
    email = (user.email if user and user.email else email).strip().lower()
    if not exchange_name or not email:
        raise HTTPException(status_code=422, detail="取引所名とメールアドレスを入力してください。")

    # CSV を Supabase Storage にアップロード（任意）
    csv_path = None
    if csv_file and csv_file.filename:
        if not csv_file.filename.endswith(".csv"):
            raise HTTPException(status_code=422, detail="CSVファイルのみアップロードできます。")
        contents = await csv_file.read()
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=422, detail="ファイルサイズは5MB以下にしてください。")
        import uuid, re
        safe_name = re.sub(r"[^\w.-]", "_", exchange_name)
        storage_path = f"{safe_name}/{uuid.uuid4()}.csv"
        try:
            supabase.storage.from_("exchange-csvs").upload(
                path=storage_path,
                file=contents,
                file_options={"content-type": "text/csv"},
            )
            csv_path = storage_path
        except Exception:
            pass  # CSV保存失敗はリクエスト自体を妨げない

    try:
        supabase.table("exchange_requests").upsert(
            {"exchange_name": exchange_name, "email": email, "csv_path": csv_path},
            on_conflict="exchange_name,email"
        ).execute()
    except Exception:
        raise HTTPException(status_code=500, detail="リクエストの保存に失敗しました。")

    count_res = supabase.table("exchange_requests").select("id", count="exact").eq("exchange_name", exchange_name).execute()
    count = count_res.count if count_res.count is not None else 0
    return {"exchange_name": exchange_name, "count": count, "is_official": count >= 3}


@app.get("/exchange-requests")
async def get_exchange_requests():
    if not supabase:
        raise HTTPException(status_code=503, detail="データベースに接続できません。")
    try:
        res = supabase.table("exchange_requests").select("exchange_name").execute()
        rows = res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail="データの取得に失敗しました。")

    # 取引所ごとにカウント集計
    counts: dict = {}
    for row in rows:
        name = row["exchange_name"]
        counts[name] = counts.get(name, 0) + 1

    result = [
        {"exchange_name": name, "count": cnt, "is_official": cnt >= 3}
        for name, cnt in sorted(counts.items(), key=lambda x: -x[1])
    ]
    return {"exchanges": result}


# ==================== プラン情報 ====================

@app.get("/plans")
async def get_plans():
    """料金プラン情報を返す（認証不要）"""
    return {
        "plans": [
            {
                "id": "free",
                "name": "無料プラン",
                "price": 0,
                "interval": None,
                "features": [
                    "CSV取り込みによる損益計算",
                    "総平均法・移動平均法に対応",
                    "AIサポートチャット",
                ],
                "limitations": [
                    "CSV取り込み時に広告が表示されます",
                    "PDF出力は利用できません",
                ],
            },
            {
                "id": "premium",
                "name": "プレミアムプラン",
                "price": 980,
                "currency": "jpy",
                "interval": "year",
                "features": [
                    "CSV取り込みによる損益計算",
                    "総平均法・移動平均法に対応",
                    "AIサポートチャット",
                    "広告なし",
                    "取引履歴PDF出力",
                ],
                "limitations": [],
            },
        ]
    }


# ==================== Stripe 決済 ====================

@app.post("/create-checkout-session")
async def create_checkout_session(user: AuthUser = Depends(get_current_user)):
    """認証必須: JWTからユーザーIDとメールを取得して決済セッションを作成"""
    if not stripe.api_key or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=503, detail="決済機能が設定されていません。")
    if not user.email:
        raise HTTPException(status_code=422, detail="メールアドレスが取得できません。プロフィールを確認してください。")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {
                        "name": "暗号資産損益計算ツール 年間プラン",
                        "description": "広告非表示・CSV/PDF出力機能（1年間有効）",
                    },
                    "unit_amount": 980,
                },
                "quantity": 1,
            }],
            mode="payment",
            customer_email=user.email,
            client_reference_id=user.id,
            billing_address_collection="required",
            success_url=f"{FRONTEND_URL}?payment=success",
            cancel_url=f"{FRONTEND_URL}?payment=cancel",
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"決済セッションの作成に失敗しました: {str(e)}")


async def _send_payment_email(customer_email: str):
    """決済完了メール送信（バックグラウンドタスク用）"""
    password_reset_url = None
    if supabase_admin:
        try:
            link_res = supabase_admin.auth.admin.generate_link({
                "type": "recovery",
                "email": customer_email,
                "options": {"redirect_to": FRONTEND_URL},
            })
            if hasattr(link_res, 'properties') and hasattr(link_res.properties, 'action_link'):
                password_reset_url = link_res.properties.action_link
            elif hasattr(link_res, 'action_link'):
                password_reset_url = link_res.action_link
            print(f"[Webhook] パスワードリセットリンク生成成功: {customer_email}")
        except Exception as e:
            print(f"[Webhook] パスワードリセットリンク生成失敗: {customer_email} - {e}")

    try:
        subject, html = payment_success_email(customer_email, password_reset_url)
        await send_email(customer_email, subject, html)
        print(f"[Webhook] 決済完了メール送信成功: {customer_email}")
    except Exception as e:
        print(f"[Webhook] 決済完了メール送信失敗: {customer_email} - {e}")


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request, background_tasks: BackgroundTasks):
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook署名シークレットが設定されていません。")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if not sig_header:
        raise HTTPException(status_code=400, detail="stripe-signatureヘッダーがありません。")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="無効な署名です。")
    except ValueError:
        raise HTTPException(status_code=400, detail="ペイロードが不正です。")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook検証エラー: {str(e)}")

    event_type = event["type"]
    print(f"[Webhook] イベント受信: {event_type}")

    if event_type == "checkout.session.completed":
        session = event["data"]["object"]
        # Stripe StripeObject は .get() を持たないため属性アクセスを使用
        user_id = session.client_reference_id
        customer_id = session.customer
        customer_email = session.customer_email or (
            session.customer_details.email if session.customer_details else None
        )
        print(f"[Webhook] checkout完了: user_id={user_id}, email={customer_email}")

        if user_id and supabase_admin:
            from datetime import datetime, timedelta, timezone
            paid_until = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            upsert_data = {
                "id": user_id,
                "is_paid": True,
                "paid_until": paid_until,
            }
            if customer_id:
                upsert_data["stripe_customer_id"] = customer_id
            supabase_admin.table("user_profiles").upsert(upsert_data).execute()
            print(f"[Webhook] user_profiles更新成功: {user_id}")

            # メール送信はバックグラウンドで実行（Stripeへのレスポンスを遅延させない）
            if customer_email:
                background_tasks.add_task(_send_payment_email, customer_email)

    # 一括払いのため、サブスクリプション関連イベントは不要
    # 有効期限（paid_until）で自動的に無料プランに戻る

    return {"received": True}


@app.post("/cancel-subscription")
async def cancel_subscription(user: AuthUser = Depends(get_current_user)):
    """認証必須: 有料プランを解約する（一括払いのため即時解約）"""
    if not supabase:
        raise HTTPException(status_code=503, detail="データベースが設定されていません。")

    # ユーザーの有料ステータスを確認
    res = supabase_admin.table("user_profiles").select("is_paid").eq("id", user.id).single().execute()
    if not res.data or not res.data.get("is_paid"):
        raise HTTPException(status_code=400, detail="現在有料プランに加入していません。")

    try:
        supabase_admin.table("user_profiles").update({
            "is_paid": False,
        }).eq("id", user.id).execute()

        return {"message": "解約しました。再度ご利用いただく場合は改めてお支払いください。"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解約処理に失敗しました: {str(e)}")


# ==================== メールテスト ====================

class TestEmailRequest(BaseModel):
    email: str
    type: str  # "welcome" | "upgrade" | "payment_success"

@app.post("/test-email/send")
async def test_email_send(req: TestEmailRequest):
    """テスト用：指定したメールアドレスにテストメールを送信する"""
    templates = {
        "welcome": welcome_email,
        "upgrade": upgrade_email,
        "payment_success": payment_success_email,
    }
    if req.type not in templates:
        raise HTTPException(
            status_code=422,
            detail=f"typeは {', '.join(templates.keys())} のいずれかを指定してください。"
        )
    subject, html = templates[req.type](req.email)
    try:
        result = await send_email(req.email, subject, html)
        return {"status": "sent", "type": req.type, "to": req.email, "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"メール送信に失敗しました: {str(e)}")


@app.get("/test-email/preview/{email_type}", response_class=HTMLResponse)
async def test_email_preview(email_type: str):
    """テスト用：メールのHTMLをブラウザでプレビューする"""
    templates = {
        "welcome": welcome_email,
        "upgrade": upgrade_email,
        "payment_success": payment_success_email,
        "supabase_confirm": None,
    }
    if email_type not in templates:
        raise HTTPException(
            status_code=422,
            detail=f"typeは {', '.join(templates.keys())} のいずれかを指定してください。"
        )
    if email_type == "supabase_confirm":
        return HTMLResponse(content=SUPABASE_CONFIRM_TEMPLATE.replace("{{ .ConfirmationURL }}", "#"))
    _, html = templates[email_type]("test@example.com")
    return HTMLResponse(content=html)
