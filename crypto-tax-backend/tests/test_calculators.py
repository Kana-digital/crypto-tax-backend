"""
損益計算ロジック（total_average / moving_average）のユニットテスト
"""
import unittest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from calculators import total_average, moving_average


def make_trade(action, currency="BTC", amount=1.0, price=5000000, fee=0, exchange="Coincheck", dt="2025-01-01"):
    return {
        "action": action,
        "currency": currency,
        "amount": amount,
        "price": price,
        "fee": fee,
        "exchange": exchange,
        "datetime": dt,
    }


class TestTotalAverage(unittest.TestCase):
    """総平均法のテスト"""

    def test_empty_trades(self):
        self.assertEqual(total_average.calculate([]), [])

    def test_buy_only_no_result(self):
        trades = [make_trade("買い", amount=1.0, price=5000000)]
        result = total_average.calculate(trades)
        self.assertEqual(len(result), 0)

    def test_simple_profit(self):
        trades = [
            make_trade("買い", amount=1.0, price=4000000),
            make_trade("売り", amount=0.5, price=5000000),
        ]
        result = total_average.calculate(trades)
        self.assertEqual(len(result), 1)
        r = result[0]
        self.assertEqual(r["currency"], "BTC")
        self.assertEqual(r["amount"], 0.5)
        self.assertEqual(r["sell_price"], 5000000)
        self.assertEqual(r["avg_buy_price"], 4000000)
        # profit = (5000000 - 4000000) * 0.5 - 0 = 500000
        self.assertAlmostEqual(r["profit"], 500000)

    def test_simple_loss(self):
        trades = [
            make_trade("買い", amount=1.0, price=6000000),
            make_trade("売り", amount=1.0, price=4000000),
        ]
        result = total_average.calculate(trades)
        self.assertAlmostEqual(result[0]["profit"], -2000000)

    def test_multiple_buys_average(self):
        trades = [
            make_trade("買い", amount=1.0, price=4000000),
            make_trade("買い", amount=1.0, price=6000000),
            make_trade("売り", amount=1.0, price=5500000),
        ]
        result = total_average.calculate(trades)
        # avg = (4000000+6000000)/2 = 5000000
        self.assertAlmostEqual(result[0]["avg_buy_price"], 5000000)
        # profit = (5500000 - 5000000) * 1.0 = 500000
        self.assertAlmostEqual(result[0]["profit"], 500000)

    def test_fee_deducted(self):
        trades = [
            make_trade("買い", amount=1.0, price=5000000, fee=10000),
            make_trade("売り", amount=1.0, price=6000000, fee=5000),
        ]
        result = total_average.calculate(trades)
        # avg_buy = (5000000 + 10000) / 1.0 = 5010000
        # profit = (6000000 - 5010000) * 1.0 - 5000 = 985000
        self.assertAlmostEqual(result[0]["profit"], 985000)

    def test_multiple_currencies(self):
        trades = [
            make_trade("買い", currency="BTC", amount=1.0, price=5000000),
            make_trade("買い", currency="ETH", amount=10.0, price=300000),
            make_trade("売り", currency="BTC", amount=0.5, price=6000000),
            make_trade("売り", currency="ETH", amount=5.0, price=350000),
        ]
        result = total_average.calculate(trades)
        self.assertEqual(len(result), 2)
        btc_result = [r for r in result if r["currency"] == "BTC"][0]
        eth_result = [r for r in result if r["currency"] == "ETH"][0]
        self.assertAlmostEqual(btc_result["profit"], 500000)
        self.assertAlmostEqual(eth_result["profit"], 250000)

    def test_action_variants(self):
        """日本語/英語のアクション表記を確認"""
        for buy_action in ["買い", "買", "buy", "BUY"]:
            for sell_action in ["売り", "売", "sell", "SELL"]:
                trades = [
                    make_trade(buy_action, amount=1.0, price=4000000),
                    make_trade(sell_action, amount=1.0, price=5000000),
                ]
                result = total_average.calculate(trades)
                self.assertEqual(len(result), 1, f"{buy_action}/{sell_action}")
                self.assertAlmostEqual(result[0]["profit"], 1000000, msg=f"{buy_action}/{sell_action}")


class TestMovingAverage(unittest.TestCase):
    """移動平均法のテスト"""

    def test_empty_trades(self):
        self.assertEqual(moving_average.calculate([]), [])

    def test_simple_profit(self):
        trades = [
            make_trade("買い", amount=1.0, price=4000000, dt="2025-01-01"),
            make_trade("売り", amount=0.5, price=5000000, dt="2025-02-01"),
        ]
        result = moving_average.calculate(trades)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["avg_buy_price"], 4000000)
        self.assertAlmostEqual(result[0]["profit"], 500000)

    def test_moving_avg_updates_after_each_buy(self):
        """移動平均は追加購入のたびに再計算"""
        trades = [
            make_trade("買い", amount=1.0, price=4000000, dt="2025-01-01"),
            make_trade("買い", amount=1.0, price=6000000, dt="2025-02-01"),
            make_trade("売り", amount=1.0, price=5500000, dt="2025-03-01"),
        ]
        result = moving_average.calculate(trades)
        # avg = (4000000+6000000)/2 = 5000000
        self.assertAlmostEqual(result[0]["avg_buy_price"], 5000000)
        self.assertAlmostEqual(result[0]["profit"], 500000)

    def test_sell_reduces_holdings(self):
        """売却後の残高で次の平均価格が計算される"""
        trades = [
            make_trade("買い", amount=2.0, price=4000000, dt="2025-01-01"),
            make_trade("売り", amount=1.0, price=5000000, dt="2025-02-01"),
            make_trade("買い", amount=1.0, price=6000000, dt="2025-03-01"),
            make_trade("売り", amount=1.0, price=5500000, dt="2025-04-01"),
        ]
        result = moving_average.calculate(trades)
        self.assertEqual(len(result), 2)
        # 1回目: avg=4000000, profit=(5000000-4000000)*1.0=1000000
        self.assertAlmostEqual(result[0]["profit"], 1000000)
        # 2回目: 残高=1BTC@4000000 + 1BTC@6000000 → avg=(4000000+6000000)/2=5000000
        self.assertAlmostEqual(result[1]["avg_buy_price"], 5000000)

    def test_chronological_order(self):
        """日時順に自動ソートされて計算される"""
        trades = [
            make_trade("売り", amount=1.0, price=5000000, dt="2025-02-01"),
            make_trade("買い", amount=1.0, price=4000000, dt="2025-01-01"),
        ]
        result = moving_average.calculate(trades)
        self.assertEqual(len(result), 1)
        self.assertAlmostEqual(result[0]["avg_buy_price"], 4000000)

    def test_method_label(self):
        trades = [
            make_trade("買い", amount=1.0, price=4000000, dt="2025-01-01"),
            make_trade("売り", amount=1.0, price=5000000, dt="2025-02-01"),
        ]
        result = moving_average.calculate(trades)
        self.assertEqual(result[0]["method"], "移動平均法")

    def test_total_avg_method_label(self):
        trades = [
            make_trade("買い", amount=1.0, price=4000000),
            make_trade("売り", amount=1.0, price=5000000),
        ]
        result = total_average.calculate(trades)
        self.assertEqual(result[0]["method"], "総平均法")


if __name__ == "__main__":
    unittest.main()
