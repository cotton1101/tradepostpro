"""
プラン制御ミドルウェア
======================
投稿実行時にユーザーのプランに基づいた制限を適用します。

制限内容:
  - SNS数の制限（ライト: 2, スタンダード: 4, プレミアム: 5）
  - テンプレートの制限（ライト: basic3種のみ, スタンダード: 全種, プレミアム: 全種+カスタム）
  - 動画生成の制限（プレミアムのみ）
  - 1日あたりの投稿回数制限
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from backend.models.database import (
    User, SNSAccount, PostHistory, PostTemplate,
    PlanType, PlatformType, PostStatus
)
from backend.services.plan_service import PlanService

logger = logging.getLogger(__name__)


# 1日あたりの最大投稿回数（プラン別）
DAILY_POST_LIMITS = {
    PlanType.FREE: 1,
    PlanType.LIGHT: 5,
    PlanType.STANDARD: 15,
    PlanType.PREMIUM: 50,
}


class PlanGuard:
    """プラン制御ガードクラス"""

    @staticmethod
    def validate_post_request(
        user: User,
        db: Session,
        platforms: Optional[List[str]] = None,
        template_id: Optional[int] = None,
        generate_video: bool = False
    ) -> dict:
        """
        投稿リクエストをプランに基づいて検証します。
        
        Args:
            user: リクエストユーザー
            db: データベースセッション
            platforms: 投稿先プラットフォーム一覧
            template_id: テンプレートID
            generate_video: 動画生成フラグ
        
        Returns:
            dict: {"valid": bool, "errors": list, "warnings": list, "allowed_platforms": list}
        """
        errors = []
        warnings = []
        plan_config = PlanService.get_plan_config(user.plan)

        # 1. 動画生成チェック
        if generate_video and not plan_config.video_generation:
            errors.append(
                f"動画生成はプレミアムプランでのみ利用可能です。"
                f"現在のプラン: {plan_config.name}"
            )

        # 2. SNSアカウントの取得と制限チェック
        sns_query = db.query(SNSAccount).filter(
            SNSAccount.user_id == user.id,
            SNSAccount.is_enabled == True
        )
        all_accounts = sns_query.all()

        if platforms:
            target_accounts = [
                acc for acc in all_accounts
                if acc.platform.value in platforms
            ]
        else:
            target_accounts = all_accounts

        # プラン上限を超えるアカウントを除外
        allowed_accounts = target_accounts[:plan_config.max_sns_count]
        excluded_accounts = target_accounts[plan_config.max_sns_count:]

        if excluded_accounts:
            excluded_names = [acc.platform.value for acc in excluded_accounts]
            warnings.append(
                f"{plan_config.name}プランでは{plan_config.max_sns_count}つまでのSNSが利用可能です。"
                f"以下のSNSは除外されます: {', '.join(excluded_names)}"
            )

        # 3. テンプレートチェック
        if template_id:
            template = db.query(PostTemplate).filter(
                PostTemplate.id == template_id,
                PostTemplate.is_active == True
            ).first()

            if template:
                if not PlanService.can_use_template(user.plan, template.template_type):
                    errors.append(
                        f"テンプレート「{template.name}」は{plan_config.name}プランでは利用できません。"
                    )
            else:
                errors.append("指定されたテンプレートが見つかりません。")

        # 4. 日次投稿回数チェック
        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_post_count = db.query(PostHistory).filter(
            PostHistory.user_id == user.id,
            PostHistory.date == today,
            PostHistory.status != PostStatus.SKIPPED
        ).count()

        daily_limit = DAILY_POST_LIMITS.get(user.plan, 5)
        remaining = daily_limit - today_post_count

        if remaining <= 0:
            errors.append(
                f"本日の投稿回数上限（{daily_limit}回）に達しました。"
            )
        elif remaining < len(allowed_accounts):
            warnings.append(
                f"本日の残り投稿回数: {remaining}回（上限: {daily_limit}回）。"
                f"一部のSNSへの投稿がスキップされる可能性があります。"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "allowed_platforms": [acc.platform.value for acc in allowed_accounts],
            "plan": plan_config.name,
            "daily_remaining": max(0, remaining),
        }

    @staticmethod
    def get_user_limits(user: User, db: Session) -> dict:
        """
        ユーザーの現在の利用状況と制限を返します。
        
        Args:
            user: ユーザー
            db: データベースセッション
        
        Returns:
            dict: 利用状況と制限情報
        """
        plan_config = PlanService.get_plan_config(user.plan)

        # 有効SNS数
        active_sns = db.query(SNSAccount).filter(
            SNSAccount.user_id == user.id,
            SNSAccount.is_enabled == True
        ).count()

        # 本日の投稿数
        today = datetime.utcnow().strftime("%Y-%m-%d")
        today_posts = db.query(PostHistory).filter(
            PostHistory.user_id == user.id,
            PostHistory.date == today,
            PostHistory.status != PostStatus.SKIPPED
        ).count()

        daily_limit = DAILY_POST_LIMITS.get(user.plan, 5)

        return {
            "plan": {
                "id": user.plan.value,
                "name": plan_config.name,
                "price": plan_config.price,
            },
            "sns": {
                "active": active_sns,
                "max": plan_config.max_sns_count,
                "remaining": max(0, plan_config.max_sns_count - active_sns),
            },
            "posts": {
                "today": today_posts,
                "daily_limit": daily_limit,
                "remaining": max(0, daily_limit - today_posts),
            },
            "features": {
                "video_generation": plan_config.video_generation,
                "custom_template": plan_config.custom_template,
                "template_access": plan_config.template_access,
            },
        }
