def calculate(trades: list[dict]) -> list[dict]:
    """総平均法で損益計算する"""
    results = []
    holdings = {}  # 通貨ごとの保有情報

    # 通貨ごとに買い取引を集計して平均単価を計算
    for trade in trades:
        currency = trade["currency"]
        if currency not in holdings:
            holdings[currency] = {"total_amount": 0.0, "total_cost": 0.0}

        if trade["action"] in ["買い", "買", "buy", "BUY"]:
            holdings[currency]["total_amount"] += trade["amount"]
            holdings[currency]["total_cost"] += trade["amount"] * trade["price"] + trade["fee"]

    # 平均単価を計算
    avg_prices = {}
    for currency, h in holdings.items():
        if h["total_amount"] > 0:
            avg_prices[currency] = h["total_cost"] / h["total_amount"]

    # 売り取引で損益を計算
    for trade in trades:
        currency = trade["currency"]
        if trade["action"] in ["売り", "売", "sell", "SELL"]:
            avg_price = avg_prices.get(currency, 0)
            profit = (trade["price"] - avg_price) * trade["amount"] - trade["fee"]
            results.append({
                "exchange": trade["exchange"],
                "datetime": trade["datetime"],
                "currency": currency,
                "amount": trade["amount"],
                "sell_price": trade["price"],
                "avg_buy_price": avg_price,
                "profit": profit,
                "method": "総平均法",
            })

    return results
