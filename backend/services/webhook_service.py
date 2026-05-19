"""
TradePost Pro - Webhook通知サービス
投稿完了時などに外部サービス（Zapier/Make等）へ通知を送信
"""

import hashlib
import hmac
import json
import time
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Any
from enum import Enum

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class WebhookEvent(str, Enum):
    """Webhookイベント種別"""
    POST_COMPLETED = "post.completed"
    POST_FAILED = "post.failed"
    TRADE_RECEIVED = "trade.received"
    SCHEDULE_EXECUTED = "schedule.executed"
    PLAN_CHANGED = "plan.changed"
    TRIAL_STARTED = "trial.started"
    TRIAL_ENDING = "trial.ending"
    PAYMENT_SUCCESS = "payment.success"
    PAYMENT_FAILED = "payment.failed"


@dataclass
class WebhookEndpoint:
    """Webhookエンドポイント設定"""
    webhook_id: str = ""
    user_id: str = ""
    url: str = ""
    secret: str = ""
    events: List[str] = field(default_factory=list)
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    # 統計
    total_sent: int = 0
    total_failed: int = 0
    last_sent_at: Optional[str] = None
    last_status_code: Optional[int] = None
    # リトライ設定
    max_retries: int = 3
    retry_delay: int = 60  # 秒


@dataclass
class WebhookDelivery:
    """Webhook配信記録"""
    delivery_id: str = ""
    webhook_id: str = ""
    event: str = ""
    payload: Dict = field(default_factory=dict)
    status_code: Optional[int] = None
    response_body: str = ""
    success: bool = False
    attempt: int = 1
    created_at: str = ""
    duration_ms: Optional[int] = None


