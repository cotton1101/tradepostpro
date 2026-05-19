"""
TradePost Pro - 通知カスタマイズ
ユーザーが受け取る通知の種類を細かく設定
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class NotificationChannel(str, Enum):
    EMAIL = "email"
    LINE = "line"
    PUSH = "push"           # ブラウザプッシュ通知
    IN_APP = "in_app"       # アプリ内通知


class NotificationCategory(str, Enum):
    # 投稿関連
    POST_SUCCESS = "post_success"           # 投稿成功
    POST_FAILURE = "post_failure"           # 投稿失敗
    POST_SCHEDULED = "post_scheduled"       # 投稿スケジュール確認

    # 取引関連
    DAILY_SUMMARY = "daily_summary"         # 日次サマリー
    WEEKLY_REPORT = "weekly_report"         # 週次レポート
    MONTHLY_REPORT = "monthly_report"       # 月次レポート
    PROFIT_MILESTONE = "profit_milestone"   # 利益マイルストーン達成

    # アカウント関連
    PLAN_RENEWAL = "plan_renewal"           # プラン更新
    PLAN_EXPIRING = "plan_expiring"         # プラン期限切れ間近
    PAYMENT_SUCCESS = "payment_success"     # 決済成功
    PAYMENT_FAILED = "payment_failed"       # 決済失敗
    TRIAL_ENDING = "trial_ending"           # トライアル終了間近

    # システム関連
    SYSTEM_MAINTENANCE = "system_maintenance"   # メンテナンス通知
    NEW_FEATURE = "new_feature"                 # 新機能のお知らせ
    SECURITY_ALERT = "security_alert"           # セキュリティアラート

    # ソーシャル関連
    RANKING_UPDATE = "ranking_update"       # ランキング変動
    REFERRAL_SIGNUP = "referral_signup"     # 紹介者の登録
    REFERRAL_REWARD = "referral_reward"     # 紹介報酬


# デフォルト通知設定
DEFAULT_PREFERENCES = {
    # 投稿関連
    NotificationCategory.POST_SUCCESS.value: {
        "label_ja": "投稿成功通知",
        "label_en": "Post Success",
        "description_ja": "SNSへの投稿が成功した時に通知",
        "default_channels": [NotificationChannel.IN_APP.value],
        "importance": "low",
        "can_disable": True,
    },
    NotificationCategory.POST_FAILURE.value: {
        "label_ja": "投稿失敗通知",
        "label_en": "Post Failure",
        "description_ja": "SNSへの投稿が失敗した時に通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "high",
        "can_disable": False,
    },
    NotificationCategory.POST_SCHEDULED.value: {
        "label_ja": "投稿スケジュール確認",
        "label_en": "Post Scheduled",
        "description_ja": "翌日の投稿スケジュールを事前に通知",
        "default_channels": [NotificationChannel.IN_APP.value],
        "importance": "low",
        "can_disable": True,
    },
    # 取引関連
    NotificationCategory.DAILY_SUMMARY.value: {
        "label_ja": "日次サマリー",
        "label_en": "Daily Summary",
        "description_ja": "1日の取引結果サマリーを通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "medium",
        "can_disable": True,
    },
    NotificationCategory.WEEKLY_REPORT.value: {
        "label_ja": "週次レポート",
        "label_en": "Weekly Report",
        "description_ja": "週間の取引レポートを通知",
        "default_channels": [NotificationChannel.EMAIL.value],
        "importance": "medium",
        "can_disable": True,
    },
    NotificationCategory.MONTHLY_REPORT.value: {
        "label_ja": "月次レポート",
        "label_en": "Monthly Report",
        "description_ja": "月間の取引レポートを通知",
        "default_channels": [NotificationChannel.EMAIL.value],
        "importance": "medium",
        "can_disable": True,
    },
    NotificationCategory.PROFIT_MILESTONE.value: {
        "label_ja": "利益マイルストーン",
        "label_en": "Profit Milestone",
        "description_ja": "累計利益が節目に達した時に通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "medium",
        "can_disable": True,
    },
    # アカウント関連
    NotificationCategory.PLAN_RENEWAL.value: {
        "label_ja": "プラン更新通知",
        "label_en": "Plan Renewal",
        "description_ja": "プランの自動更新時に通知",
        "default_channels": [NotificationChannel.EMAIL.value],
        "importance": "high",
        "can_disable": False,
    },
    NotificationCategory.PLAN_EXPIRING.value: {
        "label_ja": "プラン期限切れ通知",
        "label_en": "Plan Expiring",
        "description_ja": "プランの期限が近づいた時に通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "high",
        "can_disable": False,
    },
    NotificationCategory.PAYMENT_SUCCESS.value: {
        "label_ja": "決済成功通知",
        "label_en": "Payment Success",
        "description_ja": "決済が正常に完了した時に通知",
        "default_channels": [NotificationChannel.EMAIL.value],
        "importance": "medium",
        "can_disable": True,
    },
    NotificationCategory.PAYMENT_FAILED.value: {
        "label_ja": "決済失敗通知",
        "label_en": "Payment Failed",
        "description_ja": "決済が失敗した時に通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "critical",
        "can_disable": False,
    },
    NotificationCategory.TRIAL_ENDING.value: {
        "label_ja": "トライアル終了通知",
        "label_en": "Trial Ending",
        "description_ja": "無料トライアルの終了が近づいた時に通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "high",
        "can_disable": False,
    },
    # システム関連
    NotificationCategory.SYSTEM_MAINTENANCE.value: {
        "label_ja": "メンテナンス通知",
        "label_en": "System Maintenance",
        "description_ja": "システムメンテナンスの予定を通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "high",
        "can_disable": False,
    },
    NotificationCategory.NEW_FEATURE.value: {
        "label_ja": "新機能のお知らせ",
        "label_en": "New Feature",
        "description_ja": "新機能やアップデートのお知らせ",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "low",
        "can_disable": True,
    },
    NotificationCategory.SECURITY_ALERT.value: {
        "label_ja": "セキュリティアラート",
        "label_en": "Security Alert",
        "description_ja": "不審なログインや重要なセキュリティ情報",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "critical",
        "can_disable": False,
    },
    # ソーシャル関連
    NotificationCategory.RANKING_UPDATE.value: {
        "label_ja": "ランキング変動",
        "label_en": "Ranking Update",
        "description_ja": "ランキング順位が変動した時に通知",
        "default_channels": [NotificationChannel.IN_APP.value],
        "importance": "low",
        "can_disable": True,
    },
    NotificationCategory.REFERRAL_SIGNUP.value: {
        "label_ja": "紹介者登録通知",
        "label_en": "Referral Signup",
        "description_ja": "紹介した人が登録した時に通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "medium",
        "can_disable": True,
    },
    NotificationCategory.REFERRAL_REWARD.value: {
        "label_ja": "紹介報酬通知",
        "label_en": "Referral Reward",
        "description_ja": "紹介報酬が発生した時に通知",
        "default_channels": [NotificationChannel.EMAIL.value, NotificationChannel.IN_APP.value],
        "importance": "medium",
        "can_disable": True,
    },
}


@dataclass
class UserNotificationPreference:
    """ユーザーの通知設定"""
    user_id: str = ""
    # カテゴリ → チャンネルリスト
    preferences: Dict[str, List[str]] = field(default_factory=dict)
    # 全体設定
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    email_digest: bool = False          # メールをまとめて送信
    digest_frequency: str = "daily"     # daily, weekly
    updated_at: str = ""


class NotificationPreferenceService:
    """通知カスタマイズサービス"""

    def __init__(self):
        self.user_prefs: Dict[str, UserNotificationPreference] = {}

    # ============================================================
    # 設定取得
    # ============================================================

    def get_notification_categories(self, lang: str = "ja") -> List[Dict]:
        """通知カテゴリ一覧を取得"""
        categories = []
        for cat_id, config in DEFAULT_PREFERENCES.items():
            categories.append({
                "id": cat_id,
                "label": config[f"label_{lang}"] if f"label_{lang}" in config else config["label_ja"],
                "description": config.get(f"description_{lang}", config.get("description_ja", "")),
                "importance": config["importance"],
                "can_disable": config["can_disable"],
                "default_channels": config["default_channels"],
            })
        return categories

    def get_user_preferences(self, user_id: str) -> Dict:
        """ユーザーの通知設定を取得"""
        pref = self.user_prefs.get(user_id)

        result = {}
        for cat_id, config in DEFAULT_PREFERENCES.items():
            if pref and cat_id in pref.preferences:
                channels = pref.preferences[cat_id]
            else:
                channels = config["default_channels"]

            result[cat_id] = {
                "label": config["label_ja"],
                "channels": channels,
                "importance": config["importance"],
                "can_disable": config["can_disable"],
                "enabled": len(channels) > 0,
            }

        quiet_hours = None
        if pref and pref.quiet_hours_enabled:
            quiet_hours = {
                "enabled": True,
                "start": pref.quiet_hours_start,
                "end": pref.quiet_hours_end,
            }

        return {
            "user_id": user_id,
            "categories": result,
            "quiet_hours": quiet_hours,
            "email_digest": pref.email_digest if pref else False,
            "digest_frequency": pref.digest_frequency if pref else "daily",
        }

    # ============================================================
    # 設定更新
    # ============================================================

    def update_category_channels(
        self,
        user_id: str,
        category: str,
        channels: List[str],
    ) -> Dict:
        """カテゴリの通知チャンネルを更新"""
        config = DEFAULT_PREFERENCES.get(category)
        if not config:
            return {"status": "error", "message": "無効な通知カテゴリです"}

        # 無効化不可のカテゴリチェック
        if not config["can_disable"] and len(channels) == 0:
            return {"status": "error", "message": f"「{config['label_ja']}」は無効にできません"}

        # 有効なチャンネルかチェック
        valid_channels = [c.value for c in NotificationChannel]
        for ch in channels:
            if ch not in valid_channels:
                return {"status": "error", "message": f"無効な通知チャンネル: {ch}"}

        pref = self._get_or_create_pref(user_id)
        pref.preferences[category] = channels
        pref.updated_at = datetime.now().isoformat()

        return {
            "status": "success",
            "category": category,
            "label": config["label_ja"],
            "channels": channels,
        }

    def set_quiet_hours(
        self,
        user_id: str,
        enabled: bool,
        start: str = "22:00",
        end: str = "07:00",
    ) -> Dict:
        """おやすみモード（通知停止時間帯）を設定"""
        pref = self._get_or_create_pref(user_id)
        pref.quiet_hours_enabled = enabled
        pref.quiet_hours_start = start
        pref.quiet_hours_end = end
        pref.updated_at = datetime.now().isoformat()

        return {
            "status": "success",
            "quiet_hours": {
                "enabled": enabled,
                "start": start,
                "end": end,
            },
        }

    def set_email_digest(
        self,
        user_id: str,
        enabled: bool,
        frequency: str = "daily",
    ) -> Dict:
        """メールダイジェスト設定"""
        pref = self._get_or_create_pref(user_id)
        pref.email_digest = enabled
        pref.digest_frequency = frequency
        pref.updated_at = datetime.now().isoformat()

        return {
            "status": "success",
            "email_digest": enabled,
            "frequency": frequency,
        }

    def bulk_update(
        self,
        user_id: str,
        updates: Dict[str, List[str]],
    ) -> Dict:
        """複数カテゴリの設定を一括更新"""
        results = []
        errors = []

        for category, channels in updates.items():
            result = self.update_category_channels(user_id, category, channels)
            if result["status"] == "success":
                results.append(result)
            else:
                errors.append({"category": category, "error": result["message"]})

        return {
            "status": "success" if not errors else "partial",
            "updated": len(results),
            "errors": errors,
        }

    # ============================================================
    # 通知判定
    # ============================================================

    def should_notify(
        self,
        user_id: str,
        category: str,
        channel: str,
        current_time: Optional[str] = None,
    ) -> bool:
        """指定のカテゴリ・チャンネルで通知すべきか判定"""
        pref = self.user_prefs.get(user_id)

        # 設定がない場合はデフォルト
        if not pref or category not in pref.preferences:
            config = DEFAULT_PREFERENCES.get(category, {})
            return channel in config.get("default_channels", [])

        # チャンネルチェック
        if channel not in pref.preferences.get(category, []):
            return False

        # おやすみモードチェック
        if pref.quiet_hours_enabled and channel != NotificationChannel.EMAIL.value:
            if current_time:
                if self._is_quiet_hours(current_time, pref.quiet_hours_start, pref.quiet_hours_end):
                    # critical通知はおやすみモードでも送信
                    config = DEFAULT_PREFERENCES.get(category, {})
                    if config.get("importance") != "critical":
                        return False

        return True

    def _is_quiet_hours(self, current: str, start: str, end: str) -> bool:
        """おやすみ時間帯かどうか判定"""
        current_minutes = self._time_to_minutes(current)
        start_minutes = self._time_to_minutes(start)
        end_minutes = self._time_to_minutes(end)

        if start_minutes <= end_minutes:
            return start_minutes <= current_minutes < end_minutes
        else:  # 日をまたぐ場合
            return current_minutes >= start_minutes or current_minutes < end_minutes

    def _time_to_minutes(self, time_str: str) -> int:
        """HH:MM を分に変換"""
        parts = time_str.split(":")
        return int(parts[0]) * 60 + int(parts[1])

    def _get_or_create_pref(self, user_id: str) -> UserNotificationPreference:
        """ユーザー設定を取得または作成"""
        if user_id not in self.user_prefs:
            self.user_prefs[user_id] = UserNotificationPreference(
                user_id=user_id,
                updated_at=datetime.now().isoformat(),
            )
        return self.user_prefs[user_id]

    # ============================================================
    # プリセット
    # ============================================================

    def apply_preset(self, user_id: str, preset: str) -> Dict:
        """プリセット設定を適用"""
        presets = {
            "all_on": {cat: config["default_channels"] for cat, config in DEFAULT_PREFERENCES.items()},
            "essential_only": {
                cat: config["default_channels"]
                for cat, config in DEFAULT_PREFERENCES.items()
                if config["importance"] in ("critical", "high")
            },
            "minimal": {
                cat: [NotificationChannel.IN_APP.value]
                for cat, config in DEFAULT_PREFERENCES.items()
                if not config["can_disable"]
            },
        }

        if preset not in presets:
            return {"status": "error", "message": f"無効なプリセット: {preset}"}

        pref = self._get_or_create_pref(user_id)
        pref.preferences = presets[preset]
        pref.updated_at = datetime.now().isoformat()

        return {
            "status": "success",
            "preset": preset,
            "categories_updated": len(presets[preset]),
        }


# テスト用
if __name__ == "__main__":
    service = NotificationPreferenceService()

    print("=== 通知カテゴリ一覧 ===")
    categories = service.get_notification_categories()
    for cat in categories:
        disable_str = "変更可" if cat["can_disable"] else "必須"
        print(f"  [{cat['importance']:8s}] {cat['label']} ({disable_str})")

    print(f"\n=== ユーザー設定テスト ===")
    # チャンネル更新
    result = service.update_category_channels("user1", "post_success", ["email", "in_app", "line"])
    print(f"  投稿成功通知を更新: {result['channels']}")

    # 必須通知の無効化（エラー）
    result = service.update_category_channels("user1", "payment_failed", [])
    print(f"  決済失敗を無効化: {result['message']}")

    # おやすみモード
    result = service.set_quiet_hours("user1", True, "23:00", "06:00")
    print(f"  おやすみモード: {result['quiet_hours']}")

    # メールダイジェスト
    result = service.set_email_digest("user1", True, "weekly")
    print(f"  メールダイジェスト: {result}")

    print(f"\n=== 通知判定テスト ===")
    # 通常時間
    print(f"  投稿成功(email, 10:00): {service.should_notify('user1', 'post_success', 'email', '10:00')}")
    # おやすみ時間
    print(f"  投稿成功(line, 23:30): {service.should_notify('user1', 'post_success', 'line', '23:30')}")
    # critical通知はおやすみでも送信
    print(f"  セキュリティ(in_app, 23:30): {service.should_notify('user1', 'security_alert', 'in_app', '23:30')}")

    print(f"\n=== プリセット適用 ===")
    result = service.apply_preset("user2", "essential_only")
    print(f"  essential_only: {result['categories_updated']}カテゴリ更新")

    result = service.apply_preset("user3", "minimal")
    print(f"  minimal: {result['categories_updated']}カテゴリ更新")

    print("\n✓ 通知カスタマイズサービス テスト完了")
