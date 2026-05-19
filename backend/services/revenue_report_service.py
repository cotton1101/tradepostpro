"""
TradePost Pro - 収益レポートサービス
MRR、チャーン率、LTV、ARPU等の自動計算・レポート生成
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


@dataclass
class SubscriptionRecord:
    """サブスクリプション記録"""
    user_id: str = ""
    plan: str = ""
    monthly_amount: int = 0
    started_at: str = ""
    cancelled_at: Optional[str] = None
    is_active: bool = True


@dataclass
class RevenueSnapshot:
    """収益スナップショット（月次）"""
    month: str = ""  # YYYY-MM
    mrr: int = 0
    arr: int = 0
    active_subscribers: int = 0
    new_subscribers: int = 0
    churned_subscribers: int = 0
    churn_rate: float = 0.0
    arpu: float = 0.0
    ltv: float = 0.0
    revenue_by_plan: Dict[str, int] = field(default_factory=dict)
    growth_rate: float = 0.0


class RevenueReportService:
    """収益レポートサービス"""

    PLAN_PRICES = {
        "lite": 1980,
        "standard": 2980,
        "premium": 4980,
    }

    def __init__(self):
        self.subscriptions: List[SubscriptionRecord] = []
        self.snapshots: List[RevenueSnapshot] = []

    # ============================================================
    # サブスクリプション管理
    # ============================================================

    def add_subscription(self, record: SubscriptionRecord):
        """サブスクリプション追加"""
        self.subscriptions.append(record)

    def cancel_subscription(self, user_id: str, cancelled_at: str):
        """サブスクリプション解約"""
        for sub in self.subscriptions:
            if sub.user_id == user_id and sub.is_active:
                sub.is_active = False
                sub.cancelled_at = cancelled_at
                break

    # ============================================================
    # メトリクス計算
    # ============================================================

    def calculate_mrr(self, as_of: Optional[str] = None) -> int:
        """MRR（月次経常収益）を計算"""
        as_of = as_of or datetime.now().isoformat()
        mrr = 0
        for sub in self.subscriptions:
            if sub.is_active and sub.started_at <= as_of:
                mrr += sub.monthly_amount
            elif sub.cancelled_at and sub.cancelled_at > as_of and sub.started_at <= as_of:
                mrr += sub.monthly_amount
        return mrr

    def calculate_arr(self, as_of: Optional[str] = None) -> int:
        """ARR（年次経常収益）を計算"""
        return self.calculate_mrr(as_of) * 12

    def calculate_active_subscribers(self, as_of: Optional[str] = None) -> int:
        """アクティブサブスクライバー数"""
        as_of = as_of or datetime.now().isoformat()
        count = 0
        for sub in self.subscriptions:
            if sub.is_active and sub.started_at <= as_of:
                count += 1
            elif sub.cancelled_at and sub.cancelled_at > as_of and sub.started_at <= as_of:
                count += 1
        return count

    def calculate_churn_rate(self, month: str) -> float:
        """月次チャーン率を計算"""
        month_start = f"{month}-01"
        next_month = datetime.strptime(month_start, "%Y-%m-%d")
        if next_month.month == 12:
            month_end = f"{next_month.year + 1}-01-01"
        else:
            month_end = f"{next_month.year}-{next_month.month + 1:02d}-01"

        # 月初のアクティブユーザー
        active_start = self.calculate_active_subscribers(month_start)
        if active_start == 0:
            return 0.0

        # 月中の解約数
        churned = sum(
            1 for sub in self.subscriptions
            if sub.cancelled_at and month_start <= sub.cancelled_at < month_end
        )

        return round(churned / active_start * 100, 2)

    def calculate_arpu(self, as_of: Optional[str] = None) -> float:
        """ARPU（ユーザー平均収益）を計算"""
        active = self.calculate_active_subscribers(as_of)
        if active == 0:
            return 0.0
        mrr = self.calculate_mrr(as_of)
        return round(mrr / active, 0)

    def calculate_ltv(self, avg_churn_rate: Optional[float] = None) -> float:
        """LTV（顧客生涯価値）を計算"""
        arpu = self.calculate_arpu()
        if avg_churn_rate is None:
            # 直近3ヶ月の平均チャーン率
            now = datetime.now()
            rates = []
            for i in range(3):
                month = (now - timedelta(days=30 * (i + 1))).strftime("%Y-%m")
                rate = self.calculate_churn_rate(month)
                if rate > 0:
                    rates.append(rate)
            avg_churn_rate = sum(rates) / len(rates) if rates else 5.0

        if avg_churn_rate <= 0:
            return arpu * 24  # チャーン率0の場合は24ヶ月で計算

        return round(arpu / (avg_churn_rate / 100), 0)

    def calculate_revenue_by_plan(self, as_of: Optional[str] = None) -> Dict[str, Dict]:
        """プラン別収益"""
        as_of = as_of or datetime.now().isoformat()
        plan_stats: Dict[str, Dict] = {}

        for sub in self.subscriptions:
            if sub.is_active and sub.started_at <= as_of:
                plan = sub.plan
                if plan not in plan_stats:
                    plan_stats[plan] = {"subscribers": 0, "revenue": 0}
                plan_stats[plan]["subscribers"] += 1
                plan_stats[plan]["revenue"] += sub.monthly_amount

        return plan_stats

    # ============================================================
    # レポート生成
    # ============================================================

    def generate_monthly_snapshot(self, month: str) -> RevenueSnapshot:
        """月次スナップショットを生成"""
        month_start = f"{month}-01"
        next_month_dt = datetime.strptime(month_start, "%Y-%m-%d")
        if next_month_dt.month == 12:
            month_end = f"{next_month_dt.year + 1}-01-01"
        else:
            month_end = f"{next_month_dt.year}-{next_month_dt.month + 1:02d}-01"

        mrr = self.calculate_mrr(month_end)
        active = self.calculate_active_subscribers(month_end)
        churn_rate = self.calculate_churn_rate(month)

        # 新規加入数
        new_subs = sum(
            1 for sub in self.subscriptions
            if month_start <= sub.started_at < month_end
        )

        # 解約数
        churned = sum(
            1 for sub in self.subscriptions
            if sub.cancelled_at and month_start <= sub.cancelled_at < month_end
        )

        # プラン別収益
        plan_revenue = {}
        for sub in self.subscriptions:
            if sub.is_active and sub.started_at < month_end:
                plan_revenue[sub.plan] = plan_revenue.get(sub.plan, 0) + sub.monthly_amount

        # 前月比成長率
        prev_month_dt = next_month_dt - timedelta(days=1)
        prev_month = prev_month_dt.strftime("%Y-%m")
        prev_mrr = self.calculate_mrr(f"{prev_month}-28")
        growth_rate = round((mrr - prev_mrr) / prev_mrr * 100, 2) if prev_mrr > 0 else 0

        snapshot = RevenueSnapshot(
            month=month,
            mrr=mrr,
            arr=mrr * 12,
            active_subscribers=active,
            new_subscribers=new_subs,
            churned_subscribers=churned,
            churn_rate=churn_rate,
            arpu=round(mrr / active, 0) if active > 0 else 0,
            ltv=self.calculate_ltv(churn_rate if churn_rate > 0 else None),
            revenue_by_plan=plan_revenue,
            growth_rate=growth_rate,
        )

        self.snapshots.append(snapshot)
        return snapshot

    def generate_executive_summary(self) -> Dict:
        """エグゼクティブサマリーを生成"""
        mrr = self.calculate_mrr()
        arr = self.calculate_arr()
        active = self.calculate_active_subscribers()
        arpu = self.calculate_arpu()
        ltv = self.calculate_ltv()
        plan_stats = self.calculate_revenue_by_plan()

        return {
            "generated_at": datetime.now().isoformat(),
            "key_metrics": {
                "mrr": mrr,
                "mrr_formatted": f"¥{mrr:,}",
                "arr": arr,
                "arr_formatted": f"¥{arr:,}",
                "active_subscribers": active,
                "arpu": arpu,
                "arpu_formatted": f"¥{arpu:,.0f}",
                "ltv": ltv,
                "ltv_formatted": f"¥{ltv:,.0f}",
            },
            "plan_breakdown": {
                plan: {
                    "subscribers": data["subscribers"],
                    "revenue": data["revenue"],
                    "revenue_formatted": f"¥{data['revenue']:,}",
                    "share": round(data["revenue"] / mrr * 100, 1) if mrr > 0 else 0,
                }
                for plan, data in plan_stats.items()
            },
            "health_indicators": {
                "ltv_cac_ratio": round(ltv / 5000, 1) if ltv > 0 else 0,  # CAC=5000円想定
                "churn_status": "良好" if self.calculate_churn_rate(
                    datetime.now().strftime("%Y-%m")) < 5 else "要改善",
            },
        }


# テスト用
if __name__ == "__main__":
    import random

    service = RevenueReportService()

    # サンプルデータ生成
    plans = ["lite", "standard", "premium"]
    weights = [0.5, 0.35, 0.15]
    base_date = datetime.now() - timedelta(days=90)

    for i in range(80):
        plan = random.choices(plans, weights=weights)[0]
        start = base_date + timedelta(days=random.randint(0, 80))
        sub = SubscriptionRecord(
            user_id=f"user_{i:03d}",
            plan=plan,
            monthly_amount=RevenueReportService.PLAN_PRICES[plan],
            started_at=start.isoformat(),
            is_active=True,
        )
        service.add_subscription(sub)

    # 一部解約
    for i in random.sample(range(80), 8):
        cancel_date = base_date + timedelta(days=random.randint(30, 90))
        service.cancel_subscription(f"user_{i:03d}", cancel_date.isoformat())

    # エグゼクティブサマリー
    summary = service.generate_executive_summary()
    km = summary["key_metrics"]
    print(f"=== エグゼクティブサマリー ===")
    print(f"MRR: {km['mrr_formatted']}")
    print(f"ARR: {km['arr_formatted']}")
    print(f"アクティブユーザー: {km['active_subscribers']}人")
    print(f"ARPU: {km['arpu_formatted']}")
    print(f"LTV: {km['ltv_formatted']}")

    print(f"\n=== プラン別内訳 ===")
    for plan, data in summary["plan_breakdown"].items():
        print(f"  {plan}: {data['subscribers']}人, {data['revenue_formatted']} ({data['share']:.1f}%)")

    print(f"\n=== 健全性指標 ===")
    hi = summary["health_indicators"]
    print(f"LTV/CAC比率: {hi['ltv_cac_ratio']}x")
    print(f"チャーン状況: {hi['churn_status']}")

    print("\n✓ 収益レポートサービス テスト完了")
