"""
TradePost Pro - 年額プラン割引サービス
年払いで2ヶ月分無料の割引機能
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


@dataclass
class PlanPricing:
    """プラン料金"""
    plan_id: str = ""
    plan_name: str = ""
    monthly_price: int = 0
    annual_price: int = 0          # 年額（2ヶ月分割引）
    annual_monthly_equiv: int = 0  # 年額の月あたり換算
    savings_amount: int = 0        # 年間節約額
    savings_percent: float = 0.0   # 割引率
    stripe_monthly_price_id: str = ""
    stripe_annual_price_id: str = ""


# 料金プラン定義
PLAN_PRICING = {
    "light": PlanPricing(
        plan_id="light",
        plan_name="ライト",
        monthly_price=1980,
        annual_price=19800,         # 1980 * 10 = 19,800円（2ヶ月無料）
        annual_monthly_equiv=1650,  # 19800 / 12
        savings_amount=3960,        # 1980 * 2
        savings_percent=16.7,
    ),
    "standard": PlanPricing(
        plan_id="standard",
        plan_name="スタンダード",
        monthly_price=2980,
        annual_price=29800,         # 2980 * 10 = 29,800円（2ヶ月無料）
        annual_monthly_equiv=2483,
        savings_amount=5960,
        savings_percent=16.7,
    ),
    "premium": PlanPricing(
        plan_id="premium",
        plan_name="プレミアム",
        monthly_price=4980,
        annual_price=49800,         # 4980 * 10 = 49,800円（2ヶ月無料）
        annual_monthly_equiv=4150,
        savings_amount=9960,
        savings_percent=16.7,
    ),
}


@dataclass
class Subscription:
    """サブスクリプション"""
    user_id: str = ""
    plan_id: str = ""
    billing_cycle: str = ""
    price: int = 0
    started_at: str = ""
    current_period_end: str = ""
    is_active: bool = True
    auto_renew: bool = True
    stripe_subscription_id: str = ""


class AnnualPlanService:
    """年額プラン割引サービス"""

    def __init__(self):
        self.plans = PLAN_PRICING
        self.subscriptions: Dict[str, Subscription] = {}

    # ============================================================
    # 料金情報
    # ============================================================

    def get_pricing_table(self) -> List[Dict]:
        """料金テーブルを取得"""
        table = []
        for plan in self.plans.values():
            table.append({
                "plan_id": plan.plan_id,
                "plan_name": plan.plan_name,
                "monthly": {
                    "price": plan.monthly_price,
                    "display": f"¥{plan.monthly_price:,}/月",
                },
                "annual": {
                    "price": plan.annual_price,
                    "monthly_equiv": plan.annual_monthly_equiv,
                    "display": f"¥{plan.annual_price:,}/年（¥{plan.annual_monthly_equiv:,}/月相当）",
                    "savings": f"¥{plan.savings_amount:,}お得（{plan.savings_percent}%OFF）",
                },
            })
        return table

    def get_plan_pricing(self, plan_id: str) -> Optional[PlanPricing]:
        """プラン料金を取得"""
        return self.plans.get(plan_id)

    # ============================================================
    # サブスクリプション管理
    # ============================================================

    def subscribe(
        self,
        user_id: str,
        plan_id: str,
        billing_cycle: BillingCycle,
    ) -> Dict:
        """サブスクリプションを開始"""
        plan = self.plans.get(plan_id)
        if not plan:
            return {"status": "error", "message": "プランが見つかりません"}

        # 既存サブスクリプションのチェック
        if user_id in self.subscriptions and self.subscriptions[user_id].is_active:
            return {"status": "error", "message": "既にアクティブなサブスクリプションがあります。変更はchange_planを使用してください"}

        now = datetime.now()
        if billing_cycle == BillingCycle.ANNUAL:
            price = plan.annual_price
            period_end = now + timedelta(days=365)
        else:
            price = plan.monthly_price
            period_end = now + timedelta(days=30)

        sub = Subscription(
            user_id=user_id,
            plan_id=plan_id,
            billing_cycle=billing_cycle.value,
            price=price,
            started_at=now.isoformat(),
            current_period_end=period_end.isoformat(),
            is_active=True,
        )

        self.subscriptions[user_id] = sub

        return {
            "status": "success",
            "plan": plan.plan_name,
            "billing_cycle": billing_cycle.value,
            "price": price,
            "display_price": f"¥{price:,}{'/ 年' if billing_cycle == BillingCycle.ANNUAL else '/月'}",
            "period_end": period_end.strftime("%Y-%m-%d"),
        }

    def change_plan(
        self,
        user_id: str,
        new_plan_id: str,
        new_billing_cycle: Optional[BillingCycle] = None,
    ) -> Dict:
        """プラン変更"""
        if user_id not in self.subscriptions:
            return {"status": "error", "message": "サブスクリプションが見つかりません"}

        current_sub = self.subscriptions[user_id]
        new_plan = self.plans.get(new_plan_id)
        if not new_plan:
            return {"status": "error", "message": "プランが見つかりません"}

        billing_cycle = new_billing_cycle or BillingCycle(current_sub.billing_cycle)

        # 日割り計算
        proration = self._calculate_proration(current_sub, new_plan, billing_cycle)

        # 更新
        now = datetime.now()
        if billing_cycle == BillingCycle.ANNUAL:
            new_price = new_plan.annual_price
            period_end = now + timedelta(days=365)
        else:
            new_price = new_plan.monthly_price
            period_end = now + timedelta(days=30)

        current_sub.plan_id = new_plan_id
        current_sub.billing_cycle = billing_cycle.value
        current_sub.price = new_price
        current_sub.current_period_end = period_end.isoformat()

        return {
            "status": "success",
            "old_plan": current_sub.plan_id,
            "new_plan": new_plan.plan_name,
            "billing_cycle": billing_cycle.value,
            "new_price": new_price,
            "proration": proration,
        }

    def switch_to_annual(self, user_id: str) -> Dict:
        """月額から年額に切り替え"""
        if user_id not in self.subscriptions:
            return {"status": "error", "message": "サブスクリプションが見つかりません"}

        sub = self.subscriptions[user_id]
        if sub.billing_cycle == BillingCycle.ANNUAL.value:
            return {"status": "error", "message": "既に年額プランです"}

        plan = self.plans.get(sub.plan_id)
        if not plan:
            return {"status": "error", "message": "プランが見つかりません"}

        now = datetime.now()
        sub.billing_cycle = BillingCycle.ANNUAL.value
        sub.price = plan.annual_price
        sub.current_period_end = (now + timedelta(days=365)).isoformat()

        return {
            "status": "success",
            "message": f"年額プランに切り替えました（¥{plan.savings_amount:,}お得！）",
            "new_price": plan.annual_price,
            "savings": plan.savings_amount,
            "period_end": sub.current_period_end,
        }

    def cancel_subscription(self, user_id: str) -> Dict:
        """サブスクリプション解約（期間終了まで利用可能）"""
        if user_id not in self.subscriptions:
            return {"status": "error", "message": "サブスクリプションが見つかりません"}

        sub = self.subscriptions[user_id]
        sub.auto_renew = False

        return {
            "status": "success",
            "message": f"解約を受け付けました。{sub.current_period_end[:10]}まで引き続きご利用いただけます。",
            "effective_until": sub.current_period_end,
        }

    # ============================================================
    # 日割り計算
    # ============================================================

    def _calculate_proration(
        self,
        current_sub: Subscription,
        new_plan: PlanPricing,
        new_cycle: BillingCycle,
    ) -> Dict:
        """日割り計算"""
        now = datetime.now()
        period_end = datetime.fromisoformat(current_sub.current_period_end)
        remaining_days = max((period_end - now).days, 0)

        if current_sub.billing_cycle == BillingCycle.ANNUAL.value:
            daily_rate_old = current_sub.price / 365
        else:
            daily_rate_old = current_sub.price / 30

        credit = round(daily_rate_old * remaining_days)

        if new_cycle == BillingCycle.ANNUAL:
            new_price = new_plan.annual_price
        else:
            new_price = new_plan.monthly_price

        charge = max(new_price - credit, 0)

        return {
            "remaining_days": remaining_days,
            "credit": credit,
            "new_price": new_price,
            "charge_now": charge,
        }

    # ============================================================
    # 統計
    # ============================================================

    def get_subscription_stats(self) -> Dict:
        """サブスクリプション統計"""
        active_subs = [s for s in self.subscriptions.values() if s.is_active]
        monthly_subs = [s for s in active_subs if s.billing_cycle == BillingCycle.MONTHLY.value]
        annual_subs = [s for s in active_subs if s.billing_cycle == BillingCycle.ANNUAL.value]

        mrr_monthly = sum(s.price for s in monthly_subs)
        mrr_annual = sum(s.price / 12 for s in annual_subs)

        return {
            "total_active": len(active_subs),
            "monthly_subscribers": len(monthly_subs),
            "annual_subscribers": len(annual_subs),
            "annual_ratio": round(len(annual_subs) / max(len(active_subs), 1) * 100, 1),
            "mrr": round(mrr_monthly + mrr_annual),
            "arr": round((mrr_monthly + mrr_annual) * 12),
        }


# テスト用
if __name__ == "__main__":
    service = AnnualPlanService()

    print("=== 料金テーブル ===")
    for plan in service.get_pricing_table():
        print(f"\n  【{plan['plan_name']}】")
        print(f"    月額: {plan['monthly']['display']}")
        print(f"    年額: {plan['annual']['display']}")
        print(f"    節約: {plan['annual']['savings']}")

    print(f"\n=== サブスクリプション テスト ===")
    # 月額で開始
    result = service.subscribe("user1", "standard", BillingCycle.MONTHLY)
    print(f"  月額開始: {result}")

    # 年額で開始
    result = service.subscribe("user2", "premium", BillingCycle.ANNUAL)
    print(f"  年額開始: {result}")

    # 年額に切り替え
    result = service.switch_to_annual("user1")
    print(f"  年額切替: {result}")

    # 解約
    result = service.cancel_subscription("user2")
    print(f"  解約: {result}")

    print(f"\n=== 統計 ===")
    stats = service.get_subscription_stats()
    print(f"  アクティブ: {stats['total_active']}人")
    print(f"  月額: {stats['monthly_subscribers']}人 / 年額: {stats['annual_subscribers']}人")
    print(f"  年額率: {stats['annual_ratio']}%")
    print(f"  MRR: ¥{stats['mrr']:,} / ARR: ¥{stats['arr']:,}")

    print("\n✓ 年額プラン割引サービス テスト完了")
