"""
TradePost Pro - クーポン・プロモーション機能
期間限定割引コードの発行・管理
"""

import random
import string
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class DiscountType(str, Enum):
    PERCENTAGE = "percentage"   # パーセント割引
    FIXED = "fixed"             # 固定額割引
    FREE_TRIAL = "free_trial"   # 無料期間延長


class CouponStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    DEPLETED = "depleted"       # 使用回数上限
    DISABLED = "disabled"


@dataclass
class Coupon:
    """クーポン"""
    code: str = ""
    name: str = ""
    description: str = ""
    discount_type: str = ""
    discount_value: float = 0.0     # %またはJPY
    applicable_plans: List[str] = field(default_factory=list)  # 空=全プラン
    min_billing_cycle: str = ""     # monthly, annual, 空=制限なし
    max_uses: int = 0               # 0=無制限
    current_uses: int = 0
    max_uses_per_user: int = 1
    valid_from: str = ""
    valid_until: str = ""
    status: str = "active"
    created_by: str = "admin"
    created_at: str = ""


@dataclass
class CouponRedemption:
    """クーポン利用履歴"""
    redemption_id: str = ""
    coupon_code: str = ""
    user_id: str = ""
    plan_id: str = ""
    original_price: int = 0
    discount_amount: int = 0
    final_price: int = 0
    redeemed_at: str = ""


