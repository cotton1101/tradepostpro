"""
TradePost Pro - 監査ログサービス
全操作の記録と追跡
"""

import json
import hashlib
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


class AuditAction(str, Enum):
    """監査アクション種別"""
    # 認証
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    LOGIN_FAILED = "auth.login_failed"
    PASSWORD_CHANGE = "auth.password_change"
    TWO_FA_ENABLE = "auth.2fa_enable"
    TWO_FA_DISABLE = "auth.2fa_disable"

    # ユーザー
    USER_REGISTER = "user.register"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"

    # SNS設定
    SNS_CONNECT = "sns.connect"
    SNS_DISCONNECT = "sns.disconnect"
    SNS_UPDATE = "sns.update"

    # 投稿
    POST_CREATE = "post.create"
    POST_SUCCESS = "post.success"
    POST_FAILED = "post.failed"
    POST_DELETE = "post.delete"

    # プラン
    PLAN_SUBSCRIBE = "plan.subscribe"
    PLAN_UPGRADE = "plan.upgrade"
    PLAN_DOWNGRADE = "plan.downgrade"
    PLAN_CANCEL = "plan.cancel"
    PAYMENT_SUCCESS = "plan.payment_success"
    PAYMENT_FAILED = "plan.payment_failed"

    # API
    API_KEY_CREATE = "api.key_create"
    API_KEY_REVOKE = "api.key_revoke"
    API_ACCESS = "api.access"

    # 管理者
    ADMIN_USER_EDIT = "admin.user_edit"
    ADMIN_USER_SUSPEND = "admin.user_suspend"
    ADMIN_SETTINGS_CHANGE = "admin.settings_change"

    # データ
    DATA_EXPORT = "data.export"
    DATA_IMPORT = "data.import"


