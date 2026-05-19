"""
高度なレート制限サービス
トークンバケットアルゴリズムによるAPI保護
"""

import time
import threading
from datetime import datetime
from typing import Optional, Dict, Tuple
from dataclasses import dataclass, field
from enum import Enum


class RateLimitTier(Enum):
    """レート制限ティア"""
    FREE = "free"
    LIGHT = "light"
    STANDARD = "standard"
    PREMIUM = "premium"
    API_KEY = "api_key"
    ADMIN = "admin"


@dataclass
class TokenBucket:
    """トークンバケット"""
    capacity: int           # バケット容量
    tokens: float           # 現在のトークン数
    refill_rate: float      # 秒あたりのリフィルレート
    last_refill: float      # 最後のリフィル時刻
    total_requests: int = 0
    total_rejected: int = 0

    def consume(self, tokens: int = 1) -> Tuple[bool, dict]:
        """トークンを消費"""
        now = time.time()
        # トークンをリフィル
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        self.total_requests += 1

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True, {
                "allowed": True,
                "remaining": int(self.tokens),
                "limit": self.capacity,
                "reset": int(now + (self.capacity - self.tokens) / self.refill_rate),
                "retry_after": 0,
            }
        else:
            self.total_rejected += 1
            wait_time = (tokens - self.tokens) / self.refill_rate
            return False, {
                "allowed": False,
                "remaining": 0,
                "limit": self.capacity,
                "reset": int(now + wait_time),
                "retry_after": round(wait_time, 2),
            }


@dataclass
class SlidingWindowCounter:
    """スライディングウィンドウカウンター"""
    window_size: int         # ウィンドウサイズ（秒）
    max_requests: int        # ウィンドウ内の最大リクエスト数
    requests: list = field(default_factory=list)

    def allow(self) -> Tuple[bool, dict]:
        """リクエストを許可するか判定"""
        now = time.time()
        # 期限切れのリクエストを削除
        self.requests = [t for t in self.requests if now - t < self.window_size]

        if len(self.requests) < self.max_requests:
            self.requests.append(now)
            return True, {
                "allowed": True,
                "remaining": self.max_requests - len(self.requests),
                "limit": self.max_requests,
                "window": self.window_size,
                "reset": int(now + self.window_size),
            }
        else:
            oldest = self.requests[0]
            retry_after = self.window_size - (now - oldest)
            return False, {
                "allowed": False,
                "remaining": 0,
                "limit": self.max_requests,
                "window": self.window_size,
                "reset": int(oldest + self.window_size),
                "retry_after": round(retry_after, 2),
            }


