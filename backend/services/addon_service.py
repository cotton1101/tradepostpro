"""
TradePost Pro - アドオン課金機能
テンプレート単品購入、追加SNS枠の個別課金
"""

from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class AddonType(str, Enum):
    TEMPLATE = "template"       # テンプレート単品
    SNS_SLOT = "sns_slot"       # 追加SNS枠
    AI_TEXT = "ai_text"         # AI投稿文生成
    VIDEO = "video"             # 動画生成
    COPY_TRADE = "copy_trade"   # コピートレード
    AUTO_REPLY = "auto_reply"   # 自動返信Bot
    ANALYTICS = "analytics"     # 高度な分析


class PurchaseType(str, Enum):
    ONE_TIME = "one_time"       # 買い切り
    MONTHLY = "monthly"         # 月額


@dataclass
class Addon:
    """アドオン商品"""
    addon_id: str = ""
    name: str = ""
    description: str = ""
    addon_type: str = ""
    purchase_type: str = ""
    price: int = 0              # 円
    stripe_price_id: str = ""
    is_active: bool = True
    features: List[str] = field(default_factory=list)


@dataclass
class UserAddon:
    """ユーザーが購入したアドオン"""
    user_id: str = ""
    addon_id: str = ""
    purchased_at: str = ""
    expires_at: str = ""        # 月額の場合
    is_active: bool = True
    stripe_subscription_id: str = ""


# 利用可能なアドオン一覧
ADDON_CATALOG = [
    Addon(
        addon_id="addon_template_gold",
        name="ゴールドラグジュアリーテンプレート",
        description="高級感あふれるゴールド×ブラックのプレミアムテンプレート",
        addon_type=AddonType.TEMPLATE.value,
        purchase_type=PurchaseType.ONE_TIME.value,
        price=980,
        features=["ゴールドラグジュアリーデザイン", "カスタムカラー対応"],
    ),
    Addon(
        addon_id="addon_template_gradient",
        name="グラデーションウェーブテンプレート",
        description="モダンなグラデーションデザインのテンプレート",
        addon_type=AddonType.TEMPLATE.value,
        purchase_type=PurchaseType.ONE_TIME.value,
        price=980,
        features=["パープル→ブルーのグラデーション", "アニメーション対応"],
    ),
    Addon(
        addon_id="addon_template_custom",
        name="カスタムテンプレート作成権",
        description="オリジナルテンプレートを自由に作成できる権利",
        addon_type=AddonType.TEMPLATE.value,
        purchase_type=PurchaseType.ONE_TIME.value,
        price=2980,
        features=["テンプレートエディタ利用可", "無制限作成", "画像アップロード"],
    ),
    Addon(
        addon_id="addon_sns_slot",
        name="追加SNS枠（1枠）",
        description="投稿先SNSを1つ追加できます",
        addon_type=AddonType.SNS_SLOT.value,
        purchase_type=PurchaseType.MONTHLY.value,
        price=500,
        features=["SNS枠+1", "全SNS対応"],
    ),
    Addon(
        addon_id="addon_ai_text",
        name="AI投稿文生成",
        description="GPTによる魅力的な投稿文の自動生成",
        addon_type=AddonType.AI_TEXT.value,
        purchase_type=PurchaseType.MONTHLY.value,
        price=980,
        features=["AI投稿文生成", "SNS別最適化", "ハッシュタグ自動選定"],
    ),
    Addon(
        addon_id="addon_video",
        name="動画生成",
        description="取引結果のスライドショー動画を自動生成",
        addon_type=AddonType.VIDEO.value,
        purchase_type=PurchaseType.MONTHLY.value,
        price=1480,
        features=["スライドショー動画", "BGM付き", "TikTok最適化"],
    ),
    Addon(
        addon_id="addon_copy_trade",
        name="コピートレード連携",
        description="シグナル配信・フォロー機能",
        addon_type=AddonType.COPY_TRADE.value,
        purchase_type=PurchaseType.MONTHLY.value,
        price=1980,
        features=["シグナル配信", "フォロー機能", "成績ランキング"],
    ),
    Addon(
        addon_id="addon_auto_reply",
        name="自動返信Bot",
        description="SNSコメントへの自動返信機能",
        addon_type=AddonType.AUTO_REPLY.value,
        purchase_type=PurchaseType.MONTHLY.value,
        price=980,
        features=["テンプレート返信", "AI返信", "スパムフィルター"],
    ),
    Addon(
        addon_id="addon_analytics",
        name="高度な分析",
        description="SNSエンゲージメント分析・最適投稿時間提案",
        addon_type=AddonType.ANALYTICS.value,
        purchase_type=PurchaseType.MONTHLY.value,
        price=1480,
        features=["エンゲージメント分析", "最適投稿時間", "A/Bテスト"],
    ),
]


