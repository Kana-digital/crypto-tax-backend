def calculate(trades):
    results = []
    holdings = {}

    for trade in trades:
        currency = trade["currency"]
        if currency not in holdings:
            holdings[currency] = {"total_amount": 0.0, "total_cost": 0.0}
        if trade["action"] in ["買い", "買", "buy", "BUY"]:
            holdings[currency]["total_amount"] += trade["amount"]
            holdings[currency]["total_cost"] += trade["amount"] * trade["price"] + trade["fee"]

    avg_prices = {}
    for currency, h in holdings.items():
        if h["total_amount"] > 0:
            avg_prices[currency] = h["total_cost"] / h["total_amount"]

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
