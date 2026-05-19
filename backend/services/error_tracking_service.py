"""
エラートラッキングサービス（Sentry連携）
アプリケーションエラーの収集、分類、通知
"""

import traceback
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ErrorSeverity(Enum):
    """エラー重要度"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """エラーカテゴリ"""
    API = "api"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    SNS_POSTING = "sns_posting"
    IMAGE_GENERATION = "image_generation"
    PAYMENT = "payment"
    RATE_LIMIT = "rate_limit"
    EXTERNAL_SERVICE = "external_service"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


@dataclass
class ErrorEvent:
    """エラーイベント"""
    id: str
    fingerprint: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    exception_type: str = ""
    stacktrace: str = ""
    user_id: Optional[str] = None
    request_url: str = ""
    request_method: str = ""
    request_body: str = ""
    tags: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)
    environment: str = "production"
    release: str = ""
    timestamp: str = ""
    resolved: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if not self.fingerprint:
            self.fingerprint = hashlib.md5(
                f"{self.exception_type}:{self.message}:{self.category.value}".encode()
            ).hexdigest()[:12]


@dataclass
class ErrorGroup:
    """エラーグループ（同一エラーの集約）"""
    fingerprint: str
    first_seen: str
    last_seen: str
    count: int
    severity: ErrorSeverity
    category: ErrorCategory
    message: str
    exception_type: str
    affected_users: set = field(default_factory=set)
    is_resolved: bool = False
    assigned_to: Optional[str] = None


class ErrorTrackingService:
    """エラートラッキング管理サービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.dsn = self.config.get("sentry_dsn", "")
        self.environment = self.config.get("environment", "production")
        self.release = self.config.get("release", "1.0.0")

        self.events: List[ErrorEvent] = []
        self.groups: Dict[str, ErrorGroup] = {}
        self.alert_rules: List[dict] = self._default_alert_rules()
        self.alert_history: List[dict] = []

    def _default_alert_rules(self) -> List[dict]:
        """デフォルトのアラートルール"""
        return [
            {
                "id": "high_error_rate",
                "name": "高エラーレート",
                "condition": {"type": "error_count", "threshold": 10, "window_minutes": 5},
                "severity": ErrorSeverity.ERROR,
                "notify": ["email", "slack"],
            },
            {
                "id": "fatal_error",
                "name": "致命的エラー",
                "condition": {"type": "severity", "value": "fatal"},
                "severity": ErrorSeverity.FATAL,
                "notify": ["email", "slack", "pagerduty"],
            },
            {
                "id": "payment_error",
                "name": "決済エラー",
                "condition": {"type": "category", "value": "payment"},
                "severity": ErrorSeverity.ERROR,
                "notify": ["email", "slack"],
            },
            {
                "id": "sns_posting_failure",
                "name": "SNS投稿エラー多発",
                "condition": {"type": "category_count", "category": "sns_posting", "threshold": 5, "window_minutes": 10},
                "severity": ErrorSeverity.WARNING,
                "notify": ["slack"],
            },
        ]

    def capture_exception(
        self,
        exception: Exception,
        user_id: str = None,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        tags: dict = None,
        extra: dict = None,
        request_info: dict = None,
    ) -> dict:
        """例外をキャプチャ"""
        event = ErrorEvent(
            id=hashlib.md5(f"{datetime.now().isoformat()}:{str(exception)}".encode()).hexdigest()[:16],
            fingerprint="",
            message=str(exception),
            severity=ErrorSeverity.ERROR,
            category=category,
            exception_type=type(exception).__name__,
            stacktrace=traceback.format_exc(),
            user_id=user_id,
            request_url=(request_info or {}).get("url", ""),
            request_method=(request_info or {}).get("method", ""),
            tags=tags or {},
            extra=extra or {},
            environment=self.environment,
            release=self.release,
        )

        return self._process_event(event)

    def capture_message(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.INFO,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        user_id: str = None,
        tags: dict = None,
        extra: dict = None,
    ) -> dict:
        """メッセージをキャプチャ"""
        event = ErrorEvent(
            id=hashlib.md5(f"{datetime.now().isoformat()}:{message}".encode()).hexdigest()[:16],
            fingerprint="",
            message=message,
            severity=severity,
            category=category,
            user_id=user_id,
            tags=tags or {},
            extra=extra or {},
            environment=self.environment,
            release=self.release,
        )

        return self._process_event(event)

    def _process_event(self, event: ErrorEvent) -> dict:
        """イベントを処理"""
        self.events.append(event)

        # グループ化
        if event.fingerprint in self.groups:
            group = self.groups[event.fingerprint]
            group.count += 1
            group.last_seen = event.timestamp
            if event.user_id:
                group.affected_users.add(event.user_id)
        else:
            self.groups[event.fingerprint] = ErrorGroup(
                fingerprint=event.fingerprint,
                first_seen=event.timestamp,
                last_seen=event.timestamp,
                count=1,
                severity=event.severity,
                category=event.category,
                message=event.message,
                exception_type=event.exception_type,
                affected_users={event.user_id} if event.user_id else set(),
            )

        # アラートチェック
        triggered_alerts = self._check_alerts(event)

        return {
            "event_id": event.id,
            "fingerprint": event.fingerprint,
            "severity": event.severity.value,
            "category": event.category.value,
            "group_count": self.groups[event.fingerprint].count,
            "alerts_triggered": len(triggered_alerts),
        }

    def _check_alerts(self, event: ErrorEvent) -> List[dict]:
        """アラートルールをチェック"""
        triggered = []
        now = datetime.now()

        for rule in self.alert_rules:
            cond = rule["condition"]

            if cond["type"] == "severity" and event.severity.value == cond["value"]:
                triggered.append(self._trigger_alert(rule, event))

            elif cond["type"] == "category" and event.category.value == cond["value"]:
                triggered.append(self._trigger_alert(rule, event))

            elif cond["type"] == "error_count":
                window = timedelta(minutes=cond["window_minutes"])
                recent = [e for e in self.events if datetime.fromisoformat(e.timestamp) > now - window]
                if len(recent) >= cond["threshold"]:
                    triggered.append(self._trigger_alert(rule, event))

            elif cond["type"] == "category_count":
                window = timedelta(minutes=cond["window_minutes"])
                recent = [
                    e for e in self.events
                    if datetime.fromisoformat(e.timestamp) > now - window
                    and e.category.value == cond["category"]
                ]
                if len(recent) >= cond["threshold"]:
                    triggered.append(self._trigger_alert(rule, event))

        return triggered

    def _trigger_alert(self, rule: dict, event: ErrorEvent) -> dict:
        """アラートをトリガー"""
        alert = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "event_id": event.id,
            "message": event.message,
            "severity": event.severity.value,
            "notify_channels": rule["notify"],
            "triggered_at": datetime.now().isoformat(),
        }
        self.alert_history.append(alert)
        return alert

    def resolve_group(self, fingerprint: str) -> bool:
        """エラーグループを解決済みにする"""
        if fingerprint in self.groups:
            self.groups[fingerprint].is_resolved = True
            return True
        return False

    def get_error_stats(self, hours: int = 24) -> dict:
        """エラー統計を取得"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [e for e in self.events if datetime.fromisoformat(e.timestamp) > cutoff]

        by_severity = defaultdict(int)
        by_category = defaultdict(int)
        by_hour = defaultdict(int)
        affected_users = set()

        for e in recent:
            by_severity[e.severity.value] += 1
            by_category[e.category.value] += 1
            hour = datetime.fromisoformat(e.timestamp).strftime("%H:00")
            by_hour[hour] += 1
            if e.user_id:
                affected_users.add(e.user_id)

        return {
            "period_hours": hours,
            "total_events": len(recent),
            "unique_groups": len(set(e.fingerprint for e in recent)),
            "affected_users": len(affected_users),
            "by_severity": dict(by_severity),
            "by_category": dict(by_category),
            "by_hour": dict(sorted(by_hour.items())),
            "unresolved_groups": sum(1 for g in self.groups.values() if not g.is_resolved),
            "alerts_triggered": len([a for a in self.alert_history if datetime.fromisoformat(a["triggered_at"]) > cutoff]),
        }

    def get_top_errors(self, limit: int = 10) -> List[dict]:
        """頻出エラーTop Nを取得"""
        sorted_groups = sorted(
            self.groups.values(),
            key=lambda g: g.count,
            reverse=True,
        )
        return [
            {
                "fingerprint": g.fingerprint,
                "message": g.message[:100],
                "exception_type": g.exception_type,
                "category": g.category.value,
                "severity": g.severity.value,
                "count": g.count,
                "affected_users": len(g.affected_users),
                "first_seen": g.first_seen,
                "last_seen": g.last_seen,
                "is_resolved": g.is_resolved,
            }
            for g in sorted_groups[:limit]
        ]

    def generate_sentry_config(self) -> str:
        """Sentry設定ファイルを生成"""
        return f"""# sentry.py - Sentry Configuration
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