class RateLimiterService:
    """高度なレート制限サービス"""

    # プラン別のレート制限設定
    TIER_LIMITS = {
        RateLimitTier.FREE: {
            "api_requests": {"capacity": 30, "refill_rate": 0.5},        # 30/min
            "post_creation": {"capacity": 5, "refill_rate": 0.003},      # 5/day
            "image_generation": {"capacity": 10, "refill_rate": 0.007},  # 10/day
        },
        RateLimitTier.LIGHT: {
            "api_requests": {"capacity": 60, "refill_rate": 1.0},        # 60/min
            "post_creation": {"capacity": 20, "refill_rate": 0.014},     # 20/day
            "image_generation": {"capacity": 50, "refill_rate": 0.035},  # 50/day
            "video_generation": {"capacity": 0, "refill_rate": 0},       # 不可
        },
        RateLimitTier.STANDARD: {
            "api_requests": {"capacity": 120, "refill_rate": 2.0},       # 120/min
            "post_creation": {"capacity": 50, "refill_rate": 0.035},     # 50/day
            "image_generation": {"capacity": 100, "refill_rate": 0.07},  # 100/day
            "video_generation": {"capacity": 10, "refill_rate": 0.007},  # 10/day
        },
        RateLimitTier.PREMIUM: {
            "api_requests": {"capacity": 300, "refill_rate": 5.0},       # 300/min
            "post_creation": {"capacity": 200, "refill_rate": 0.14},     # 200/day
            "image_generation": {"capacity": 500, "refill_rate": 0.35},  # 500/day
            "video_generation": {"capacity": 50, "refill_rate": 0.035},  # 50/day
        },
        RateLimitTier.API_KEY: {
            "api_requests": {"capacity": 600, "refill_rate": 10.0},      # 600/min
            "post_creation": {"capacity": 500, "refill_rate": 0.35},     # 500/day
            "image_generation": {"capacity": 1000, "refill_rate": 0.7},  # 1000/day
            "video_generation": {"capacity": 100, "refill_rate": 0.07},  # 100/day
        },
        RateLimitTier.ADMIN: {
            "api_requests": {"capacity": 10000, "refill_rate": 100.0},
            "post_creation": {"capacity": 10000, "refill_rate": 100.0},
            "image_generation": {"capacity": 10000, "refill_rate": 100.0},
            "video_generation": {"capacity": 10000, "refill_rate": 100.0},
        },
    }

    # エンドポイント別のコスト
    ENDPOINT_COSTS = {
        "/api/v1/posts": 1,
        "/api/v1/posts/create": 5,
        "/api/v1/images/generate": 10,
        "/api/v1/videos/generate": 50,
        "/api/v1/ai/generate": 20,
        "/api/v1/stats": 1,
        "/api/v1/users/profile": 1,
        "/graphql": 2,
    }

    def __init__(self):
        self._buckets: Dict[str, Dict[str, TokenBucket]] = {}
        self._ip_windows: Dict[str, SlidingWindowCounter] = {}
        self._lock = threading.Lock()

        # グローバルIP制限
        self._global_ip_limit = 1000  # 1000 req/min per IP
        self._global_ip_window = 60   # 60秒ウィンドウ

    def _get_or_create_bucket(self, identifier: str, resource: str, tier: RateLimitTier) -> TokenBucket:
        """バケットを取得または作成"""
        with self._lock:
            if identifier not in self._buckets:
                self._buckets[identifier] = {}

            if resource not in self._buckets[identifier]:
                limits = self.TIER_LIMITS.get(tier, self.TIER_LIMITS[RateLimitTier.FREE])
                resource_limits = limits.get(resource, {"capacity": 30, "refill_rate": 0.5})
                self._buckets[identifier][resource] = TokenBucket(
                    capacity=resource_limits["capacity"],
                    tokens=resource_limits["capacity"],
                    refill_rate=resource_limits["refill_rate"],
                    last_refill=time.time(),
                )
            return self._buckets[identifier][resource]

    def _get_or_create_ip_window(self, ip: str) -> SlidingWindowCounter:
        """IP用のスライディングウィンドウを取得または作成"""
        with self._lock:
            if ip not in self._ip_windows:
                self._ip_windows[ip] = SlidingWindowCounter(
                    window_size=self._global_ip_window,
                    max_requests=self._global_ip_limit,
                )
            return self._ip_windows[ip]

    def check_rate_limit(
        self,
        user_id: str,
        tier: RateLimitTier,
        resource: str = "api_requests",
        endpoint: str = None,
        ip: str = None,
    ) -> Tuple[bool, dict]:
        """レート制限をチェック"""
        # IP制限チェック
        if ip:
            ip_window = self._get_or_create_ip_window(ip)
            ip_allowed, ip_info = ip_window.allow()
            if not ip_allowed:
                return False, {
                    **ip_info,
                    "reason": "ip_rate_limit",
                    "message": "IPアドレスのレート制限に達しました",
                }

        # エンドポイントコスト計算
        cost = 1
        if endpoint:
            cost = self.ENDPOINT_COSTS.get(endpoint, 1)

        # ユーザーバケットチェック
        bucket = self._get_or_create_bucket(user_id, resource, tier)
        allowed, info = bucket.consume(cost)

        if not allowed:
            info["reason"] = "user_rate_limit"
            info["message"] = f"レート制限に達しました。{info['retry_after']}秒後に再試行してください。"
            info["tier"] = tier.value

        return allowed, info

    def get_rate_limit_headers(self, info: dict) -> dict:
        """レート制限のHTTPヘッダーを生成"""
        return {
            "X-RateLimit-Limit": str(info.get("limit", 0)),
            "X-RateLimit-Remaining": str(info.get("remaining", 0)),
            "X-RateLimit-Reset": str(info.get("reset", 0)),
            "Retry-After": str(info.get("retry_after", 0)) if not info.get("allowed") else "",
        }

    def get_user_limits(self, user_id: str) -> dict:
        """ユーザーの現在のレート制限状態を取得"""
        result = {}
        if user_id in self._buckets:
            for resource, bucket in self._buckets[user_id].items():
                # リフィル計算
                now = time.time()
                elapsed = now - bucket.last_refill
                current_tokens = min(bucket.capacity, bucket.tokens + elapsed * bucket.refill_rate)
                result[resource] = {
                    "capacity": bucket.capacity,
                    "remaining": int(current_tokens),
                    "refill_rate": bucket.refill_rate,
                    "total_requests": bucket.total_requests,
                    "total_rejected": bucket.total_rejected,
                }
        return result

    def get_global_stats(self) -> dict:
        """グローバル統計を取得"""
        total_users = len(self._buckets)
        total_requests = sum(
            bucket.total_requests
            for user_buckets in self._buckets.values()
            for bucket in user_buckets.values()
        )
        total_rejected = sum(
            bucket.total_rejected
            for user_buckets in self._buckets.values()
            for bucket in user_buckets.values()
        )
        return {
            "total_users_tracked": total_users,
            "total_ips_tracked": len(self._ip_windows),
            "total_requests": total_requests,
            "total_rejected": total_rejected,
            "rejection_rate": (total_rejected / total_requests * 100) if total_requests > 0 else 0,
        }

    def reset_user_limits(self, user_id: str) -> bool:
        """ユーザーのレート制限をリセット"""
        with self._lock:
            if user_id in self._buckets:
                del self._buckets[user_id]
                return True
        return False

    def cleanup_expired(self) -> int:
        """期限切れのエントリをクリーンアップ"""
        cleaned = 0
        now = time.time()
        with self._lock:
            # 古いIPウィンドウを削除
            expired_ips = [
                ip for ip, window in self._ip_windows.items()
                if not window.requests or (now - max(window.requests)) > window.window_size * 2
            ]
            for ip in expired_ips:
                del self._ip_windows[ip]
                cleaned += 1
        return cleaned