class AddonService:
    """アドオン課金サービス"""

    def __init__(self):
        self.catalog: Dict[str, Addon] = {a.addon_id: a for a in ADDON_CATALOG}
        self.user_addons: Dict[str, List[UserAddon]] = {}

    # ============================================================
    # カタログ管理
    # ============================================================

    def get_catalog(self, addon_type: Optional[str] = None) -> List[Addon]:
        """アドオンカタログを取得"""
        addons = [a for a in self.catalog.values() if a.is_active]
        if addon_type:
            addons = [a for a in addons if a.addon_type == addon_type]
        return addons

    def get_addon(self, addon_id: str) -> Optional[Addon]:
        """アドオン詳細を取得"""
        return self.catalog.get(addon_id)

    # ============================================================
    # 購入管理
    # ============================================================

    def purchase_addon(self, user_id: str, addon_id: str) -> Dict:
        """アドオンを購入"""
        addon = self.catalog.get(addon_id)
        if not addon:
            return {"status": "error", "message": "アドオンが見つかりません"}

        if not addon.is_active:
            return {"status": "error", "message": "このアドオンは現在販売していません"}

        # 重複チェック
        user_addons = self.user_addons.get(user_id, [])
        for ua in user_addons:
            if ua.addon_id == addon_id and ua.is_active:
                return {"status": "error", "message": "既に購入済みです"}

        # 購入処理
        now = datetime.now()
        user_addon = UserAddon(
            user_id=user_id,
            addon_id=addon_id,
            purchased_at=now.isoformat(),
            is_active=True,
        )

        if addon.purchase_type == PurchaseType.MONTHLY.value:
            from dateutil.relativedelta import relativedelta
            try:
                user_addon.expires_at = (now + relativedelta(months=1)).isoformat()
            except ImportError:
                from datetime import timedelta
                user_addon.expires_at = (now + timedelta(days=30)).isoformat()

        self.user_addons.setdefault(user_id, []).append(user_addon)

        return {
            "status": "success",
            "message": f"{addon.name}を購入しました",
            "addon": addon.name,
            "price": addon.price,
            "purchase_type": addon.purchase_type,
        }

    def cancel_addon(self, user_id: str, addon_id: str) -> Dict:
        """アドオンを解約"""
        user_addons = self.user_addons.get(user_id, [])
        for ua in user_addons:
            if ua.addon_id == addon_id and ua.is_active:
                addon = self.catalog.get(addon_id)
                if addon and addon.purchase_type == PurchaseType.ONE_TIME.value:
                    return {"status": "error", "message": "買い切りアドオンは解約できません"}

                ua.is_active = False
                return {"status": "success", "message": "アドオンを解約しました"}

        return {"status": "error", "message": "購入済みのアドオンが見つかりません"}

    # ============================================================
    # ユーザーのアドオン確認
    # ============================================================

    def get_user_addons(self, user_id: str, active_only: bool = True) -> List[Dict]:
        """ユーザーの購入済みアドオンを取得"""
        user_addons = self.user_addons.get(user_id, [])
        if active_only:
            user_addons = [ua for ua in user_addons if ua.is_active]

        result = []
        for ua in user_addons:
            addon = self.catalog.get(ua.addon_id)
            if addon:
                result.append({
                    "addon_id": ua.addon_id,
                    "name": addon.name,
                    "price": addon.price,
                    "purchase_type": addon.purchase_type,
                    "purchased_at": ua.purchased_at,
                    "expires_at": ua.expires_at,
                    "is_active": ua.is_active,
                })
        return result

    def has_addon(self, user_id: str, addon_type: str) -> bool:
        """ユーザーが特定タイプのアドオンを持っているか"""
        user_addons = self.user_addons.get(user_id, [])
        for ua in user_addons:
            if ua.is_active:
                addon = self.catalog.get(ua.addon_id)
                if addon and addon.addon_type == addon_type:
                    return True
        return False

    def get_additional_sns_slots(self, user_id: str) -> int:
        """追加SNS枠数を取得"""
        count = 0
        user_addons = self.user_addons.get(user_id, [])
        for ua in user_addons:
            if ua.is_active and ua.addon_id == "addon_sns_slot":
                count += 1
        return count

    # ============================================================
    # 月額費用計算
    # ============================================================

    def calculate_monthly_cost(self, user_id: str, base_plan_price: int = 0) -> Dict:
        """月額費用を計算"""
        user_addons = self.get_user_addons(user_id)
        monthly_addons = [a for a in user_addons if a["purchase_type"] == PurchaseType.MONTHLY.value]
        addon_total = sum(a["price"] for a in monthly_addons)

        return {
            "base_plan": base_plan_price,
            "addon_total": addon_total,
            "total": base_plan_price + addon_total,
            "addons": monthly_addons,
        }


# テスト用
if __name__ == "__main__":
    service = AddonService()

    print("=== アドオンカタログ ===")
    for addon in service.get_catalog():
        purchase = "買い切り" if addon.purchase_type == "one_time" else "月額"
        print(f"  {addon.name}: {addon.price:,}円 ({purchase})")

    print(f"\n=== テンプレートアドオン ===")
    for addon in service.get_catalog(AddonType.TEMPLATE.value):
        print(f"  {addon.name}: {addon.price:,}円")

    print(f"\n=== 購入テスト ===")
    print(service.purchase_addon("user1", "addon_template_gold"))
    print(service.purchase_addon("user1", "addon_ai_text"))
    print(service.purchase_addon("user1", "addon_sns_slot"))
    print(service.purchase_addon("user1", "addon_sns_slot"))  # 2枠目
    print(service.purchase_addon("user1", "addon_template_gold"))  # 重複

    print(f"\n=== ユーザーのアドオン ===")
    for addon in service.get_user_addons("user1"):
        print(f"  {addon['name']}: {addon['price']:,}円")

    print(f"\n=== 追加SNS枠: {service.get_additional_sns_slots('user1')}枠 ===")
    print(f"AI投稿文アドオン: {service.has_addon('user1', AddonType.AI_TEXT.value)}")

    print(f"\n=== 月額費用 ===")
    cost = service.calculate_monthly_cost("user1", base_plan_price=2980)
    print(f"  基本プラン: {cost['base_plan']:,}円")
    print(f"  アドオン合計: {cost['addon_total']:,}円")
    print(f"  合計: {cost['total']:,}円")

    print("\n✓ アドオン課金サービス テスト完了")
