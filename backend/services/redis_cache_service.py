"""
Redisキャッシュ層サービス
API高速化のためのキャッシュ管理
Redis非接続時はインメモリフォールバック対応
"""

import json
import time
import hashlib
import functools
from datetime import datetime, timedelta
from typing import Optional, Any, Callable
from dataclasses import dataclass, field


@dataclass
class CacheEntry:
    """キャッシュエントリ"""
    key: str
    value: Any
    ttl: int  # seconds
    created_at: float
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.created_at > self.ttl


class InMemoryCache:
    """インメモリキャッシュ（Redis非接続時のフォールバック）"""

    def __init__(self, max_size: int = 10000):
        self._cache: dict = {}
        self._max_size = max_size
        self._stats = {"hits": 0, "misses": 0, "sets": 0, "deletes": 0}

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is None:
            self._stats["misses"] += 1
            return None
        if entry.is_expired:
            del self._cache[key]
            self._stats["misses"] += 1
            return None
        entry.hits += 1
        self._stats["hits"] += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        if len(self._cache) >= self._max_size:
            self._evict()
        self._cache[key] = CacheEntry(
            key=key,
            value=value,
            ttl=ttl,
            created_at=time.time(),
        )
        self._stats["sets"] += 1
        return True

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            self._stats["deletes"] += 1
            return True
        return False

    def delete_pattern(self, pattern: str) -> int:
        """パターンに一致するキーを削除"""
        import re
        regex = re.compile(pattern.replace("*", ".*"))
        keys_to_delete = [k for k in self._cache if regex.match(k)]
        for key in keys_to_delete:
            del self._cache[key]
        self._stats["deletes"] += len(keys_to_delete)
        return len(keys_to_delete)

    def exists(self, key: str) -> bool:
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            return True
        return False

    def ttl(self, key: str) -> int:
        """残りTTLを返す"""
        entry = self._cache.get(key)
        if entry and not entry.is_expired:
            remaining = entry.ttl - (time.time() - entry.created_at)
            return max(0, int(remaining))
        return -1

    def flush(self) -> bool:
        self._cache.clear()
        return True

    def size(self) -> int:
        return len(self._cache)

    def get_stats(self) -> dict:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "total_requests": total,
            "hit_rate": (self._stats["hits"] / total * 100) if total > 0 else 0,
            "cache_size": len(self._cache),
            "max_size": self._max_size,
        }

    def _evict(self):
        """LRU風の削除（期限切れ優先、次にヒット数が少ないもの）"""
        # まず期限切れを削除
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired:
            del self._cache[key]

        # まだ溢れている場合はヒット数が少ないものを削除
        if len(self._cache) >= self._max_size:
            sorted_entries = sorted(self._cache.items(), key=lambda x: x[1].hits)
            to_remove = len(self._cache) - self._max_size + 100  # 100個余裕を持たせる
            for key, _ in sorted_entries[:to_remove]:
                del self._cache[key]


