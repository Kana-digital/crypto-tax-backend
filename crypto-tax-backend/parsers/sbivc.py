import pandas as pd

REQUIRED_COLUMNS = {"約定日時", "売買", "銘柄", "数量", "約定レート", "取引手数料"}
BUY_TYPES = {"買"}
SELL_TYPES = {"売"}

def to_float(val):
    """カンマや空文字を考慮してfloatに変換"""
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return 0.0

def parse(file_path: str) -> list[dict]:
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
    except Exception:
        raise ValueError("CSVファイルの読み込みに失敗しました。ファイルが壊れていないか確認してください。")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            "SBI VC Trade用のCSVとして認識できません。"
            "「SBI VC Trade」を選択している場合は、SBI VC Tradeからエクスポートしたファイルを使用してください。"
        )

    trades = []
    try:
        for _, row in df.iterrows():
            action_type = str(row["売買"]).strip()

            # 買・売のみ処理
            if action_type not in (BUY_TYPES | SELL_TYPES):
                continue

            # 約定レートが空の行はスキップ
            try:
                price = to_float(row["約定レート"])
                if price == 0.0:
                    continue
            except Exception:
                continue

            # 銘柄から通貨名を取得（例: XDC/JPY → XDC）
            currency = str(row["銘柄"]).split("/")[0].strip()

            action = "買い" if action_type in BUY_TYPES else "売り"

            trades.append({
                "exchange": "sbivc",
                "datetime": row["約定日時"],
                "action": action,
                "currency": currency,
                "amount": to_float(row["数量"]),
                "price": price,
                "fee": to_float(row["取引手数料"]),
            })
    except Exception as e:
        raise ValueError(f"SBI VC Trade CSVのデータ解析中にエラーが発生しました：{e}")

    return trades
