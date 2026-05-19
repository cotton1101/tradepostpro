"""
TradePost Pro - 無料トライアルサービス
7日間の無料お試し期間の管理
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TrialStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CONVERTED = "converted"  # 有料プランに移行済み
    CANCELLED = "cancelled"


# トライアル設定
TRIAL_CONFIG = {
    "duration_days": 7,
    "plan_level": "standard",  # トライアル中はスタンダードプラン相当
    "max_sns_accounts": 4,
    "max_daily_posts": 3,
    "templates_available": ["dark_classic", "neon_glow", "minimal_white"],
    "video_generation": False,
    "require_email_verification": True,
    "require_payment_method": False,  # クレカ不要
    "reminder_days": [1, 3, 5, 7],  # リマインダー送信日
    "grace_period_hours": 24,  # 猶予期間
}


class TrialService:
    """無料トライアルサービス"""

    def __init__(self, db_session=None):
        self.db = db_session
        self.config = TRIAL_CONFIG

    def start_trial(self, user_id: str, email: str) -> Dict:
        """トライアルを開始"""
        now = datetime.now()
        end_date = now + timedelta(days=self.config["duration_days"])

        trial_data = {
            "user_id": user_id,
            "email": email,
            "status": TrialStatus.ACTIVE,
            "start_date": now.isoformat(),
            "end_date": end_date.isoformat(),
            "days_remaining": self.config["duration_days"],
            "plan_level": self.config["plan_level"],
            "features": {
                "max_sns_accounts": self.config["max_sns_accounts"],
                "max_daily_posts": self.config["max_daily_posts"],
                "templates": self.config["templates_available"],
                "video_generation": self.config["video_generation"],
            },
        }

        logger.info(f"トライアル開始: user={user_id}, end={end_date.strftime('%Y-%m-%d')}")
        return trial_data

    def check_trial_status(
        self,
        start_date: str,
        is_paid: bool = False,
    ) -> Dict:
        """トライアルのステータスを確認"""
        if is_paid:
            return {
                "status": TrialStatus.CONVERTED,
                "message": "有料プランに移行済みです",
                "is_active": False,
            }

        start = datetime.fromisoformat(start_date)
        end = start + timedelta(days=self.config["duration_days"])
        now = datetime.now()

        grace_end = end + timedelta(hours=self.config["grace_period_hours"])

        if now < end:
            days_remaining = (end - now).days + 1
            return {
                "status": TrialStatus.ACTIVE,
                "days_remaining": days_remaining,
                "end_date": end.isoformat(),
                "is_active": True,
                "message": f"トライアル残り{days_remaining}日",
            }
        elif now < grace_end:
            return {
                "status": TrialStatus.ACTIVE,
                "days_remaining": 0,
                "end_date": end.isoformat(),
                "is_active": True,
                "message": "トライアル最終日（猶予期間中）",
                "is_grace_period": True,
            }
        else:
            return {
                "status": TrialStatus.EXPIRED,
                "days_remaining": 0,
                "end_date": end.isoformat(),
                "is_active": False,
                "message": "トライアル期間が終了しました。有料プランにアップグレードしてください。",
            }

    def get_trial_features(self) -> Dict:
        """トライアルで利用可能な機能一覧"""
        return {
            "duration": f"{self.config['duration_days']}日間",
            "plan_equivalent": "スタンダードプラン相当",
            "features": [
                f"SNSアカウント最大{self.config['max_sns_accounts']}つ",
                f"1日最大{self.config['max_daily_posts']}回投稿",
                f"画像テンプレート{len(self.config['templates_available'])}種類",
                "MT4/MT5データ連携",
                "自動投稿スケジュール",
                "投稿履歴閲覧",
            ],
            "limitations": [
                "動画生成は利用不可",
                "カスタムテンプレートは利用不可",
                "プレミアムテンプレートは利用不可",
            ],
            "no_credit_card": not self.config["require_payment_method"],
        }

    def should_send_reminder(
        self,
        start_date: str,
        reminders_sent: list,
    ) -> Optional[Dict]:
        """リマインダーを送信すべきか判定"""
        start = datetime.fromisoformat(start_date)
        now = datetime.now()
        elapsed_days = (now - start).days

        for reminder_day in self.config["reminder_days"]:
            if reminder_day == elapsed_days and reminder_day not in reminders_sent:
                remaining = self.config["duration_days"] - elapsed_days
                return {
                    "should_send": True,
                    "day": reminder_day,
                    "remaining_days": remaining,
                    "template": self._get_reminder_template(remaining),
                }

        return {"should_send": False}

    def _get_reminder_template(self, remaining_days: int) -> Dict:
        """リマインダーテンプレートを取得"""
        if remaining_days >= 5:
            return {
                "subject": "TradePost Pro トライアルをお楽しみいただけていますか？",
                "tone": "friendly",
                "cta": "機能を試してみる",
            }
        elif remaining_days >= 2:
            return {
                "subject": f"トライアル残り{remaining_days}日！お見逃しなく",
                "tone": "urgent",
                "cta": "今すぐアップグレード",
            }
        else:
            return {
                "subject": "トライアル最終日！特別割引のご案内",
                "tone": "final",
                "cta": "20%オフでアップグレード",
                "discount_code": "TRIAL20",
                "discount_rate": 0.20,
            }

    def convert_to_paid(
        self,
        user_id: str,
        plan: str,
        discount_code: Optional[str] = None,
    ) -> Dict:
        """トライアルから有料プランに移行"""
        plans = {
            "light": {"name": "ライト", "price": 1980},
            "standard": {"name": "スタンダード", "price": 2980},
            "premium": {"name": "プレミアム", "price": 4980},
        }

        plan_info = plans.get(plan)
        if not plan_info:
            return {"success": False, "message": "無効なプランです"}

        price = plan_info["price"]
        discount = 0

        if discount_code == "TRIAL20":
            discount = price * 0.20
            price -= discount

        return {
            "success": True,
            "user_id": user_id,
            "plan": plan_info["name"],
            "original_price": plan_info["price"],
            "discount": discount,
            "final_price": price,
            "message": f"{plan_info['name']}プランへの移行が完了しました",
        }


if __name__ == "__main__":
    service = TrialService()

    # トライアル開始
    trial = service.start_trial("user_001", "test@example.com")
    print(f"=== トライアル開始 ===")
    print(f"期間: {trial['start_date'][:10]} 〜 {trial['end_date'][:10]}")
    print(f"残り: {trial['days_remaining']}日")
    print(f"プラン: {trial['plan_level']}")

    # 機能一覧
    features = service.get_trial_features()
    print(f"\n=== トライアル機能 ===")
    print(f"期間: {features['duration']}")
    print(f"クレカ不要: {features['no_credit_card']}")
    for f in features['features']:
        print(f"  ✓ {f}")
    for l in features['limitations']:
        print(f"  ✗ {l}")

    # ステータス確認
    status = service.check_trial_status(trial['start_date'])
    print(f"\n=== ステータス ===")
    print(f"状態: {status['status']}")
    print(f"残り: {status['days_remaining']}日")

    # 有料プラン移行
    result = service.convert_to_paid("user_001", "standard", "TRIAL20")
    print(f"\n=== プラン移行 ===")
    print(f"プラン: {result['plan']}")
    print(f"通常価格: {result['original_price']:,}円")
    print(f"割引: {result['discount']:,.0f}円")
    print(f"支払額: {result['final_price']:,.0f}円")
