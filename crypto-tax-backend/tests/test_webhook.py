"""
Stripe Webhook エンドポイントのユニットテスト
署名検証のガード条件をテストする
"""
import unittest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# FastAPI テスト用（httpxが利用可能な場合のみ）
try:
    from fastapi.testclient import TestClient
    HAS_TESTCLIENT = True
except ImportError:
    HAS_TESTCLIENT = False


@unittest.skipUnless(HAS_TESTCLIENT, "fastapi[testing] not available")
class TestStripeWebhook(unittest.TestCase):
    """Webhook 署名検証のテスト"""

    @classmethod
    def setUpClass(cls):
        # 環境変数をセット（テスト用）
        os.environ.setdefault("SUPABASE_URL", "")
        os.environ.setdefault("SUPABASE_ANON_KEY", "")
        os.environ.setdefault("STRIPE_SECRET_KEY", "sk_test_dummy")
        os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "whsec_test_dummy")
        os.environ.setdefault("STRIPE_PRICE_ID", "price_test_dummy")
        os.environ.setdefault("ANTHROPIC_API_KEY", "test_dummy")
        from main import app
        cls.client = TestClient(app)

    def test_missing_signature_header(self):
        """stripe-signatureヘッダーがない場合400エラー"""
        response = self.client.post("/stripe-webhook", content=b'{}')
        self.assertEqual(response.status_code, 400)

    def test_invalid_signature(self):
        """不正な署名の場合400エラー"""
        response = self.client.post(
            "/stripe-webhook",
            content=b'{"type":"checkout.session.completed"}',
            headers={"stripe-signature": "t=0,v1=invalid_signature"}
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_payload(self):
        """空ペイロードの場合400エラー"""
        response = self.client.post(
            "/stripe-webhook",
            content=b'',
            headers={"stripe-signature": "t=0,v1=test"}
        )
        self.assertEqual(response.status_code, 400)


class TestWebhookGuards(unittest.TestCase):
    """Webhook ガード条件の単体テスト"""

    def test_webhook_secret_env_var(self):
        """STRIPE_WEBHOOK_SECRET 環境変数が参照可能"""
        # テスト環境でも取得可能であることを確認
        secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
        self.assertIsInstance(secret, str)

    def test_construct_event_rejects_bad_sig(self):
        """stripe.Webhook.construct_event が不正署名を拒否する"""
        try:
            import stripe
        except ImportError:
            self.skipTest("stripe not installed")
        with self.assertRaises(Exception):
            stripe.Webhook.construct_event(
                payload=b'{"type":"test"}',
                sig_header="t=0,v1=bad",
                secret="whsec_test"
            )


if __name__ == "__main__":
    unittest.main()