class RedisCacheService:
    """Redisキャッシュサービス"""

    # キャッシュキープレフィックス
    PREFIX = "tradepost:"

    # デフォルトTTL（秒）
    TTL_SHORT = 60          # 1分
    TTL_MEDIUM = 300        # 5分
    TTL_LONG = 3600         # 1時間
    TTL_DAILY = 86400       # 24時間
    TTL_WEEKLY = 604800     # 7日

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.redis_url = self.config.get("redis_url", "redis://localhost:6379/0")
        self._redis = None
        self._fallback = InMemoryCache(max_size=self.config.get("max_cache_size", 10000))
        self._use_redis = False

        # Redis接続を試行
        self._try_connect_redis()

    def _try_connect_redis(self):
        """Redis接続を試行"""
        try:
            import redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
            self._redis.ping()
            self._use_redis = True
        except Exception:
            self._use_redis = False
            self._redis = None

    @property
    def backend(self) -> str:
        return "redis" if self._use_redis else "memory"

    def _make_key(self, *parts) -> str:
        """キャッシュキーを生成"""
        return self.PREFIX + ":".join(str(p) for p in parts)

    def get(self, key: str) -> Optional[Any]:
        """キャッシュから値を取得"""
        full_key = self._make_key(key)
        if self._use_redis:
            try:
                value = self._redis.get(full_key)
                if value:
                    return json.loads(value)
                return None
            except Exception:
                pass
        return self._fallback.get(full_key)

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """キャッシュに値を設定"""
        full_key = self._make_key(key)
        ttl = ttl or self.TTL_MEDIUM
        if self._use_redis:
            try:
                self._redis.setex(full_key, ttl, json.dumps(value, ensure_ascii=False, default=str))
                return True
            except Exception:
                pass
        return self._fallback.set(full_key, value, ttl)

    def delete(self, key: str) -> bool:
        """キャッシュから値を削除"""
        full_key = self._make_key(key)
        if self._use_redis:
            try:
                return bool(self._redis.delete(full_key))
            except Exception:
                pass
        return self._fallback.delete(full_key)

    def invalidate_pattern(self, pattern: str) -> int:
        """パターンに一致するキャッシュを無効化"""
        full_pattern = self._make_key(pattern)
        if self._use_redis:
            try:
                keys = self._redis.keys(full_pattern)
                if keys:
                    return self._redis.delete(*keys)
                return 0
            except Exception:
                pass
        return self._fallback.delete_pattern(full_pattern)

    # ========== 用途別キャッシュメソッド ==========

    def cache_user_profile(self, user_id: str, data: dict) -> bool:
        """ユーザープロフィールをキャッシュ"""
        return self.set(f"user:{user_id}:profile", data, self.TTL_LONG)

    def get_user_profile(self, user_id: str) -> Optional[dict]:
        """ユーザープロフィールキャッシュを取得"""
        return self.get(f"user:{user_id}:profile")

    def cache_trade_results(self, user_id: str, date_str: str, data: dict) -> bool:
        """取引結果をキャッシュ"""
        return self.set(f"trades:{user_id}:{date_str}", data, self.TTL_DAILY)

    def get_trade_results(self, user_id: str, date_str: str) -> Optional[dict]:
        """取引結果キャッシュを取得"""
        return self.get(f"trades:{user_id}:{date_str}")

    def cache_dashboard_stats(self, user_id: str, data: dict) -> bool:
        """ダッシュボード統計をキャッシュ"""
        return self.set(f"dashboard:{user_id}:stats", data, self.TTL_SHORT)

    def get_dashboard_stats(self, user_id: str) -> Optional[dict]:
        """ダッシュボード統計キャッシュを取得"""
        return self.get(f"dashboard:{user_id}:stats")

    def cache_sns_posts(self, user_id: str, page: int, data: dict) -> bool:
        """SNS投稿一覧をキャッシュ"""
        return self.set(f"posts:{user_id}:page:{page}", data, self.TTL_MEDIUM)

    def get_sns_posts(self, user_id: str, page: int) -> Optional[dict]:
        """SNS投稿一覧キャッシュを取得"""
        return self.get(f"posts:{user_id}:page:{page}")

    def cache_templates(self, data: list) -> bool:
        """テンプレート一覧をキャッシュ"""
        return self.set("templates:all", data, self.TTL_DAILY)

    def get_templates(self) -> Optional[list]:
        """テンプレート一覧キャッシュを取得"""
        return self.get("templates:all")

    def cache_ranking(self, period: str, data: list) -> bool:
        """ランキングをキャッシュ"""
        return self.set(f"ranking:{period}", data, self.TTL_LONG)

    def get_ranking(self, period: str) -> Optional[list]:
        """ランキングキャッシュを取得"""
        return self.get(f"ranking:{period}")

    def cache_api_response(self, endpoint: str, params_hash: str, data: Any) -> bool:
        """APIレスポンスをキャッシュ"""
        return self.set(f"api:{endpoint}:{params_hash}", data, self.TTL_MEDIUM)

    def get_api_response(self, endpoint: str, params_hash: str) -> Optional[Any]:
        """APIレスポンスキャッシュを取得"""
        return self.get(f"api:{endpoint}:{params_hash}")

    # ========== キャッシュ無効化 ==========

    def invalidate_user_cache(self, user_id: str) -> int:
        """ユーザー関連のキャッシュを全て無効化"""
        count = 0
        count += self.invalidate_pattern(f"user:{user_id}:*")
        count += self.invalidate_pattern(f"trades:{user_id}:*")
        count += self.invalidate_pattern(f"dashboard:{user_id}:*")
        count += self.invalidate_pattern(f"posts:{user_id}:*")
        return count

    def invalidate_all_rankings(self) -> int:
        """全ランキングキャッシュを無効化"""
        return self.invalidate_pattern("ranking:*")

    # ========== デコレータ ==========

    def cached(self, ttl: int = None, key_prefix: str = "func"):
        """関数の結果をキャッシュするデコレータ"""
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # キャッシュキー生成
                key_parts = [key_prefix, func.__name__]
                key_parts.extend(str(a) for a in args)
                key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = ":".join(key_parts)
                key_hash = hashlib.md5(cache_key.encode()).hexdigest()[:12]
                full_key = f"func:{func.__name__}:{key_hash}"

                # キャッシュチェック
                cached_value = self.get(full_key)
                if cached_value is not None:
                    return cached_value

                # 関数実行
                result = func(*args, **kwargs)

                # キャッシュ保存
                self.set(full_key, result, ttl or self.TTL_MEDIUM)
                return result
            return wrapper
        return decorator

    # ========== 統計 ==========

    def get_stats(self) -> dict:
        """キャッシュ統計を取得"""
        if self._use_redis:
            try:
                info = self._redis.info("stats")
                return {
                    "backend": "redis",
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                    "connected_clients": self._redis.info("clients").get("connected_clients", 0),
                    "used_memory": self._redis.info("memory").get("used_memory_human", "N/A"),
                }
            except Exception:
                pass
        return {
            "backend": "memory",
            **self._fallback.get_stats(),
        }


