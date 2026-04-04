"""
Supabase Auth 認証モジュールのユニットテスト
"""
import unittest
import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import jwt as pyjwt
    HAS_JWT = True
except ImportError:
    HAS_JWT = False

try:
    import fastapi
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False


@unittest.skipUnless(HAS_JWT and HAS_FASTAPI, "PyJWT or FastAPI not installed")
class TestAuthModule(unittest.TestCase):
    """auth.py の単体テスト"""

    TEST_SECRET = "test-jwt-secret-for-unit-tests-only"

    @classmethod
    def setUpClass(cls):
        os.environ["SUPABASE_JWT_SECRET"] = cls.TEST_SECRET
        # auth モジュールをリロード
        if "auth" in sys.modules:
            del sys.modules["auth"]
        from auth import _decode_token, _extract_user, AuthUser
        cls._decode_token = staticmethod(_decode_token)
        cls._extract_user = staticmethod(_extract_user)
        cls.AuthUser = AuthUser

    def _make_token(self, payload: dict, secret: str = None) -> str:
        secret = secret or self.TEST_SECRET
        return pyjwt.encode(payload, secret, algorithm="HS256")

    def test_valid_token(self):
        """正常なトークンが通る"""
        token = self._make_token({
            "sub": "user-123",
            "email": "test@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        })
        payload = self._decode_token(token)
        self.assertEqual(payload["sub"], "user-123")
        self.assertEqual(payload["email"], "test@example.com")

    def test_expired_token(self):
        """期限切れトークンは401"""
        from fastapi import HTTPException
        token = self._make_token({
            "sub": "user-123",
            "aud": "authenticated",
            "exp": int(time.time()) - 100,
        })
        with self.assertRaises(HTTPException) as ctx:
            self._decode_token(token)
        self.assertEqual(ctx.exception.status_code, 401)
        self.assertIn("有効期限", ctx.exception.detail)

    def test_wrong_secret(self):
        """別のシークレットで署名されたトークンは401"""
        from fastapi import HTTPException
        token = self._make_token({
            "sub": "user-123",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }, secret="wrong-secret")
        with self.assertRaises(HTTPException) as ctx:
            self._decode_token(token)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_extract_user(self):
        """ペイロードからAuthUserを生成"""
        payload = {"sub": "user-456", "email": "user@test.com", "role": "authenticated"}
        user = self._extract_user(payload)
        self.assertEqual(user.id, "user-456")
        self.assertEqual(user.email, "user@test.com")
        self.assertEqual(user.role, "authenticated")

    def test_extract_user_missing_sub(self):
        """subがないペイロードは401"""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self._extract_user({"email": "test@example.com"})
        self.assertEqual(ctx.exception.status_code, 401)

    def test_extract_user_default_role(self):
        """roleがない場合はデフォルト値"""
        user = self._extract_user({"sub": "user-789"})
        self.assertEqual(user.role, "authenticated")
        self.assertIsNone(user.email)

    def test_no_secret_configured(self):
        """SUPABASE_JWT_SECRET未設定時は503"""
        from fastapi import HTTPException
        original = os.environ.get("SUPABASE_JWT_SECRET", "")
        os.environ["SUPABASE_JWT_SECRET"] = ""
        # リロード
        if "auth" in sys.modules:
            del sys.modules["auth"]
        from auth import _decode_token
        token = self._make_token({
            "sub": "user-123",
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        })
        with self.assertRaises(HTTPException) as ctx:
            _decode_token(token)
        self.assertEqual(ctx.exception.status_code, 503)
        # 元に戻す
        os.environ["SUPABASE_JWT_SECRET"] = original

    def test_authuser_dataclass(self):
        """AuthUser のフィールドが正しい"""
        user = self.AuthUser(id="abc", email="test@test.com", role="admin")
        self.assertEqual(user.id, "abc")
        self.assertEqual(user.email, "test@test.com")
        self.assertEqual(user.role, "admin")


if __name__ == "__main__":
    unittest.main()