class AuditSeverity(str, Enum):
    """重要度"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# アクション別のデフォルト重要度
ACTION_SEVERITY = {
    AuditAction.LOGIN: AuditSeverity.LOW,
    AuditAction.LOGOUT: AuditSeverity.LOW,
    AuditAction.LOGIN_FAILED: AuditSeverity.HIGH,
    AuditAction.PASSWORD_CHANGE: AuditSeverity.HIGH,
    AuditAction.TWO_FA_ENABLE: AuditSeverity.MEDIUM,
    AuditAction.TWO_FA_DISABLE: AuditSeverity.HIGH,
    AuditAction.USER_REGISTER: AuditSeverity.MEDIUM,
    AuditAction.USER_DELETE: AuditSeverity.CRITICAL,
    AuditAction.SNS_CONNECT: AuditSeverity.MEDIUM,
    AuditAction.POST_CREATE: AuditSeverity.LOW,
    AuditAction.POST_FAILED: AuditSeverity.MEDIUM,
    AuditAction.PLAN_SUBSCRIBE: AuditSeverity.MEDIUM,
    AuditAction.PLAN_CANCEL: AuditSeverity.HIGH,
    AuditAction.PAYMENT_FAILED: AuditSeverity.HIGH,
    AuditAction.API_KEY_CREATE: AuditSeverity.HIGH,
    AuditAction.API_KEY_REVOKE: AuditSeverity.HIGH,
    AuditAction.ADMIN_USER_SUSPEND: AuditSeverity.CRITICAL,
    AuditAction.ADMIN_SETTINGS_CHANGE: AuditSeverity.CRITICAL,
    AuditAction.DATA_EXPORT: AuditSeverity.MEDIUM,
}


@dataclass
class AuditLogEntry:
    """監査ログエントリ"""
    log_id: str = ""
    timestamp: str = ""
    user_id: str = ""
    action: str = ""
    severity: str = AuditSeverity.LOW
    resource_type: str = ""
    resource_id: str = ""
    ip_address: str = ""
    user_agent: str = ""
    details: Dict = field(default_factory=dict)
    success: bool = True
    error_message: str = ""
    # 改ざん検知用
    checksum: str = ""


class AuditLogService:
    """監査ログサービス"""

    def __init__(self):
        self.logs: List[AuditLogEntry] = []
        self._log_counter = 0

    # ============================================================
    # ログ記録
    # ============================================================

    def log(
        self,
        user_id: str,
        action: AuditAction,
        resource_type: str = "",
        resource_id: str = "",
        ip_address: str = "",
        user_agent: str = "",
        details: Optional[Dict] = None,
        success: bool = True,
        error_message: str = "",
    ) -> AuditLogEntry:
        """監査ログを記録"""
        self._log_counter += 1
        timestamp = datetime.now().isoformat()

        # ログID生成
        log_id = hashlib.md5(
            f"{self._log_counter}:{timestamp}:{user_id}:{action}".encode()
        ).hexdigest()[:16]

        # 重要度
        severity = ACTION_SEVERITY.get(action, AuditSeverity.LOW)

        # 機密情報のマスキング
        masked_details = self._mask_sensitive(details or {})

        entry = AuditLogEntry(
            log_id=log_id,
            timestamp=timestamp,
            user_id=user_id,
            action=action.value if isinstance(action, AuditAction) else action,
            severity=severity.value if isinstance(severity, AuditSeverity) else severity,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            details=masked_details,
            success=success,
            error_message=error_message,
        )

        # チェックサム生成（改ざん検知）
        entry.checksum = self._generate_checksum(entry)

        self.logs.append(entry)
        return entry

    def _mask_sensitive(self, details: Dict) -> Dict:
        """機密情報をマスキング"""
        sensitive_keys = {"password", "secret", "token", "api_key", "credit_card"}
        masked = {}
        for key, value in details.items():
            if any(s in key.lower() for s in sensitive_keys):
                if isinstance(value, str) and len(value) > 4:
                    masked[key] = value[:2] + "*" * (len(value) - 4) + value[-2:]
                else:
                    masked[key] = "***"
            else:
                masked[key] = value
        return masked

    def _generate_checksum(self, entry: AuditLogEntry) -> str:
        """改ざん検知用チェックサムを生成"""
        data = f"{entry.log_id}:{entry.timestamp}:{entry.user_id}:{entry.action}:{entry.success}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def verify_integrity(self, entry: AuditLogEntry) -> bool:
        """ログの整合性を検証"""
        expected = self._generate_checksum(entry)
        return entry.checksum == expected

    # ============================================================
    # 検索・フィルタリング
    # ============================================================

    def search(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        severity: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        success: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict:
        """監査ログを検索"""
        results = self.logs.copy()

        if user_id:
            results = [l for l in results if l.user_id == user_id]
        if action:
            results = [l for l in results if l.action == action]
        if severity:
            results = [l for l in results if l.severity == severity]
        if start_date:
            results = [l for l in results if l.timestamp >= start_date]
        if end_date:
            results = [l for l in results if l.timestamp <= end_date]
        if success is not None:
            results = [l for l in results if l.success == success]

        total = len(results)
        results = sorted(results, key=lambda l: l.timestamp, reverse=True)
        paginated = results[offset:offset + limit]

        return {
            "total": total,
            "offset": offset,
            "limit": limit,
            "entries": paginated,
        }

    def get_user_activity(self, user_id: str, days: int = 30) -> Dict:
        """ユーザーアクティビティサマリー"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        user_logs = [l for l in self.logs if l.user_id == user_id and l.timestamp >= cutoff]

        action_counts: Dict[str, int] = {}
        for log in user_logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        failed_count = sum(1 for l in user_logs if not l.success)

        return {
            "user_id": user_id,
            "period_days": days,
            "total_actions": len(user_logs),
            "failed_actions": failed_count,
            "action_breakdown": action_counts,
            "last_login": next(
                (l.timestamp for l in reversed(user_logs) if l.action == AuditAction.LOGIN.value),
                None
            ),
        }

    def get_security_alerts(self, hours: int = 24) -> List[Dict]:
        """セキュリティアラートを取得"""
        cutoff = (datetime.now() - timedelta(hours=hours)).isoformat()
        alerts = []

        # 直近のログをフィルタ
        recent = [l for l in self.logs if l.timestamp >= cutoff]

        # ログイン失敗の集計
        failed_logins: Dict[str, int] = {}
        for log in recent:
            if log.action == AuditAction.LOGIN_FAILED.value:
                failed_logins[log.user_id] = failed_logins.get(log.user_id, 0) + 1

        for user_id, count in failed_logins.items():
            if count >= 3:
                alerts.append({
                    "type": "brute_force_attempt",
                    "severity": "critical",
                    "user_id": user_id,
                    "message": f"ユーザー {user_id} で{count}回のログイン失敗を検出",
                    "count": count,
                })

        # 重要度の高いアクション
        critical_logs = [l for l in recent if l.severity in ("high", "critical")]
        for log in critical_logs:
            if not log.success:
                alerts.append({
                    "type": "high_severity_failure",
                    "severity": log.severity,
                    "user_id": log.user_id,
                    "message": f"重要操作の失敗: {log.action}",
                    "log_id": log.log_id,
                })

        return alerts


# テスト用
if __name__ == "__main__":
    service = AuditLogService()

    # ログ記録テスト
    entry1 = service.log(
        user_id="user_001",
        action=AuditAction.LOGIN,
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0",
        details={"method": "email_password"},
    )
    print(f"ログ記録: {entry1.log_id} ({entry1.action})")

    # ログイン失敗
    for i in range(5):
        service.log(
            user_id="user_002",
            action=AuditAction.LOGIN_FAILED,
            ip_address="10.0.0.50",
            success=False,
            error_message="パスワードが正しくありません",
        )

    # SNS接続
    service.log(
        user_id="user_001",
        action=AuditAction.SNS_CONNECT,
        resource_type="sns_account",
        resource_id="x_account_001",
        details={"platform": "x", "api_key": "sk-1234567890abcdef"},
    )

    # プラン変更
    service.log(
        user_id="user_001",
        action=AuditAction.PLAN_UPGRADE,
        details={"from": "lite", "to": "standard", "amount": 2980},
    )

    # 整合性検証
    is_valid = service.verify_integrity(entry1)
    print(f"整合性検証: {'OK' if is_valid else 'NG'}")

    # 検索テスト
    results = service.search(user_id="user_001")
    print(f"\nuser_001のログ: {results['total']}件")

    # アクティビティサマリー
    activity = service.get_user_activity("user_001")
    print(f"アクティビティ: {json.dumps(activity, indent=2, ensure_ascii=False)}")

    # セキュリティアラート
    alerts = service.get_security_alerts()
    print(f"\nセキュリティアラート: {len(alerts)}件")
    for alert in alerts:
        print(f"  [{alert['severity']}] {alert['message']}")

    print("\n✓ 監査ログサービス テスト完了")
