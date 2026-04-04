"""
Binance CSVパーサーのユニットテスト
"""
import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parsers import binance


class TestExtractCurrency(unittest.TestCase):
    """通貨ペアからの暗号資産名抽出テスト"""

    def test_slash_separated(self):
        self.assertEqual(binance.extract_currency("BTC/JPY"), "BTC")
        self.assertEqual(binance.extract_currency("ETH/USDT"), "ETH")

    def test_underscore_separated(self):
        self.assertEqual(binance.extract_currency("btc_jpy"), "BTC")

    def test_suffix_removal(self):
        self.assertEqual(binance.extract_currency("BTCJPY"), "BTC")
        self.assertEqual(binance.extract_currency("ETHUSDT"), "ETH")
        self.assertEqual(binance.extract_currency("XRPBUSD"), "XRP")
        self.assertEqual(binance.extract_currency("SOLBNB"), "SOL")

    def test_no_suffix(self):
        self.assertEqual(binance.extract_currency("BTC"), "BTC")


class TestNormalizeSide(unittest.TestCase):
    """売買方向の正規化テスト"""

    def test_buy_variants(self):
        self.assertEqual(binance.normalize_side("BUY"), "買い")
        self.assertEqual(binance.normalize_side("buy"), "買い")
        self.assertEqual(binance.normalize_side("買い"), "買い")

    def test_sell_variants(self):
        self.assertEqual(binance.normalize_side("SELL"), "売り")
        self.assertEqual(binance.normalize_side("sell"), "売り")
        self.assertEqual(binance.normalize_side("売り"), "売り")

    def test_unknown(self):
        self.assertIsNone(binance.normalize_side("transfer"))
        self.assertIsNone(binance.normalize_side(""))


class TestToFloat(unittest.TestCase):
    """数値変換テスト"""

    def test_normal(self):
        self.assertEqual(binance.to_float("1234.56"), 1234.56)

    def test_with_comma(self):
        self.assertEqual(binance.to_float("1,234.56"), 1234.56)

    def test_with_unit(self):
        self.assertAlmostEqual(binance.to_float("0.05 BTC"), 0.05)

    def test_invalid(self):
        self.assertEqual(binance.to_float("abc"), 0.0)
        self.assertEqual(binance.to_float(None), 0.0)


class TestBinanceSpotCSV(unittest.TestCase):
    """スポット取引履歴CSVのパーステスト"""

    def _write_csv(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
        f.write(content)
        f.close()
        return f.name

    def test_spot_format(self):
        csv = (
            "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
            "2025-01-15 10:30:00,BTCJPY,BUY,7000000,0.5,3500000,0.0005 BTC\n"
            "2025-02-20 14:00:00,BTCJPY,SELL,8000000,0.3,2400000,0.0003 BTC\n"
        )
        path = self._write_csv(csv)
        try:
            trades = binance.parse(path)
            self.assertEqual(len(trades), 2)
            # 買い
            self.assertEqual(trades[0]["exchange"], "binance")
            self.assertEqual(trades[0]["action"], "買い")
            self.assertEqual(trades[0]["currency"], "BTC")
            self.assertAlmostEqual(trades[0]["amount"], 0.5)
            self.assertAlmostEqual(trades[0]["price"], 7000000)
            self.assertAlmostEqual(trades[0]["fee"], 0.0005)
            # 売り
            self.assertEqual(trades[1]["action"], "売り")
            self.assertAlmostEqual(trades[1]["amount"], 0.3)
        finally:
            os.unlink(path)

    def test_new_format(self):
        csv = (
            "Date(UTC),OrderNo,Pair,Type,Side,Order Price,Order Amount,AvgTrading Price,Filled,Total,status\n"
            "2025-03-01,12345,ETH/USDT,LIMIT,BUY,3000,2.0,3000,2.0,6000,Filled\n"
            "2025-04-01,12346,ETH/USDT,LIMIT,SELL,3500,1.5,3500,1.5,5250,Filled\n"
        )
        path = self._write_csv(csv)
        try:
            trades = binance.parse(path)
            self.assertEqual(len(trades), 2)
            self.assertEqual(trades[0]["currency"], "ETH")
            self.assertEqual(trades[0]["action"], "買い")
            self.assertAlmostEqual(trades[0]["price"], 3000)
            self.assertAlmostEqual(trades[0]["amount"], 2.0)
        finally:
            os.unlink(path)

    def test_skip_unknown_side(self):
        csv = (
            "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
            "2025-01-15,BTCJPY,TRANSFER,7000000,0.5,3500000,0\n"
        )
        path = self._write_csv(csv)
        try:
            trades = binance.parse(path)
            self.assertEqual(len(trades), 0)
        finally:
            os.unlink(path)

    def test_non_binance_csv_raises(self):
        csv = "日付,種別,金額\n2025-01-01,入金,100000\n"
        path = self._write_csv(csv)
        try:
            with self.assertRaises(ValueError):
                binance.parse(path)
        finally:
            os.unlink(path)

    def test_empty_csv(self):
        csv = "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
        path = self._write_csv(csv)
        try:
            trades = binance.parse(path)
            self.assertEqual(len(trades), 0)
        finally:
            os.unlink(path)

    def test_multiple_currencies(self):
        csv = (
            "Date(UTC),Pair,Side,Price,Executed,Amount,Fee\n"
            "2025-01-01,BTCJPY,BUY,7000000,1.0,7000000,0\n"
            "2025-01-01,ETHUSDT,BUY,3000,5.0,15000,0\n"
            "2025-02-01,BTCJPY,SELL,8000000,0.5,4000000,0\n"
        )
        path = self._write_csv(csv)
        try:
            trades = binance.parse(path)
            self.assertEqual(len(trades), 3)
            currencies = [t["currency"] for t in trades]
            self.assertIn("BTC", currencies)
            self.assertIn("ETH", currencies)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