# テスト実行
if __name__ == "__main__":
    service = RateLimiterService()

    print("=== トークンバケット レート制限テスト ===")

    # Premiumユーザーのテスト
    print("\n--- Premiumユーザー ---")
    for i in range(5):
        allowed, info = service.check_rate_limit(
            "user_premium",
            RateLimitTier.PREMIUM,
            "api_requests",
            endpoint="/api/v1/stats",
            ip="192.168.1.1",
        )
        print(f"  リクエスト {i+1}: {'許可' if allowed else '拒否'} (残り: {info['remaining']})")

    # Freeユーザーのテスト（制限に達するまで）
    print("\n--- Freeユーザー（高コストエンドポイント）---")
    for i in range(8):
        allowed, info = service.check_rate_limit(
            "user_free",
            RateLimitTier.FREE,
            "api_requests",
            endpoint="/api/v1/ai/generate",  # コスト20
        )
        status = "許可" if allowed else "拒否"
        print(f"  リクエスト {i+1}: {status} (残り: {info['remaining']}, retry_after: {info.get('retry_after', 0)}s)")

    # レート制限ヘッダー
    print("\n--- HTTPヘッダー ---")
    _, last_info = service.check_rate_limit("user_test", RateLimitTier.STANDARD, "api_requests")
    headers = service.get_rate_limit_headers(last_info)
    for key, value in headers.items():
        if value:
            print(f"  {key}: {value}")

    # ユーザー制限状態
    print("\n--- ユーザー制限状態 ---")
    limits = service.get_user_limits("user_premium")
    for resource, info in limits.items():
        print(f"  {resource}: {info['remaining']}/{info['capacity']} (リクエスト: {info['total_requests']}, 拒否: {info['total_rejected']})")

    # グローバル統計
    print("\n--- グローバル統計 ---")
    stats = service.get_global_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # スライディングウィンドウテスト
    print("\n=== スライディングウィンドウテスト ===")
    window = SlidingWindowCounter(window_size=1, max_requests=3)
    for i in range(5):
        allowed, info = window.allow()
        print(f"  リクエスト {i+1}: {'許可' if allowed else '拒否'} (残り: {info['remaining']})")

    print("\n✓ レート制限サービス テスト完了")
