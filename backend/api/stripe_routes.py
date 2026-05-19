"""
Stripe決済APIルート
====================
Stripe Checkout Session作成、Webhook処理、
サブスクリプション管理のエンドポイントを提供します。
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.models.database import User, PlanType, get_db
from backend.middleware.auth import get_current_user_by_jwt
from backend.services.stripe_service import StripeService
from backend.services.email_service import EmailService

logger = logging.getLogger(__name__)
_email_service = EmailService()

router = APIRouter(prefix="/api/stripe", tags=["stripe"])

# Stripe設定
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:8080")


def get_stripe_service() -> StripeService:
    """Stripeサービスを取得します。"""
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stripe APIキーが設定されていません"
        )
    return StripeService(STRIPE_SECRET_KEY)


# ============================================================
# スキーマ
# ============================================================

class CheckoutRequest(BaseModel):
    plan_id: str  # "light", "standard", "premium"

class ChangePlanRequest(BaseModel):
    new_plan_id: str


# ============================================================
# エンドポイント
# ============================================================

@router.post("/checkout")
async def create_checkout(
    data: CheckoutRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db),
    stripe: StripeService = Depends(get_stripe_service)
):
    """Stripe Checkout Sessionを作成"""
    # Stripeカスタマーの確認/作成
    if not user.stripe_customer_id:
        customer_id = stripe.create_customer(user.email, user.name)
        user.stripe_customer_id = customer_id
        db.commit()
    else:
        customer_id = user.stripe_customer_id

    # Checkout Session作成
    result = stripe.create_checkout_session(
        customer_id=customer_id,
        plan_id=data.plan_id,
        success_url=f"{DASHBOARD_URL}?stripe=success",
        cancel_url=f"{DASHBOARD_URL}?stripe=cancel",
    )

    return result


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Stripe Webhookイベントを処理"""
    if not STRIPE_SECRET_KEY or not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Stripe未設定")

    stripe = StripeService(STRIPE_SECRET_KEY)

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        result = stripe.handle_webhook(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not result["handled"]:
        return {"status": "ignored"}

    event_type = result["event_type"]

    # checkout.session.completed: 新規サブスクリプション開始
    if event_type == "checkout.session.completed":
        customer_id = result.get("customer_id")
        subscription_id = result.get("subscription_id")
        plan_id = result.get("plan_id")

        if customer_id and plan_id:
            user = db.query(User).filter(
                User.stripe_customer_id == customer_id
            ).first()

            if user:
                plan_map = {
                    "light": PlanType.LIGHT,
                    "standard": PlanType.STANDARD,
                    "premium": PlanType.PREMIUM,
                }
                user.plan = plan_map.get(plan_id, PlanType.LIGHT)
                user.stripe_subscription_id = subscription_id
                db.commit()
                logger.info(f"ユーザー {user.id} のプランを {plan_id} に更新")

                # 管理者へサブスク通知
                try:
                    plan_names = {"light": "ライト", "standard": "スタンダード", "premium": "プレミアム"}
                    _email_service.send_admin_new_subscription({
                        "name": user.name,
                        "email": user.email,
                        "plan_name": plan_names.get(plan_id, plan_id),
                        "subscription_id": subscription_id or "",
                    })
                except Exception as e:
                    logger.warning(f"サブスク管理者通知失敗: {e}")

    # customer.subscription.deleted: サブスクリプションキャンセル
    elif event_type == "customer.subscription.deleted":
        subscription_id = result.get("subscription_id")
        if subscription_id:
            user = db.query(User).filter(
                User.stripe_subscription_id == subscription_id
            ).first()
            if user:
                user.plan = PlanType.FREE
                user.stripe_subscription_id = None
                db.commit()
                logger.info(f"ユーザー {user.id} のサブスクリプションをキャンセル")

    return {"status": "ok"}


@router.post("/cancel")
async def cancel_subscription(
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db),
    stripe: StripeService = Depends(get_stripe_service)
):
    """サブスクリプションをキャンセル（期間終了時）"""
    if not user.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="アクティブなサブスクリプションがありません"
        )

    result = stripe.cancel_subscription(
        user.stripe_subscription_id,
        at_period_end=True
    )

    return {
        "message": "サブスクリプションは期間終了時にキャンセルされます",
        **result
    }


@router.post("/change-plan")
async def change_plan(
    data: ChangePlanRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db),
    stripe: StripeService = Depends(get_stripe_service)
):
    """プランを変更"""
    if not user.stripe_subscription_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="アクティブなサブスクリプションがありません。先にプランを購入してください。"
        )

    result = stripe.change_plan(
        user.stripe_subscription_id,
        data.new_plan_id
    )

    # DBのプランも更新
    plan_map = {
        "light": PlanType.LIGHT,
        "standard": PlanType.STANDARD,
        "premium": PlanType.PREMIUM,
    }
    user.plan = plan_map.get(data.new_plan_id, user.plan)
    db.commit()

    return {
        "message": f"プランを{data.new_plan_id}に変更しました",
        **result
    }
