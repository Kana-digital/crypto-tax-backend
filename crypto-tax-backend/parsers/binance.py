"""
Binance 取引履歴CSVパーサー

Binanceの取引履歴CSVは以下のフォーマット:
1. スポット取引履歴 (Trade History):
   Date(UTC), Pair, Side, Price, Executed, Amount, Fee

2. 新フォーマット (Transaction History):
   Date(UTC), OrderNo, Pair, Type, Side, Order Price, Order Amount, AvgTrading Price,
   Filled, Total, status

3. P2P/Convert等の簡易フォーマット:
   Date(UTC), Pair, Side, Filled Price, Filled, Fee
"""
import pandas as pd

# スポット取引履歴の列名パターン
SPOT_COLUMNS = {"Date(UTC)", "Pair", "Side", "Price", "Executed", "Amount", "Fee"}
# 新フォーマットの列名パターン
NEW_COLUMNS = {"Date(UTC)", "Pair", "Side", "AvgTrading Price", "Filled", "Total"}
# 最小必須列
MIN_COLUMNS = {"Pair", "Side"}


def to_float(val) -> float:
    try:
        s = str(val).replace(",", "").strip()
        # "0.05 BTC" のような値からも数値を抽出
        parts = s.split()
        return float(parts[0])
    except (ValueError, TypeError, IndexError):
        return 0.0


def extract_currency(pair: str) -> str:
    """
    通貨ペアから暗号資産名を抽出する。
    例: BTCJPY → BTC, BTC/JPY → BTC, ETHUSDT → ETH, ETH/USDT → ETH
    """
    pair = str(pair).strip().upper()
    # スラッシュ区切り
    if "/" in pair:
        return pair.split("/")[0]
    # アンダースコア区切り
    if "_" in pair:
        return pair.split("_")[0]
    # JPY/USDT/BUSD/BTC/ETH/BNB で終わる場合のサフィックス除去
    for suffix in ["JPY", "USDT", "BUSD", "FDUSD", "USDC", "BTC", "ETH", "BNB"]:
        if pair.endswith(suffix) and len(pair) > len(suffix):
            return pair[:-len(suffix)]
    return pair


def normalize_side(side: str) -> str | None:
    """売買方向を正規化"""
    s = str(side).strip().upper()
    if s in ("BUY", "買い", "買"):
        return "買い"
    if s in ("SELL", "売り", "売"):
        return "売り"
    return None


def parse(file_path: str) -> list[dict]:
    # Binance CSVはUTF-8（BOMあり/なし両対応）
    for encoding in ["utf-8-sig", "utf-8"]:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            break
        except Exception:
            continue
    else:
        raise ValueError("CSVファイルの読み込みに失敗しました。")

    # 列名の前後スペースを除去
    df.columns = [c.strip() for c in df.columns]

    # Binance CSVかどうかの判定
    cols = set(df.columns)
    if not MIN_COLUMNS.issubset(cols):
        raise ValueError(
            "Binance用のCSVとして認識できません。"
            "Binanceからダウンロードした取引履歴CSVを使用してください。"
        )

    # フォーマット判定
    is_spot = SPOT_COLUMNS.issubset(cols)
    is_new = NEW_COLUMNS.issubset(cols)

    if not is_spot and not is_new:
        # 最低限 Date(UTC), Pair, Side があればパース試行
        if "Date(UTC)" not in cols:
            raise ValueError("Binance CSVに 'Date(UTC)' 列がありません。")

    # 日付列の特定
    date_col = "Date(UTC)" if "Date(UTC)" in cols else None
    if not date_col:
        for c in cols:
            if "date" in c.lower():
                date_col = c
                break

    trades = []
    try:
        for _, row in df.iterrows():
            side = normalize_side(row.get("Side", ""))
            if not side:
                continue

            pair = str(row.get("Pair", "")).strip()
            currency = extract_currency(pair)

            # 価格の取得（フォーマットに応じて列名が異なる）
            price = 0.0
            for price_col in ["Price", "AvgTrading Price", "Filled Price", "Order Price"]:
                if price_col in cols:
                    price = to_float(row.get(price_col, 0))
                    if price > 0:
                        break

            # 数量の取得
            amount = 0.0
            for amount_col in ["Executed", "Filled", "Order Amount", "Amount"]:
                if amount_col in cols:
                    val = to_float(row.get(amount_col, 0))
                    if val > 0:
                        amount = val
                        break

            if amount <= 0 or price <= 0:
                continue

            # 手数料
            fee = 0.0
            if "Fee" in cols:
                fee = to_float(row.get("Fee", 0))

            # 日時
            dt = str(row.get(date_col, "")) if date_col else ""

            trades.append({
                "exchange": "binance",
                "datetime": dt,
                "action": side,
                "currency": currency,
                "amount": amount,
                "price": price,
                "fee": fee,
            })
    except Exception as e:
        raise ValueError(f"Binance CSVのデータ解析中にエラーが発生しました：{e}")

    return trades