def init_sentry():
    sentry_sdk.init(
        dsn="{self.dsn or 'YOUR_SENTRY_DSN'}",
        environment="{self.environment}",
        release="{self.release}",
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
        ],
        before_send=before_send,
        before_breadcrumb=before_breadcrumb,
    )

def before_send(event, hint):
    # 機密情報をフィルタリング
    if 'request' in event:
        headers = event['request'].get('headers', {{}})
        if 'Authorization' in headers:
            headers['Authorization'] = '[FILTERED]'
        if 'Cookie' in headers:
            headers['Cookie'] = '[FILTERED]'
    return event

def before_breadcrumb(crumb, hint):
    if crumb.get('category') == 'http' and 'password' in str(crumb.get('data', {{}})):
        return None
    return crumb
"""


# テスト実行
if __name__ == "__main__":
    service = ErrorTrackingService({
        "sentry_dsn": "https://examplePublicKey@o0.ingest.sentry.io/0",
        "environment": "production",
        "release": "tradepost-pro@1.0.0",
    })

    print("=== エラートラッキングサービス テスト ===")

    # 例外キャプチャ
    print("\n--- 例外キャプチャ ---")
    try:
        raise ValueError("Invalid trade data: lot_size must be positive")
    except Exception as e:
        result = service.capture_exception(
            e,
            user_id="user_001",
            category=ErrorCategory.VALIDATION,
            tags={"endpoint": "/api/v1/trades"},
            extra={"lot_size": -0.1},
        )
        print(f"  イベントID: {result['event_id']}")
        print(f"  重要度: {result['severity']}")
        print(f"  カテゴリ: {result['category']}")

    # SNS投稿エラー
    print("\n--- SNS投稿エラー ---")
    for i in range(6):
        try:
            raise ConnectionError(f"Twitter API rate limit exceeded (attempt {i+1})")
        except Exception as e:
            result = service.capture_exception(
                e,
                user_id=f"user_{i:03d}",
                category=ErrorCategory.SNS_POSTING,
                tags={"platform": "twitter"},
            )
    print(f"  6件のSNS投稿エラーをキャプチャ")
    print(f"  アラート発火: {result['alerts_triggered']}")

    # 致命的エラー
    print("\n--- 致命的エラー ---")
    result = service.capture_message(
        "Database connection pool exhausted",
        severity=ErrorSeverity.FATAL,
        category=ErrorCategory.DATABASE,
        tags={"db": "primary"},
    )
    print(f"  イベントID: {result['event_id']}")
    print(f"  アラート発火: {result['alerts_triggered']}")

    # 決済エラー
    print("\n--- 決済エラー ---")
    try:
        raise RuntimeError("Stripe payment failed: card_declined")
    except Exception as e:
        result = service.capture_exception(
            e,
            user_id="user_005",
            category=ErrorCategory.PAYMENT,
        )
    print(f"  アラート発火: {result['alerts_triggered']}")

    # 統計
    print("\n--- エラー統計 (24h) ---")
    stats = service.get_error_stats(24)
    print(f"  総イベント: {stats['total_events']}")
    print(f"  ユニークグループ: {stats['unique_groups']}")
    print(f"  影響ユーザー: {stats['affected_users']}")
    print(f"  重要度別: {stats['by_severity']}")
    print(f"  カテゴリ別: {stats['by_category']}")
    print(f"  未解決グループ: {stats['unresolved_groups']}")
    print(f"  発火アラート: {stats['alerts_triggered']}")

    # Top エラー
    print("\n--- 頻出エラー Top 5 ---")
    top_errors = service.get_top_errors(5)
    for err in top_errors:
        print(f"  [{err['count']}回] {err['exception_type']}: {err['message'][:60]} ({err['category']})")

    # エラーグループ解決
    print("\n--- エラーグループ解決 ---")
    if top_errors:
        fp = top_errors[0]["fingerprint"]
        service.resolve_group(fp)
        print(f"  解決: {fp}")

    # Sentry設定
    print("\n--- Sentry設定ファイル ---")
    config = service.generate_sentry_config()
    print(f"  設定ファイル長: {len(config)}文字")

    print("\n✓ エラートラッキングサービス テスト完了")
