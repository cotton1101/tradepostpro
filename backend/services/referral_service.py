"""
TradePost Pro - アフィリエイトプログラム（紹介報酬）サービス
ユーザーが他のユーザーを紹介すると報酬が入る仕組み
"""

import hashlib
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# 報酬設定
REFERRAL_CONFIG = {
    "commission_rate": 0.20,       # 紹介報酬率 20%
    "commission_months": 12,       # 報酬が発生する月数
    "min_payout": 3000,            # 最低出金額（円）
    "cookie_days": 30,             # クッキー有効期間（日）
    "max_referrals": 1000,         # 最大紹介数
    "bonus_first_referral": 500,   # 初回紹介ボーナス（円）
    "tiers": {
        "bronze": {"min_referrals": 0, "rate": 0.20},
        "silver": {"min_referrals": 10, "rate": 0.25},
        "gold": {"min_referrals": 50, "rate": 0.30},
        "platinum": {"min_referrals": 100, "rate": 0.35},
    },
}


class ReferralService:
    """紹介報酬サービス"""

    def __init__(self, db_session=None):
        self.db = db_session
        self.config = REFERRAL_CONFIG

    def generate_referral_code(self, user_id: str) -> str:
        """ユーザー固有の紹介コードを生成"""
        raw = f"{user_id}_{uuid.uuid4().hex[:8]}"
        code = hashlib.md5(raw.encode()).hexdigest()[:8].upper()
        return code

    def generate_referral_link(self, referral_code: str, base_url: str = "") -> str:
        """紹介リンクを生成"""
        base = base_url or os.getenv("APP_URL", "https://tradepost-pro.com")
        return f"{base}/register?ref={referral_code}"

    def get_user_tier(self, total_referrals: int) -> Dict:
        """紹介数に基づくティアを取得"""
        current_tier = "bronze"
        current_rate = self.config["tiers"]["bronze"]["rate"]

        for tier_name, tier_config in self.config["tiers"].items():
            if total_referrals >= tier_config["min_referrals"]:
                current_tier = tier_name
                current_rate = tier_config["rate"]

        # 次のティアまでの残り
        tier_order = list(self.config["tiers"].keys())
        current_idx = tier_order.index(current_tier)
        next_tier = None
        remaining = 0

        if current_idx < len(tier_order) - 1:
            next_tier_name = tier_order[current_idx + 1]
            next_tier = {
                "name": next_tier_name,
                "rate": self.config["tiers"][next_tier_name]["rate"],
            }
            remaining = self.config["tiers"][next_tier_name]["min_referrals"] - total_referrals

        return {
            "tier": current_tier,
            "rate": current_rate,
            "rate_percent": f"{current_rate * 100:.0f}%",
            "next_tier": next_tier,
            "remaining_to_next": remaining,
        }

    def calculate_commission(
        self,
        plan_price: float,
        referrer_total_referrals: int,
    ) -> float:
        """紹介報酬を計算"""
        tier = self.get_user_tier(referrer_total_referrals)
        commission = plan_price * tier["rate"]
        return round(commission, 0)

    def get_referral_dashboard_data(self, user_id: str) -> Dict:
        """紹介ダッシュボード用のデータを取得（モック）"""
        # 実際にはDBから取得
        return {
            "referral_code": self.generate_referral_code(user_id),
            "referral_link": self.generate_referral_link(
                self.generate_referral_code(user_id)
            ),
            "total_referrals": 15,
            "active_referrals": 12,
            "total_earnings": 45600,
            "pending_payout": 12800,
            "available_payout": 32800,
            "tier": self.get_user_tier(15),
            "monthly_earnings": [
                {"month": "2026-01", "amount": 15200},
                {"month": "2026-02", "amount": 17600},
                {"month": "2026-03", "amount": 12800},
            ],
            "recent_referrals": [
                {
                    "date": "2026-03-10",
                    "user": "user_***123",
                    "plan": "スタンダード",
                    "commission": 596,
                    "status": "active",
                },
                {
                    "date": "2026-03-08",
                    "user": "user_***456",
                    "plan": "プレミアム",
                    "commission": 996,
                    "status": "active",
                },
                {
                    "date": "2026-03-05",
                    "user": "user_***789",
                    "plan": "ライト",
                    "commission": 396,
                    "status": "active",
                },
            ],
            "config": {
                "commission_rate": self.config["commission_rate"],
                "commission_months": self.config["commission_months"],
                "min_payout": self.config["min_payout"],
            },
        }

    def process_referral_signup(
        self,
        referral_code: str,
        new_user_id: str,
    ) -> Dict:
        """紹介経由のサインアップを処理"""
        logger.info(f"紹介サインアップ: code={referral_code}, user={new_user_id}")

        return {
            "success": True,
            "referral_code": referral_code,
            "new_user_id": new_user_id,
            "bonus_applied": self.config["bonus_first_referral"],
            "message": "紹介が正常に記録されました",
        }

    def request_payout(self, user_id: str, amount: float) -> Dict:
        """出金リクエスト"""
        if amount < self.config["min_payout"]:
            return {
                "success": False,
                "message": f"最低出金額は{self.config['min_payout']:,}円です",
            }

        return {
            "success": True,
            "user_id": user_id,
            "amount": amount,
            "estimated_date": (datetime.now() + timedelta(days=15)).strftime("%Y-%m-%d"),
            "message": f"{amount:,.0f}円の出金リクエストを受け付けました",
        }


# FastAPI ルーター
from fastapi import APIRouter

router = APIRouter(prefix="/api/referral", tags=["Referral Program"])


@router.get("/dashboard/{user_id}")
async def get_referral_dashboard(user_id: str):
    """紹介ダッシュボードデータを取得"""
    service = ReferralService()
    return service.get_referral_dashboard_data(user_id)


@router.get("/tier/{total_referrals}")
async def get_tier_info(total_referrals: int):
    """ティア情報を取得"""
    service = ReferralService()
    return service.get_user_tier(total_referrals)


@router.post("/signup")
async def process_signup(referral_code: str, new_user_id: str):
    """紹介サインアップを処理"""
    service = ReferralService()
    return service.process_referral_signup(referral_code, new_user_id)


@router.post("/payout")
async def request_payout(user_id: str, amount: float):
    """出金リクエスト"""
    service = ReferralService()
    return service.request_payout(user_id, amount)


if __name__ == "__main__":
    service = ReferralService()

    # テスト
    code = service.generate_referral_code("user_001")
    link = service.generate_referral_link(code)
    print(f"紹介コード: {code}")
    print(f"紹介リンク: {link}")

    # ティア計算
    for count in [0, 5, 10, 25, 50, 75, 100, 150]:
        tier = service.get_user_tier(count)
        print(f"紹介{count}人: {tier['tier']} ({tier['rate_percent']})")

    # 報酬計算
    plans = {"ライト": 1980, "スタンダード": 2980, "プレミアム": 4980}
    for plan_name, price in plans.items():
        commission = service.calculate_commission(price, 15)
        print(f"{plan_name}({price}円) → 報酬: {commission:,.0f}円")

    # ダッシュボードデータ
    dashboard = service.get_referral_dashboard_data("user_001")
    print(f"\n=== 紹介ダッシュボード ===")
    print(f"総紹介数: {dashboard['total_referrals']}人")
    print(f"総報酬: {dashboard['total_earnings']:,}円")
    print(f"ティア: {dashboard['tier']['tier']} ({dashboard['tier']['rate_percent']})")
