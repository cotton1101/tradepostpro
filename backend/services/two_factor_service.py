"""
TradePost Pro - 2段階認証（2FA）サービス
Google Authenticator / TOTP対応
"""

import hmac
import hashlib
import struct
import time
import base64
import secrets
import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from urllib.parse import quote


@dataclass
class TwoFactorSetup:
    """2FA設定データ"""
    user_id: str = ""
    secret_key: str = ""
    provisioning_uri: str = ""
    backup_codes: List[str] = field(default_factory=list)
    is_enabled: bool = False
    enabled_at: Optional[str] = None


class TwoFactorService:
    """2段階認証サービス"""

    APP_NAME = "TradePost Pro"
    CODE_DIGITS = 6
    CODE_INTERVAL = 30  # 秒
    CODE_WINDOW = 1     # 前後1ステップ許容
    BACKUP_CODE_COUNT = 10

    def __init__(self):
        self.user_secrets: Dict[str, TwoFactorSetup] = {}
        self.used_backup_codes: Dict[str, set] = {}

    # ============================================================
    # セットアップ
    # ============================================================

    def generate_setup(self, user_id: str, email: str) -> TwoFactorSetup:
        """2FAセットアップデータを生成"""
        # ランダムなシークレットキー生成（Base32）
        secret_bytes = secrets.token_bytes(20)
        secret_key = base64.b32encode(secret_bytes).decode("utf-8").rstrip("=")

        # プロビジョニングURI（QRコード用）
        provisioning_uri = (
            f"otpauth://totp/{quote(self.APP_NAME)}:{quote(email)}"
            f"?secret={secret_key}"
            f"&issuer={quote(self.APP_NAME)}"
            f"&digits={self.CODE_DIGITS}"
            f"&period={self.CODE_INTERVAL}"
        )

        # バックアップコード生成
        backup_codes = [
            f"{secrets.randbelow(10**8):08d}" for _ in range(self.BACKUP_CODE_COUNT)
        ]

        setup = TwoFactorSetup(
            user_id=user_id,
            secret_key=secret_key,
            provisioning_uri=provisioning_uri,
            backup_codes=backup_codes,
            is_enabled=False,
        )

        self.user_secrets[user_id] = setup
        self.used_backup_codes[user_id] = set()

        return setup

    def enable_2fa(self, user_id: str, verification_code: str) -> bool:
        """2FAを有効化（初回コード検証後）"""
        setup = self.user_secrets.get(user_id)
        if not setup:
            return False

        # コード検証
        if not self.verify_totp(setup.secret_key, verification_code):
            return False

        setup.is_enabled = True
        setup.enabled_at = datetime.now().isoformat()
        return True

    def disable_2fa(self, user_id: str) -> bool:
        """2FAを無効化"""
        setup = self.user_secrets.get(user_id)
        if not setup:
            return False

        setup.is_enabled = False
        return True

    # ============================================================
    # TOTP生成・検証
    # ============================================================

    def _generate_hotp(self, secret: str, counter: int) -> str:
        """HOTP（HMAC-based OTP）を生成"""
        # Base32デコード（パディング補完）
        secret_padded = secret + "=" * (8 - len(secret) % 8) if len(secret) % 8 != 0 else secret
        key = base64.b32decode(secret_padded.upper())

        # カウンターを8バイトに変換
        counter_bytes = struct.pack(">Q", counter)

        # HMAC-SHA1
        hmac_hash = hmac.new(key, counter_bytes, hashlib.sha1).digest()

        # Dynamic Truncation
        offset = hmac_hash[-1] & 0x0F
        truncated = struct.unpack(">I", hmac_hash[offset:offset + 4])[0] & 0x7FFFFFFF

        # 指定桁数に切り詰め
        code = truncated % (10 ** self.CODE_DIGITS)
        return f"{code:0{self.CODE_DIGITS}d}"

    def generate_totp(self, secret: str, timestamp: Optional[int] = None) -> str:
        """TOTP（Time-based OTP）を生成"""
        if timestamp is None:
            timestamp = int(time.time())
        counter = timestamp // self.CODE_INTERVAL
        return self._generate_hotp(secret, counter)

    def verify_totp(self, secret: str, code: str, timestamp: Optional[int] = None) -> bool:
        """TOTPコードを検証（前後ウィンドウ許容）"""
        if timestamp is None:
            timestamp = int(time.time())

        for offset in range(-self.CODE_WINDOW, self.CODE_WINDOW + 1):
            check_time = timestamp + (offset * self.CODE_INTERVAL)
            expected = self.generate_totp(secret, check_time)
            if hmac.compare_digest(code, expected):
                return True

        return False

    # ============================================================
    # 認証
    # ============================================================

    def verify_login(self, user_id: str, code: str) -> Dict:
        """ログイン時の2FA検証"""
        setup = self.user_secrets.get(user_id)
        if not setup or not setup.is_enabled:
            return {"success": True, "method": "2fa_not_enabled"}

        # TOTPコード検証
        if self.verify_totp(setup.secret_key, code):
            return {"success": True, "method": "totp"}

        # バックアップコード検証
        if code in setup.backup_codes and code not in self.used_backup_codes.get(user_id, set()):
            self.used_backup_codes[user_id].add(code)
            remaining = len(setup.backup_codes) - len(self.used_backup_codes[user_id])
            return {
                "success": True,
                "method": "backup_code",
                "remaining_backup_codes": remaining,
                "warning": f"バックアップコードの残り: {remaining}個" if remaining <= 3 else None,
            }

        return {"success": False, "method": "invalid_code"}

    def get_status(self, user_id: str) -> Dict:
        """2FAステータス取得"""
        setup = self.user_secrets.get(user_id)
        if not setup:
            return {"enabled": False, "setup_completed": False}

        used_codes = len(self.used_backup_codes.get(user_id, set()))
        return {
            "enabled": setup.is_enabled,
            "setup_completed": True,
            "enabled_at": setup.enabled_at,
            "backup_codes_remaining": len(setup.backup_codes) - used_codes,
            "backup_codes_total": len(setup.backup_codes),
        }

    def regenerate_backup_codes(self, user_id: str) -> Optional[List[str]]:
        """バックアップコードを再生成"""
        setup = self.user_secrets.get(user_id)
        if not setup:
            return None

        setup.backup_codes = [
            f"{secrets.randbelow(10**8):08d}" for _ in range(self.BACKUP_CODE_COUNT)
        ]
        self.used_backup_codes[user_id] = set()
        return setup.backup_codes


