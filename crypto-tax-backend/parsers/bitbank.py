import pandas as pd

REQUIRED_COLUMNS = {"通貨ペア", "取引日時", "売/買", "数量", "価格"}

def to_float(val):
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
            "bitbank用のCSVとして認識できません。"
            "「bitbank」を選択している場合は、bitbankからエクスポートしたファイルを使用してください。"
        )

    # 手数料列の特定（発生手数料 or 手数料）
    fee_col = None
    for col in ["発生手数料", "手数料"]:
        if col in df.columns:
            fee_col = col
            break

    trades = []
    try:
        for _, row in df.iterrows():
            action_raw = str(row["売/買"]).strip().lower()
            if action_raw in ["buy"]:
                action = "買い"
            elif action_raw in ["sell"]:
                action = "売り"
            elif action_raw in ["買い", "買"]:
                action = "買い"
            elif action_raw in ["売り", "売"]:
                action = "売り"
            else:
                continue  # 不明な種別はスキップ

            # 通貨ペアから通貨名を取得（例: xrp_jpy → XRP）
            currency = str(row["通貨ペア"]).split("_")[0].upper()

            fee = 0.0
            if fee_col:
                try:
                    fee = abs(to_float(row[fee_col]))
                except Exception:
                    fee = 0.0

            trades.append({
                "exchange": "bitbank",
                "datetime": row["取引日時"],
                "action": action,
                "currency": currency,
                "amount": to_float(row["数量"]),
                "price": to_float(row["価格"]),
                "fee": fee,
            })
    except Exception as e:
        raise ValueError(f"bitbank CSVのデータ解析中にエラーが発生しました：{e}")

    return trades