# テスト実行
if __name__ == "__main__":
    service = RedisCacheService()

    print(f"=== キャッシュバックエンド: {service.backend} ===")

    # 基本的なset/get
    print("\n=== 基本操作テスト ===")
    service.set("test:key1", {"name": "テスト", "value": 123}, ttl=60)
    result = service.get("test:key1")
    print(f"  set/get: {result}")

    # ユーザープロフィールキャッシュ
    print("\n=== ユーザープロフィールキャッシュ ===")
    service.cache_user_profile("user_001", {
        "id": "user_001",
        "email": "test@example.com",
        "plan": "premium",
    })
    profile = service.get_user_profile("user_001")
    print(f"  プロフィール: {profile}")

    # 取引結果キャッシュ
    print("\n=== 取引結果キャッシュ ===")
    service.cache_trade_results("user_001", "2026-03-11", {
        "daily_profit": 15000,
        "win_rate": 66.7,
        "total_trades": 12,
    })
    trades = service.get_trade_results("user_001", "2026-03-11")
    print(f"  取引結果: {trades}")

    # ダッシュボード統計キャッシュ
    print("\n=== ダッシュボード統計キャッシュ ===")
    service.cache_dashboard_stats("user_001", {
        "total_posts": 156,
        "total_profit": 285000,
    })
    stats = service.get_dashboard_stats("user_001")
    print(f"  統計: {stats}")

    # テンプレートキャッシュ
    print("\n=== テンプレートキャッシュ ===")
    service.cache_templates([
        {"id": "dark_classic", "name": "ダーククラシック"},
        {"id": "neon_glow", "name": "ネオングロー"},
    ])
    templates = service.get_templates()
    print(f"  テンプレート: {templates}")

    # デコレータテスト
    print("\n=== デコレータテスト ===")

    @service.cached(ttl=60, key_prefix="test")
    def expensive_calculation(x, y):
        print(f"    計算実行中... {x} + {y}")
        return x + y

    result1 = expensive_calculation(10, 20)
    print(f"  1回目: {result1}")
    result2 = expensive_calculation(10, 20)
    print(f"  2回目(キャッシュ): {result2}")

    # 統計
    print("\n=== キャッシュ統計 ===")
    cache_stats = service.get_stats()
    for key, value in cache_stats.items():
        print(f"  {key}: {value}")

    # キャッシュ無効化
    print("\n=== キャッシュ無効化テスト ===")
    count = service.invalidate_user_cache("user_001")
    print(f"  削除されたキー数: {count}")
    profile_after = service.get_user_profile("user_001")
    print(f"  無効化後のプロフィール: {profile_after}")

    print("\n✓ Redisキャッシュサービス テスト完了")
