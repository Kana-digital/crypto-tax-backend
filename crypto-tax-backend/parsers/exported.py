import pandas as pd

REQUIRED_COLUMNS = {"取引日時", "取引所", "売買", "通貨", "数量", "単価(円)", "手数料"}

def parse(file_path: str) -> list[dict]:
    try:
        df = pd.read_csv(file_path, encoding="utf-8")
    except Exception:
        raise ValueError("CSVファイルの読み込みに失敗しました。ファイルが壊れていないか確認してください。")

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError("エクスポートされた取引データのCSVとして認識できません。")

    trades = []
    try:
        for _, row in df.iterrows():
            trades.append({
                "exchange": str(row["取引所"]).strip(),
                "datetime": row["取引日時"],
                "action": str(row["売買"]).strip(),
                "currency": str(row["通貨"]).strip(),
                "amount": float(str(row["数量"]).replace(",", "")),
                "price": float(str(row["単価(円)"]).replace(",", "")),
                "fee": float(str(row["手数料"]).replace(",", "")) if pd.notna(row["手数料"]) else 0.0,
            })
    except Exception as e:
        raise ValueError(f"取引データCSVの解析中にエラーが発生しました：{e}")

    return trades