class CouponService:
    """クーポン・プロモーションサービス"""

    def __init__(self):
        self.coupons: Dict[str, Coupon] = {}
        self.redemptions: List[CouponRedemption] = []
        self._init_default_coupons()

    def _init_default_coupons(self):
        """デフォルトクーポンを初期化"""
        now = datetime.now()
        default_coupons = [
            Coupon(
                code="WELCOME20",
                name="新規登録20%OFF",
                description="新規登録者限定20%OFFクーポン",
                discount_type=DiscountType.PERCENTAGE.value,
                discount_value=20.0,
                max_uses=0,
                max_uses_per_user=1,
                valid_from=now.isoformat(),
                valid_until=(now + timedelta(days=365)).isoformat(),
                created_at=now.isoformat(),
            ),
            Coupon(
                code="ANNUAL500",
                name="年額プラン500円OFF",
                description="年額プラン限定500円割引",
                discount_type=DiscountType.FIXED.value,
                discount_value=500,
                min_billing_cycle="annual",
                max_uses=100,
                max_uses_per_user=1,
                valid_from=now.isoformat(),
                valid_until=(now + timedelta(days=90)).isoformat(),
                created_at=now.isoformat(),
            ),
            Coupon(
                code="PREMIUM30",
                name="プレミアムプラン30%OFF",
                description="プレミアムプラン限定30%OFF（初月のみ）",
                discount_type=DiscountType.PERCENTAGE.value,
                discount_value=30.0,
                applicable_plans=["premium"],
                max_uses=50,
                max_uses_per_user=1,
                valid_from=now.isoformat(),
                valid_until=(now + timedelta(days=60)).isoformat(),
                created_at=now.isoformat(),
            ),
            Coupon(
                code="FREETRIAL14",
                name="14日間無料トライアル",
                description="通常7日間のトライアルを14日間に延長",
                discount_type=DiscountType.FREE_TRIAL.value,
                discount_value=14,  # 日数
                max_uses=200,
                max_uses_per_user=1,
                valid_from=now.isoformat(),
                valid_until=(now + timedelta(days=180)).isoformat(),
                created_at=now.isoformat(),
            ),
        ]

        for coupon in default_coupons:
            self.coupons[coupon.code] = coupon

    # ============================================================
    # クーポン管理（管理者向け）
    # ============================================================

    def create_coupon(
        self,
        name: str,
        discount_type: DiscountType,
        discount_value: float,
        valid_days: int = 30,
        max_uses: int = 0,
        code: Optional[str] = None,
        applicable_plans: Optional[List[str]] = None,
        min_billing_cycle: str = "",
        description: str = "",
    ) -> Coupon:
        """クーポンを作成"""
        if not code:
            code = self._generate_code()

        now = datetime.now()
        coupon = Coupon(
            code=code.upper(),
            name=name,
            description=description or name,
            discount_type=discount_type.value,
            discount_value=discount_value,
            applicable_plans=applicable_plans or [],
            min_billing_cycle=min_billing_cycle,
            max_uses=max_uses,
            max_uses_per_user=1,
            valid_from=now.isoformat(),
            valid_until=(now + timedelta(days=valid_days)).isoformat(),
            created_at=now.isoformat(),
        )

        self.coupons[coupon.code] = coupon
        return coupon

    def _generate_code(self, length: int = 8) -> str:
        """ランダムなクーポンコードを生成"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = "TP-" + "".join(random.choices(chars, k=length))
            if code not in self.coupons:
                return code

    def disable_coupon(self, code: str) -> Dict:
        """クーポンを無効化"""
        coupon = self.coupons.get(code.upper())
        if not coupon:
            return {"status": "error", "message": "クーポンが見つかりません"}

        coupon.status = CouponStatus.DISABLED.value
        return {"status": "success", "message": f"クーポン {code} を無効化しました"}

    def get_all_coupons(self, active_only: bool = False) -> List[Coupon]:
        """全クーポンを取得"""
        coupons = list(self.coupons.values())
        if active_only:
            now = datetime.now().isoformat()
            coupons = [
                c for c in coupons
                if c.status == CouponStatus.ACTIVE.value
                and c.valid_from <= now
                and c.valid_until >= now
                and (c.max_uses == 0 or c.current_uses < c.max_uses)
            ]
        return coupons

    # ============================================================
    # クーポン適用（ユーザー向け）
    # ============================================================

    def validate_coupon(
        self,
        code: str,
        user_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
    ) -> Dict:
        """クーポンの有効性を検証"""
        coupon = self.coupons.get(code.upper())

        if not coupon:
            return {"valid": False, "message": "無効なクーポンコードです"}

        # ステータスチェック
        if coupon.status != CouponStatus.ACTIVE.value:
            return {"valid": False, "message": "このクーポンは現在利用できません"}

        # 期間チェック
        now = datetime.now().isoformat()
        if now < coupon.valid_from or now > coupon.valid_until:
            return {"valid": False, "message": "このクーポンは有効期間外です"}

        # 使用回数チェック
        if coupon.max_uses > 0 and coupon.current_uses >= coupon.max_uses:
            return {"valid": False, "message": "このクーポンは使用回数の上限に達しました"}

        # ユーザー使用回数チェック
        user_uses = sum(1 for r in self.redemptions if r.coupon_code == code.upper() and r.user_id == user_id)
        if user_uses >= coupon.max_uses_per_user:
            return {"valid": False, "message": "このクーポンは既にご利用済みです"}

        # プラン適用チェック
        if coupon.applicable_plans and plan_id not in coupon.applicable_plans:
            plan_names = ", ".join(coupon.applicable_plans)
            return {"valid": False, "message": f"このクーポンは{plan_names}プランのみ適用可能です"}

        # 請求サイクルチェック
        if coupon.min_billing_cycle and billing_cycle != coupon.min_billing_cycle:
            return {"valid": False, "message": f"このクーポンは{coupon.min_billing_cycle}プランのみ適用可能です"}

        return {"valid": True, "coupon": coupon, "message": "クーポンが適用可能です"}

    def apply_coupon(
        self,
        code: str,
        user_id: str,
        plan_id: str,
        original_price: int,
        billing_cycle: str = "monthly",
    ) -> Dict:
        """クーポンを適用"""
        validation = self.validate_coupon(code, user_id, plan_id, billing_cycle)
        if not validation["valid"]:
            return {"status": "error", "message": validation["message"]}

        coupon = validation["coupon"]

        # 割引計算
        if coupon.discount_type == DiscountType.PERCENTAGE.value:
            discount = round(original_price * coupon.discount_value / 100)
        elif coupon.discount_type == DiscountType.FIXED.value:
            discount = int(coupon.discount_value)
        elif coupon.discount_type == DiscountType.FREE_TRIAL.value:
            discount = original_price  # 全額割引（トライアル期間）
        else:
            discount = 0

        discount = min(discount, original_price)
        final_price = original_price - discount

        # 利用記録
        redemption = CouponRedemption(
            redemption_id=f"RDM-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.redemptions)+1}",
            coupon_code=code.upper(),
            user_id=user_id,
            plan_id=plan_id,
            original_price=original_price,
            discount_amount=discount,
            final_price=final_price,
            redeemed_at=datetime.now().isoformat(),
        )
        self.redemptions.append(redemption)
        coupon.current_uses += 1

        # 使用上限チェック
        if coupon.max_uses > 0 and coupon.current_uses >= coupon.max_uses:
            coupon.status = CouponStatus.DEPLETED.value

        return {
            "status": "success",
            "coupon_code": code.upper(),
            "coupon_name": coupon.name,
            "original_price": original_price,
            "discount_amount": discount,
            "final_price": final_price,
            "discount_display": f"-¥{discount:,}" if coupon.discount_type != DiscountType.FREE_TRIAL.value else f"{int(coupon.discount_value)}日間無料",
        }

    # ============================================================
    # バルク生成（キャンペーン用）
    # ============================================================

    def generate_bulk_coupons(
        self,
        count: int,
        name: str,
        discount_type: DiscountType,
        discount_value: float,
        valid_days: int = 30,
        prefix: str = "CAMP",
    ) -> List[str]:
        """キャンペーン用クーポンを一括生成"""
        codes = []
        for _ in range(count):
            code = f"{prefix}-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            coupon = Coupon(
                code=code,
                name=name,
                description=f"{name}（キャンペーン）",
                discount_type=discount_type.value,
                discount_value=discount_value,
                max_uses=1,
                max_uses_per_user=1,
                valid_from=datetime.now().isoformat(),
                valid_until=(datetime.now() + timedelta(days=valid_days)).isoformat(),
                created_at=datetime.now().isoformat(),
            )
            self.coupons[code] = coupon
            codes.append(code)
        return codes

    # ============================================================
    # 統計
    # ============================================================

    def get_stats(self) -> Dict:
        """クーポン統計"""
        active = self.get_all_coupons(active_only=True)
        total_discount = sum(r.discount_amount for r in self.redemptions)

        return {
            "total_coupons": len(self.coupons),
            "active_coupons": len(active),
            "total_redemptions": len(self.redemptions),
            "total_discount_amount": total_discount,
            "avg_discount": round(total_discount / max(len(self.redemptions), 1)),
        }


# テスト用
if __name__ == "__main__":
    service = CouponService()

    print("=== 利用可能クーポン ===")
    for coupon in service.get_all_coupons(active_only=True):
        if coupon.discount_type == "percentage":
            discount_str = f"{coupon.discount_value}%OFF"
        elif coupon.discount_type == "fixed":
            discount_str = f"¥{int(coupon.discount_value):,}OFF"
        else:
            discount_str = f"{int(coupon.discount_value)}日間無料"
        print(f"  [{coupon.code}] {coupon.name} ({discount_str})")

    print(f"\n=== クーポン適用テスト ===")
    # 20%OFFクーポン
    result = service.apply_coupon("WELCOME20", "user1", "standard", 2980)
    print(f"  WELCOME20: {result['original_price']:,}円 → {result['final_price']:,}円 ({result['discount_display']})")

    # 年額500円OFF
    result = service.apply_coupon("ANNUAL500", "user2", "standard", 29800, "annual")
    print(f"  ANNUAL500: {result['original_price']:,}円 → {result['final_price']:,}円 ({result['discount_display']})")

    # プレミアム30%OFF
    result = service.apply_coupon("PREMIUM30", "user3", "premium", 4980)
    print(f"  PREMIUM30: {result['original_price']:,}円 → {result['final_price']:,}円 ({result['discount_display']})")

    # 無効なケース
    result = service.apply_coupon("PREMIUM30", "user4", "standard", 2980)
    print(f"  PREMIUM30(standard): {result['message']}")

    # 重複使用
    result = service.apply_coupon("WELCOME20", "user1", "standard", 2980)
    print(f"  WELCOME20(重複): {result['message']}")

    print(f"\n=== バルク生成 ===")
    codes = service.generate_bulk_coupons(5, "春のキャンペーン", DiscountType.PERCENTAGE, 15.0, 30)
    for code in codes:
        print(f"  {code}")

    print(f"\n=== 統計 ===")
    stats = service.get_stats()
    print(f"  総クーポン: {stats['total_coupons']}件")
    print(f"  利用回数: {stats['total_redemptions']}回")
    print(f"  総割引額: ¥{stats['total_discount_amount']:,}")

    print("\n✓ クーポン・プロモーションサービス テスト完了")
