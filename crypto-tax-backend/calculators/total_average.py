def calculate(trades):
    results = []
    holdings = {}
    warnings = []

    for trade in trades:
        currency = trade["currency"]
        if currency not in holdings:
            holdings[currency] = {"total_amount": 0.0, "total_cost": 0.0}

        # 数量・価格のバリデーション
        amount = float(trade.get("amount", 0))
        price = float(trade.get("price", 0))
        fee = float(trade.get("fee", 0))
        if amount <= 0 or price < 0:
            continue

        if trade["action"] in ["買い", "買", "buy", "BUY"]:
            holdings[currency]["total_amount"] += amount
            holdings[currency]["total_cost"] += amount * price + fee

    avg_prices = {}
    for currency, h in holdings.items():
        if h["total_amount"] > 0:
            avg_prices[currency] = h["total_cost"] / h["total_amount"]

    for trade in trades:
        currency = trade["currency"]
        amount = float(trade.get("amount", 0))
        price = float(trade.get("price", 0))
        fee = float(trade.get("fee", 0))
        if amount <= 0 or price < 0:
            continue

        if trade["action"] in ["売り", "売", "sell", "SELL"]:
            avg_price = avg_prices.get(currency, 0)
            profit = (price - avg_price) * amount - fee
            results.append({
                "exchange": trade["exchange"],
                "datetime": trade["datetime"],
                "currency": currency,
                "amount": amount,
                "sell_price": price,
                "avg_buy_price": avg_price,
                "profit": profit,
                "method": "総平均法",
            })
    return results
