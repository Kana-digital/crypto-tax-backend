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

app = FastAPI()

anthropic_client = Anthropic()  # ANTHROPIC_API_KEY 環境変数を自動参照

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