class WebhookService:
    """Webhook管理・配信サービス"""

    def __init__(self):
        self.endpoints: Dict[str, WebhookEndpoint] = {}
        self.deliveries: List[WebhookDelivery] = []
        self.user_endpoints: Dict[str, List[str]] = {}  # user_id -> [webhook_id]

    def register_endpoint(
        self,
        user_id: str,
        url: str,
        events: List[str],
        secret: Optional[str] = None
    ) -> WebhookEndpoint:
        """Webhookエンドポイントを登録"""
        webhook_id = hashlib.md5(
            f"{user_id}:{url}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        if not secret:
            secret = hashlib.sha256(
                f"{webhook_id}:{time.time()}".encode()
            ).hexdigest()

        endpoint = WebhookEndpoint(
            webhook_id=webhook_id,
            user_id=user_id,
            url=url,
            secret=secret,
            events=events,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        self.endpoints[webhook_id] = endpoint

        if user_id not in self.user_endpoints:
            self.user_endpoints[user_id] = []
        self.user_endpoints[user_id].append(webhook_id)

        logger.info(f"Webhook登録: {webhook_id} -> {url} (events: {events})")
        return endpoint

    def update_endpoint(
        self,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[WebhookEndpoint]:
        """エンドポイント更新"""
        endpoint = self.endpoints.get(webhook_id)
        if not endpoint:
            return None

        if url is not None:
            endpoint.url = url
        if events is not None:
            endpoint.events = events
        if is_active is not None:
            endpoint.is_active = is_active

        endpoint.updated_at = datetime.now().isoformat()
        return endpoint

    def delete_endpoint(self, webhook_id: str) -> bool:
        """エンドポイント削除"""
        endpoint = self.endpoints.get(webhook_id)
        if not endpoint:
            return False

        if endpoint.user_id in self.user_endpoints:
            self.user_endpoints[endpoint.user_id] = [
                wid for wid in self.user_endpoints[endpoint.user_id]
                if wid != webhook_id
            ]

        del self.endpoints[webhook_id]
        return True

    def get_user_endpoints(self, user_id: str) -> List[WebhookEndpoint]:
        """ユーザーのWebhook一覧取得"""
        webhook_ids = self.user_endpoints.get(user_id, [])
        return [self.endpoints[wid] for wid in webhook_ids if wid in self.endpoints]

    def _generate_signature(self, payload: str, secret: str) -> str:
        """HMAC-SHA256署名を生成"""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    def _build_payload(self, event: str, data: Dict) -> Dict:
        """Webhookペイロードを構築"""
        return {
            "event": event,
            "data": data,
            "timestamp": datetime.now().isoformat(),
            "api_version": "1.0.0",
        }

    def dispatch(self, user_id: str, event: str, data: Dict) -> List[WebhookDelivery]:
        """イベントを該当するWebhookに配信"""
        deliveries = []
        webhook_ids = self.user_endpoints.get(user_id, [])

        for webhook_id in webhook_ids:
            endpoint = self.endpoints.get(webhook_id)
            if not endpoint or not endpoint.is_active:
                continue

            if event not in endpoint.events and "*" not in endpoint.events:
                continue

            delivery = self._send_webhook(endpoint, event, data)
            deliveries.append(delivery)

        return deliveries

    def _send_webhook(
        self,
        endpoint: WebhookEndpoint,
        event: str,
        data: Dict,
        attempt: int = 1
    ) -> WebhookDelivery:
        """Webhook送信"""
        payload = self._build_payload(event, data)
        payload_json = json.dumps(payload, ensure_ascii=False)
        signature = self._generate_signature(payload_json, endpoint.secret)

        delivery_id = hashlib.md5(
            f"{endpoint.webhook_id}:{event}:{time.time()}".encode()
        ).hexdigest()[:16]

        delivery = WebhookDelivery(
            delivery_id=delivery_id,
            webhook_id=endpoint.webhook_id,
            event=event,
            payload=payload,
            attempt=attempt,
            created_at=datetime.now().isoformat(),
        )

        headers = {
            "Content-Type": "application/json",
            "X-TradePost-Signature": f"sha256={signature}",
            "X-TradePost-Event": event,
            "X-TradePost-Delivery": delivery_id,
            "User-Agent": "TradePost-Webhook/1.0",
        }

        try:
            if requests is None:
                logger.warning("requestsライブラリが未インストールです")
                delivery.success = False
                delivery.response_body = "requests library not available"
                return delivery

            start_time = time.time()
            response = requests.post(
                endpoint.url,
                data=payload_json,
                headers=headers,
                timeout=30,
            )
            duration = int((time.time() - start_time) * 1000)

            delivery.status_code = response.status_code
            delivery.response_body = response.text[:1000]
            delivery.duration_ms = duration
            delivery.success = 200 <= response.status_code < 300

            endpoint.total_sent += 1
            endpoint.last_sent_at = datetime.now().isoformat()
            endpoint.last_status_code = response.status_code

            if not delivery.success:
                endpoint.total_failed += 1
                logger.warning(
                    f"Webhook配信失敗: {endpoint.url} "
                    f"status={response.status_code} "
                    f"attempt={attempt}/{endpoint.max_retries}"
                )

        except requests.exceptions.Timeout:
            delivery.success = False
            delivery.response_body = "Timeout"
            endpoint.total_failed += 1
            logger.error(f"Webhook タイムアウト: {endpoint.url}")

        except requests.exceptions.ConnectionError:
            delivery.success = False
            delivery.response_body = "Connection Error"
            endpoint.total_failed += 1
            logger.error(f"Webhook 接続エラー: {endpoint.url}")

        except Exception as e:
            delivery.success = False
            delivery.response_body = str(e)
            endpoint.total_failed += 1
            logger.error(f"Webhook エラー: {endpoint.url} - {e}")

        self.deliveries.append(delivery)
        return delivery

    def get_delivery_history(
        self,
        webhook_id: str,
        limit: int = 50
    ) -> List[WebhookDelivery]:
        """配信履歴を取得"""
        history = [d for d in self.deliveries if d.webhook_id == webhook_id]
        return sorted(history, key=lambda d: d.created_at, reverse=True)[:limit]

    def test_endpoint(self, webhook_id: str) -> WebhookDelivery:
        """テスト配信"""
        endpoint = self.endpoints.get(webhook_id)
        if not endpoint:
            return WebhookDelivery(success=False, response_body="Endpoint not found")

        test_data = {
            "message": "これはテスト配信です",
            "webhook_id": webhook_id,
            "timestamp": datetime.now().isoformat(),
        }

        return self._send_webhook(endpoint, "test.ping", test_data)

    # ============================================================
    # Zapier/Make用のヘルパー
    # ============================================================

    @staticmethod
    def get_zapier_sample_payload(event: str) -> Dict:
        """Zapier用のサンプルペイロード"""
        samples = {
            WebhookEvent.POST_COMPLETED: {
                "event": "post.completed",
                "data": {
                    "post_id": "abc123",
                    "platform": "x",
                    "date": "2026-03-11",
                    "profit": 17000,
                    "win_rate": 66.7,
                    "image_url": "https://example.com/image.jpg",
                    "post_url": "https://x.com/user/status/123",
                },
            },
            WebhookEvent.POST_FAILED: {
                "event": "post.failed",
                "data": {
                    "post_id": "abc123",
                    "platform": "instagram",
                    "error": "API rate limit exceeded",
                    "retry_at": "2026-03-11T07:05:00",
                },
            },
            WebhookEvent.TRADE_RECEIVED: {
                "event": "trade.received",
                "data": {
                    "trade_id": "def456",
                    "date": "2026-03-11",
                    "profit": 17000,
                    "total_trades": 12,
                    "wins": 8,
                    "losses": 4,
                    "win_rate": 66.7,
                    "cumulative_profit": 250000,
                },
            },
            WebhookEvent.PLAN_CHANGED: {
                "event": "plan.changed",
                "data": {
                    "previous_plan": "light",
                    "new_plan": "standard",
                    "effective_date": "2026-03-11",
                },
            },
        }
        return samples.get(event, {"event": event, "data": {}})


# テスト用
if __name__ == "__main__":
    service = WebhookService()

    # エンドポイント登録
    ep = service.register_endpoint(
        user_id="user_001",
        url="https://hooks.zapier.com/hooks/catch/123/abc/",
        events=[WebhookEvent.POST_COMPLETED, WebhookEvent.TRADE_RECEIVED],
    )
    print(f"Webhook登録: {ep.webhook_id}")
    print(f"Secret: {ep.secret[:16]}...")

    # ユーザーのWebhook一覧
    endpoints = service.get_user_endpoints("user_001")
    print(f"登録数: {len(endpoints)}")

    # サンプルペイロード
    sample = WebhookService.get_zapier_sample_payload(WebhookEvent.POST_COMPLETED)
    print(f"\nZapierサンプル: {json.dumps(sample, indent=2, ensure_ascii=False)}")

    # 署名テスト
    sig = service._generate_signature('{"test": true}', ep.secret)
    print(f"\n署名テスト: sha256={sig[:32]}...")

    print("\n✓ Webhookサービス テスト完了")
