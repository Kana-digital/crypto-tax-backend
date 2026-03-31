def calculate(trades):
    results = []
    holdings = {}

    sorted_trades = sorted(trades, key=lambda x: x["datetime"])

    for trade in sorted_trades:
        currency = trade["currency"]
        if currency not in holdings:
            holdings[currency] = {"amount": 0.0, "cost": 0.0}

        if trade["action"] in ["買い", "買", "buy", "BUY"]:
            holdings[currency]["amount"] += trade["amount"]
            holdings[currency]["cost"] += trade["amount"] * trade["price"] + trade["fee"]

        elif trade["action"] in ["売り", "売", "sell", "SELL"]:
            if holdings[currency]["amount"] > 0:
                avg_price = holdings[currency]["cost"] / holdings[currency]["amount"]
            else:
                avg_price = 0
            profit = (trade["price"] - avg_price) * trade["amount"] - trade["fee"]
            holdings[currency]["cost"] -= avg_price * trade["amount"]
            holdings[currency]["amount"] -= trade["amount"]
            results.append({
                "exchange": trade["exchange"],
                "datetime": trade["datetime"],
                "currency": currency,
                "amount": trade["amount"],
                "sell_price": trade["price"],
                "avg_buy_price": avg_price,
                "profit": profit,
                "method": "移動平均法",
            })
    return results
