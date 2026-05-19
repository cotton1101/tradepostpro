"""
Stripe決済サービス
==================
Stripe Checkout Sessionを使用したサブスクリプション決済を管理します。

料金プラン:
  - ライト:     1,980円/月 (price_light)
  - スタンダード: 2,980円/月 (price_standard)
  - プレミアム:   4,980円/月 (price_premium)

【前提条件】
  - pip install stripe
  - Stripeアカウントで以下を作成済み:
    1. 3つのProduct（ライト/スタンダード/プレミアム）
    2. 各Productに対応するPrice（月額サブスクリプション）
    3. Webhook Endpoint（checkout.session.completed等）
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

# Stripe Price ID（Stripeダッシュボードで作成後に設定）
STRIPE_PRICE_IDS = {
    "light": os.getenv("STRIPE_PRICE_LIGHT", "price_light_placeholder"),
    "standard": os.getenv("STRIPE_PRICE_STANDARD", "price_standard_placeholder"),
    "premium": os.getenv("STRIPE_PRICE_PREMIUM", "price_premium_placeholder"),
}


class StripeService:
    """Stripe決済サービスクラス"""

    def __init__(self, secret_key: str):
        """
        Args:
            secret_key: Stripe Secret Key (sk_test_xxx or sk_live_xxx)
        """
        try:
            import stripe
            self.stripe = stripe
            self.stripe.api_key = secret_key
            logger.info("Stripe初期化完了")
        except ImportError:
            raise ImportError("stripeパッケージが必要です: pip install stripe")

    def create_customer(self, email: str, name: str) -> str:
        """
        Stripeカスタマーを作成します。
        
        Args:
            email: ユーザーのメールアドレス
            name: ユーザー名
        
        Returns:
            str: Stripe Customer ID
        """
        customer = self.stripe.Customer.create(
            email=email,
            name=name,
            metadata={"source": "xm_sns_auto_poster"}
        )
        logger.info(f"Stripeカスタマー作成: {customer.id}")
        return customer.id

    def create_checkout_session(
        self,
        customer_id: str,
        plan_id: str,
        success_url: str,
        cancel_url: str
    ) -> dict:
        """
        Stripe Checkout Sessionを作成します。
        
        Args:
            customer_id: Stripe Customer ID
            plan_id: プランID ("light", "standard", "premium")
            success_url: 決済成功時のリダイレクトURL
            cancel_url: 決済キャンセル時のリダイレクトURL
        
        Returns:
            dict: Checkout Session情報
        """
        price_id = STRIPE_PRICE_IDS.get(plan_id)
        if not price_id:
            raise ValueError(f"無効なプランID: {plan_id}")

        session = self.stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": price_id,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url,
            metadata={
                "plan_id": plan_id,
            },
            locale="ja",
            allow_promotion_codes=True,
        )

        logger.info(f"Checkout Session作成: {session.id}, plan={plan_id}")

        return {
            "session_id": session.id,
            "url": session.url,
        }

    def get_subscription(self, subscription_id: str) -> dict:
        """
        サブスクリプション情報を取得します。
        
        Args:
            subscription_id: Stripe Subscription ID
        
        Returns:
            dict: サブスクリプション情報
        """
        subscription = self.stripe.Subscription.retrieve(subscription_id)

        return {
            "id": subscription.id,
            "status": subscription.status,
            "current_period_end": subscription.current_period_end,
            "cancel_at_period_end": subscription.cancel_at_period_end,
            "plan_id": subscription.metadata.get("plan_id"),
        }

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True) -> dict:
        """
        サブスクリプションをキャンセルします。
        
        Args:
            subscription_id: Stripe Subscription ID
            at_period_end: 期間終了時にキャンセルするか（デフォルト: True）
        
        Returns:
            dict: キャンセル結果
        """
        if at_period_end:
            subscription = self.stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
        else:
            subscription = self.stripe.Subscription.cancel(subscription_id)

        logger.info(f"サブスクリプションキャンセル: {subscription_id}")

        return {
            "id": subscription.id,
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }

    def change_plan(self, subscription_id: str, new_plan_id: str) -> dict:
        """
        プランを変更します（アップグレード/ダウングレード）。
        
        Args:
            subscription_id: Stripe Subscription ID
            new_plan_id: 新しいプランID
        
        Returns:
            dict: 変更結果
        """
        new_price_id = STRIPE_PRICE_IDS.get(new_plan_id)
        if not new_price_id:
            raise ValueError(f"無効なプランID: {new_plan_id}")

        subscription = self.stripe.Subscription.retrieve(subscription_id)

        updated = self.stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": subscription["items"]["data"][0].id,
                "price": new_price_id,
            }],
            proration_behavior="create_prorations",
            metadata={"plan_id": new_plan_id},
        )

        logger.info(f"プラン変更: {subscription_id} → {new_plan_id}")

        return {
            "id": updated.id,
            "status": updated.status,
            "plan_id": new_plan_id,
        }

    def handle_webhook(self, payload: bytes, sig_header: str, webhook_secret: str) -> dict:
        """
        Stripe Webhookイベントを処理します。
        
        Args:
            payload: リクエストボディ
            sig_header: Stripe-Signatureヘッダー
            webhook_secret: Webhook Secret
        
        Returns:
            dict: 処理結果
        """
        try:
            event = self.stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
        except ValueError:
            raise ValueError("無効なペイロード")
        except self.stripe.error.SignatureVerificationError:
            raise ValueError("無効な署名")

        event_type = event["type"]
        data = event["data"]["object"]

        logger.info(f"Webhookイベント受信: {event_type}")

        result = {
            "event_type": event_type,
            "handled": False,
        }

        if event_type == "checkout.session.completed":
            result["customer_id"] = data.get("customer")
            result["subscription_id"] = data.get("subscription")
            result["plan_id"] = data.get("metadata", {}).get("plan_id")
            result["handled"] = True

        elif event_type == "customer.subscription.updated":
            result["subscription_id"] = data.get("id")
            result["status"] = data.get("status")
            result["handled"] = True

        elif event_type == "customer.subscription.deleted":
            result["subscription_id"] = data.get("id")
            result["status"] = "canceled"
            result["handled"] = True

        elif event_type == "invoice.payment_failed":
            result["customer_id"] = data.get("customer")
            result["subscription_id"] = data.get("subscription")
            result["handled"] = True

        return result
