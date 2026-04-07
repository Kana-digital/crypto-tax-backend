def calculate(trades):
    results = []
    holdings = {}

    sorted_trades = sorted(trades, key=lambda x: str(x["datetime"]))

    for trade in sorted_trades:
        currency = trade["currency"]
        if currency not in holdings:
            holdings[currency] = {"amount": 0.0, "cost": 0.0}

        # 数量・価格のバリデーション
        amount = float(trade.get("amount", 0))
        price = float(trade.get("price", 0))
        fee = float(trade.get("fee", 0))
        if amount <= 0 or price < 0:
            continue

        if trade["action"] in ["買い", "買", "buy", "BUY"]:
            holdings[currency]["amount"] += amount
            holdings[currency]["cost"] += amount * price + fee

        elif trade["action"] in ["売り", "売", "sell", "SELL"]:
            h = holdings[currency]
            if h["amount"] > 0:
                avg_price = h["cost"] / h["amount"]
            else:
                avg_price = 0

            # マイナス残高防止: 売却量が保有量を超える場合は保有量に制限
            actual_sell_amount = min(amount, h["amount"]) if h["amount"] > 0 else amount

            profit = (price - avg_price) * actual_sell_amount - fee
            h["cost"] = max(0, h["cost"] - avg_price * actual_sell_amount)
            h["amount"] = max(0, h["amount"] - actual_sell_amount)

            results.append({
                "exchange": trade["exchange"],
                "datetime": trade["datetime"],
                "currency": currency,
                "amount": actual_sell_amount,
                "sell_price": price,
                "avg_buy_price": avg_price,
                "profit": profit,
                "method": "移動平均法",
            })
    return results
