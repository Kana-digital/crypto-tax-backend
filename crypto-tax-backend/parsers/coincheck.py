import pandas as pd

REQUIRED_COLUMNS = {"取引日時", "取引種別", "増加通貨名", "増加数量", "減少通貨名", "減少数量", "約定価格"}
BUY_TYPES = {"購入"}
SELL_TYPES = {"売却"}

def parse(file_path: str) -> list[dict]:
    try:
        df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
    except TypeError:
        try:
            df = pd.read_csv(file_path, encoding="utf-8", error_bad_lines=False)
        except Exception:
            raise ValueError("CSVファイルの読み込みに失敗しました。ファイルが壊れていないか確認してください。")
    except Exception:
        raise ValueError("CSVファイルの読み込みに失敗しました。ファイルが壊れていないか確認してください。")

    # 取引日時が空の行（残高情報など）を除外
    df = df[df["取引日時"].notna() & (df["取引日時"].astype(str).str.strip() != "")]

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            "Coincheck用のCSVとして認識できません。"
            "「Coincheck」を選択している場合は、Coincheckからエクスポートしたファイルを使用してください。"
        )

    trades = []
    try:
        for _, row in df.iterrows():
            action_type = str(row["取引種別"]).strip()

            # 購入・売却のみ処理。預入・受取・送付などはスキップ
            if action_type not in (BUY_TYPES | SELL_TYPES):
                continue

            # 約定価格が空の行はスキップ
            try:
                price = float(row["約定価格"])
            except (ValueError, TypeError):
                continue

            if action_type in BUY_TYPES:
                # 購入：増加した暗号資産が対象
                currency = str(row["増加通貨名"]).strip()
                amount = float(row["増加数量"])
                action = "買い"
            else:
                # 売却：減少した暗号資産が対象
                currency = str(row["減少通貨名"]).strip()
                amount = float(row["減少数量"])
                action = "売り"

            fee = 0.0
            try:
                fee_qty = row["手数料数量"]
                if pd.notna(fee_qty) and str(fee_qty).strip() != "":
                    fee = float(fee_qty)
            except (ValueError, TypeError):
                fee = 0.0

            trades.append({
                "exchange": "coincheck",
                "datetime": row["取引日時"],
                "action": action,
                "currency": currency,
                "amount": amount,
                "price": price,
                "fee": fee,
            })
    except Exception as e:
        raise ValueError(f"Coincheck CSVのデータ解析中にエラーが発生しました：{e}")

    return trades