# テスト用
if __name__ == "__main__":
    service = TwoFactorService()

    # セットアップ
    setup = service.generate_setup("user_001", "test@example.com")
    print(f"シークレットキー: {setup.secret_key}")
    print(f"プロビジョニングURI: {setup.provisioning_uri[:80]}...")
    print(f"バックアップコード: {setup.backup_codes[:3]}... (計{len(setup.backup_codes)}個)")

    # TOTP生成・検証
    code = service.generate_totp(setup.secret_key)
    print(f"\n現在のTOTPコード: {code}")

    # 有効化
    result = service.enable_2fa("user_001", code)
    print(f"2FA有効化: {'成功' if result else '失敗'}")

    # ログイン検証（正しいコード）
    current_code = service.generate_totp(setup.secret_key)
    verify = service.verify_login("user_001", current_code)
    print(f"\nログイン検証（TOTP）: {verify}")

    # バックアップコードでログイン
    backup = setup.backup_codes[0]
    verify_backup = service.verify_login("user_001", backup)
    print(f"ログイン検証（バックアップ）: {verify_backup}")

    # 不正コードでログイン
    verify_invalid = service.verify_login("user_001", "000000")
    print(f"ログイン検証（不正）: {verify_invalid}")

    # ステータス確認
    status = service.get_status("user_001")
    print(f"\n2FAステータス: {json.dumps(status, indent=2, ensure_ascii=False)}")

    print("\n✓ 2段階認証サービス テスト完了")
