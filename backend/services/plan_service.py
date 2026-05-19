"""
プラン制御サービス
==================
サブスクリプションプランに基づくアクセス制御を管理します。

料金プラン:
  - 無料:       0円 - 登録直後のデフォルト, SNS連携不可, ダッシュボード閲覧のみ
  - ライト:     1,980円/月 - SNS 2つまで, 基本テンプレート3種, 動画非対応
  - スタンダード: 2,980円/月 - SNS 4つまで, 全テンプレート, 動画非対応
  - プレミアム:   4,980円/月 - SNS 5つ全て, 全テンプレート+カスタム, 動画対応
"""

from dataclasses import dataclass
from typing import List

from backend.models.database import PlanType


@dataclass
class PlanConfig:
    """プラン設定"""
    name: str
    price: int                    # 月額（円）
    max_sns_count: int            # 対応SNS数
    template_access: str          # テンプレートアクセスレベル
    video_generation: bool        # 動画生成対応
    custom_template: bool         # カスタムテンプレート対応
    stripe_price_id: str = ""     # Stripe Price ID


# プラン定義
PLAN_CONFIGS = {
    PlanType.FREE: PlanConfig(
        name="無料",
        price=0,
        max_sns_count=0,
        template_access="basic",
        video_generation=False,
        custom_template=False,
    ),
    PlanType.LIGHT: PlanConfig(
        name="ライト",
        price=1980,
        max_sns_count=2,
        template_access="basic",
        video_generation=False,
        custom_template=False,
    ),
    PlanType.STANDARD: PlanConfig(
        name="スタンダード",
        price=2980,
        max_sns_count=4,
        template_access="all",
        video_generation=False,
        custom_template=False,
    ),
    PlanType.PREMIUM: PlanConfig(
        name="プレミアム",
        price=4980,
        max_sns_count=5,
        template_access="all",
        video_generation=True,
        custom_template=True,
    ),
}


class PlanService:
    """プラン制御サービスクラス"""

    @staticmethod
    def get_plan_config(plan: PlanType) -> PlanConfig:
        """プラン設定を取得します。"""
        return PLAN_CONFIGS.get(plan, PLAN_CONFIGS[PlanType.LIGHT])

    @staticmethod
    def can_use_platform(plan: PlanType, enabled_count: int) -> bool:
        """
        新しいSNSプラットフォームを追加できるか判定します。
        
        Args:
            plan: ユーザーのプラン
            enabled_count: 現在有効なSNS数
        
        Returns:
            bool: 追加可能ならTrue
        """
        config = PLAN_CONFIGS[plan]
        return enabled_count < config.max_sns_count

    @staticmethod
    def can_use_template(plan: PlanType, template_type: str) -> bool:
        """
        テンプレートを使用できるか判定します。
        
        Args:
            plan: ユーザーのプラン
            template_type: テンプレートの種類 ("basic", "premium", "custom")
        
        Returns:
            bool: 使用可能ならTrue
        """
        config = PLAN_CONFIGS[plan]

        if template_type == "basic":
            return True
        elif template_type == "premium":
            return config.template_access == "all"
        elif template_type == "custom":
            return config.custom_template
        return False

    @staticmethod
    def can_generate_video(plan: PlanType) -> bool:
        """動画生成が利用可能か判定します。"""
        config = PLAN_CONFIGS[plan]
        return config.video_generation

    @staticmethod
    def get_available_platforms(plan: PlanType) -> int:
        """利用可能なSNS数を返します。"""
        return PLAN_CONFIGS[plan].max_sns_count

    @staticmethod
    def get_all_plans() -> List[dict]:
        """全プラン情報をリストで返します。"""
        return [
            {
                "plan_id": plan.value,
                "name": config.name,
                "price": config.price,
                "max_sns_count": config.max_sns_count,
                "template_access": config.template_access,
                "video_generation": config.video_generation,
                "custom_template": config.custom_template,
            }
            for plan, config in PLAN_CONFIGS.items()
        ]
