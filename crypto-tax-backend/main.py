import shutil
import tempfile
import os
import io
from anthropic import Anthropic
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from parsers import coincheck, sbivc, bitbank, exported
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

anthropic_client = Anthropic()  # ANTHROPIC_API_KEY 環境変数を自動参照

# Supabase クライアント
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY) if SUPABASE_URL and SUPABASE_ANON_KEY else None

# Stripe 設定
stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_PRICE_ID = os.environ.get("STRIPE_PRICE_ID", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://crypto-tax-frontend.vercel.app")

CHAT_SYSTEM_PROMPT = """あなたは「暗号資産損益計算ツール」のサポートAIです。
ユーザーからの質問・不具合報告に丁寧かつ簡潔に日本語で答えてください。

【ツールの概要】
- Coincheck・SBI VC Trade・bitbank の取引履歴CSVをアップロードすると損益を計算するWebツールです
- 計算方法は「総平均法」と「移動平均法」に対応しています
- 計算結果はPDFでもダウンロードできます
- 無料で利用できます

【よくある質問と回答】
- 対応取引所: Coincheck・SBI VC Trade・bitbank のみです
- CSVの取得方法: 各取引所のマイページ→取引履歴→CSV出力からダウンロードできます
- 計算結果はあくまで参考値であり、確定申告には税理士への相談を推奨します
- アップロードしたCSVはサーバーに保存されず、計算後即座に削除されます

不具合の報告を受けた場合は、「ご報告ありがとうございます。開発者に共有し改善いたします」と伝えてください。
回答は3〜5文程度でコンパクトにまとめてください。"""

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
    for parser in [exported, coincheck, sbivc, bitbank]:
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


@app.post("/calculate")
async def calculate(
    files: List[UploadFile] = File(...),
    method: str = Form(...),
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

    return {
        "total_profit": total_profit,
        "trades": results,
        "raw_trades": all_trades,
    }


@app.post("/calculate/pdf")
async def calculate_pdf(
    files: List[UploadFile] = File(...),
    method: str = Form(...),
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
    try:
        response = anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=CHAT_SYSTEM_PROMPT,
            messages=[{"role": m.role, "content": m.content} for m in request.messages],
        )
        return {"reply": response.content[0].text}
    except Exception as e:
        raise HTTPException(status_code=500, detail="AIサポートへの接続に失敗しました。しばらく待ってから再度お試しください。")


# ==================== Exchange Requests ====================
@app.post("/request-exchange")
async def request_exchange(
    exchange_name: str = Form(...),
    email: str = Form(...),
    csv_file: UploadFile = File(None),  # 任意
):
    if not supabase:
        raise HTTPException(status_code=503, detail="データベースに接続できません。")
    exchange_name = exchange_name.strip()
    email = email.strip().lower()
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


# ==================== Stripe 決済 ====================

class CheckoutRequest(BaseModel):
    user_id: str
    email: str

@app.post("/create-checkout-session")
async def create_checkout_session(req: CheckoutRequest):
    if not stripe.api_key or not STRIPE_PRICE_ID:
        raise HTTPException(status_code=503, detail="決済機能が設定されていません。")
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            mode="subscription",
            customer_email=req.email,
            client_reference_id=req.user_id,
            billing_address_collection="required",
            success_url=f"{FRONTEND_URL}?payment=success",
            cancel_url=f"{FRONTEND_URL}?payment=cancel",
        )
        return {"checkout_url": session.url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"決済セッションの作成に失敗しました: {str(e)}")


@app.post("/stripe-webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="無効な署名です。")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        if user_id and supabase:
            from datetime import datetime, timedelta, timezone
            paid_until = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
            supabase.table("user_profiles").upsert({
                "id": user_id,
                "is_paid": True,
                "paid_until": paid_until,
            }).execute()

    elif event["type"] in ("customer.subscription.deleted", "customer.subscription.paused"):
        subscription = event["data"]["object"]
        # customer IDからユーザーを特定してis_paidをfalseに
        customer_id = subscription.get("customer")
        if customer_id and supabase:
            try:
                customer = stripe.Customer.retrieve(customer_id)
                # client_reference_idはCheckout Sessionにあるので、metadataで対応
                # ここでは簡易的にemailで検索
                email = customer.get("email")
                if email:
                    # auth.usersからemailでuser_idを取得する処理は省略
                    # 将来的にstripe customer idをuser_profilesに保存して対応
                    pass
            except Exception:
                pass

    return {"received": True}
