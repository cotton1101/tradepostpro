"""
PWAプッシュ通知サービス
Web Push APIを使用したプッシュ通知管理
"""

import json
import hashlib
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class NotificationType(Enum):
    """通知タイプ"""
    POST_SUCCESS = "post_success"
    POST_FAILED = "post_failed"
    TRADE_RESULT = "trade_result"
    DAILY_SUMMARY = "daily_summary"
    WEEKLY_REPORT = "weekly_report"
    BADGE_EARNED = "badge_earned"
    LEVEL_UP = "level_up"
    SYSTEM_ALERT = "system_alert"
    MAINTENANCE = "maintenance"
    PROMOTION = "promotion"


class NotificationPriority(Enum):
    """通知優先度"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class PushSubscription:
    """プッシュ通知サブスクリプション"""
    user_id: str
    endpoint: str
    p256dh_key: str
    auth_key: str
    user_agent: str = ""
    created_at: str = ""
    is_active: bool = True

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class NotificationPayload:
    """通知ペイロード"""
    title: str
    body: str
    icon: str = "/icons/icon-192x192.png"
    badge: str = "/icons/badge-72x72.png"
    image: Optional[str] = None
    tag: str = ""
    data: dict = field(default_factory=dict)
    actions: list = field(default_factory=list)
    require_interaction: bool = False
    silent: bool = False
    vibrate: list = field(default_factory=lambda: [200, 100, 200])


@dataclass
class NotificationLog:
    """通知送信ログ"""
    id: str
    user_id: str
    notification_type: NotificationType
    payload: dict
    sent_at: str
    delivered: bool = False
    clicked: bool = False


class PWAPushService:
    """PWAプッシュ通知管理サービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.vapid_public_key = self.config.get("vapid_public_key", "")
        self.vapid_private_key = self.config.get("vapid_private_key", "")
        self.vapid_email = self.config.get("vapid_email", "admin@tradepost-pro.com")

        self.subscriptions: dict = {}  # user_id -> [PushSubscription]
        self.notification_logs: list = []
        self.user_preferences: dict = {}  # user_id -> {notification_type: bool}

    def register_subscription(self, user_id: str, subscription_data: dict) -> dict:
        """プッシュ通知サブスクリプションを登録"""
        sub = PushSubscription(
            user_id=user_id,
            endpoint=subscription_data.get("endpoint", ""),
            p256dh_key=subscription_data.get("keys", {}).get("p256dh", ""),
            auth_key=subscription_data.get("keys", {}).get("auth", ""),
            user_agent=subscription_data.get("user_agent", ""),
        )

        if user_id not in self.subscriptions:
            self.subscriptions[user_id] = []

        # 重複チェック
        existing = [s for s in self.subscriptions[user_id] if s.endpoint == sub.endpoint]
        if not existing:
            self.subscriptions[user_id].append(sub)

        return {
            "success": True,
            "subscription_count": len(self.subscriptions[user_id]),
        }

    def unregister_subscription(self, user_id: str, endpoint: str) -> bool:
        """サブスクリプションを解除"""
        if user_id in self.subscriptions:
            self.subscriptions[user_id] = [
                s for s in self.subscriptions[user_id] if s.endpoint != endpoint
            ]
            return True
        return False

    def set_preferences(self, user_id: str, preferences: dict) -> dict:
        """通知設定を更新"""
        if user_id not in self.user_preferences:
            self.user_preferences[user_id] = {nt.value: True for nt in NotificationType}

        self.user_preferences[user_id].update(preferences)
        return self.user_preferences[user_id]

    def get_preferences(self, user_id: str) -> dict:
        """通知設定を取得"""
        if user_id not in self.user_preferences:
            return {nt.value: True for nt in NotificationType}
        return self.user_preferences[user_id]

    def send_notification(
        self,
        user_id: str,
        notification_type: NotificationType,
        payload: NotificationPayload,
        priority: NotificationPriority = NotificationPriority.NORMAL,
    ) -> dict:
        """プッシュ通知を送信"""
        # 設定チェック
        prefs = self.get_preferences(user_id)
        if not prefs.get(notification_type.value, True):
            return {"success": False, "reason": "notification_disabled"}

        # サブスクリプション取得
        subs = self.subscriptions.get(user_id, [])
        active_subs = [s for s in subs if s.is_active]

        if not active_subs:
            return {"success": False, "reason": "no_subscriptions"}

        # ペイロード構築
        notification_data = {
            "title": payload.title,
            "body": payload.body,
            "icon": payload.icon,
            "badge": payload.badge,
            "tag": payload.tag or notification_type.value,
            "data": {
                **payload.data,
                "notification_type": notification_type.value,
                "timestamp": datetime.now().isoformat(),
                "url": payload.data.get("url", "/dashboard"),
            },
            "actions": payload.actions,
            "requireInteraction": payload.require_interaction,
            "silent": payload.silent,
            "vibrate": payload.vibrate,
        }

        if payload.image:
            notification_data["image"] = payload.image

        # 送信ログ
        log = NotificationLog(
            id=hashlib.md5(f"{user_id}:{datetime.now().isoformat()}".encode()).hexdigest()[:12],
            user_id=user_id,
            notification_type=notification_type,
            payload=notification_data,
            sent_at=datetime.now().isoformat(),
            delivered=True,  # 実際にはWeb Push APIの結果で判定
        )
        self.notification_logs.append(log)

        return {
            "success": True,
            "notification_id": log.id,
            "recipients": len(active_subs),
            "payload": notification_data,
        }

    # ========== 通知テンプレート ==========

    def notify_post_success(self, user_id: str, platform: str, post_url: str = "") -> dict:
        """投稿成功通知"""
        payload = NotificationPayload(
            title="投稿完了",
            body=f"{platform}への自動投稿が完了しました",
            tag="post_success",
            data={"url": post_url or "/dashboard/posts"},
            actions=[
                {"action": "view", "title": "投稿を見る"},
                {"action": "dismiss", "title": "閉じる"},
            ],
        )
        return self.send_notification(user_id, NotificationType.POST_SUCCESS, payload)

    def notify_post_failed(self, user_id: str, platform: str, error: str = "") -> dict:
        """投稿失敗通知"""
        payload = NotificationPayload(
            title="投稿エラー",
            body=f"{platform}への投稿に失敗しました: {error[:50]}",
            tag="post_failed",
            require_interaction=True,
            data={"url": "/dashboard/posts"},
            actions=[
                {"action": "retry", "title": "再試行"},
                {"action": "view", "title": "詳細を見る"},
            ],
        )
        return self.send_notification(user_id, NotificationType.POST_FAILED, payload, NotificationPriority.HIGH)

    def notify_trade_result(self, user_id: str, profit: float, win_rate: float) -> dict:
        """取引結果通知"""
        emoji = "📈" if profit >= 0 else "📉"
        result = "プラス" if profit >= 0 else "マイナス"
        payload = NotificationPayload(
            title=f"{emoji} 本日の取引結果",
            body=f"{result}{abs(profit):,.0f}円 (勝率: {win_rate:.1f}%)",
            tag="trade_result",
            data={"url": "/dashboard/trades"},
        )
        return self.send_notification(user_id, NotificationType.TRADE_RESULT, payload)

    def notify_badge_earned(self, user_id: str, badge_name: str, badge_icon: str) -> dict:
        """バッジ獲得通知"""
        payload = NotificationPayload(
            title=f"{badge_icon} バッジ獲得！",
            body=f"「{badge_name}」バッジを獲得しました！",
            tag="badge_earned",
            data={"url": "/dashboard/achievements"},
            actions=[
                {"action": "view", "title": "バッジを見る"},
                {"action": "share", "title": "シェア"},
            ],
        )
        return self.send_notification(user_id, NotificationType.BADGE_EARNED, payload)

    def notify_level_up(self, user_id: str, new_level: int, title: str) -> dict:
        """レベルアップ通知"""
        payload = NotificationPayload(
            title="🎉 レベルアップ！",
            body=f"レベル{new_level}に到達しました！「{title}」",
            tag="level_up",
            data={"url": "/dashboard/profile"},
            vibrate=[200, 100, 200, 100, 200],
        )
        return self.send_notification(user_id, NotificationType.LEVEL_UP, payload)

    def notify_daily_summary(self, user_id: str, summary: dict) -> dict:
        """日次サマリー通知"""
        posts = summary.get("posts_today", 0)
        profit = summary.get("daily_profit", 0)
        payload = NotificationPayload(
            title="📊 本日のサマリー",
            body=f"投稿: {posts}件 | 損益: {profit:+,.0f}円",
            tag="daily_summary",
            data={"url": "/dashboard"},
        )
        return self.send_notification(user_id, NotificationType.DAILY_SUMMARY, payload)

    # ========== Service Worker / マニフェスト生成 ==========

    def generate_service_worker(self) -> str:
        """Service Workerスクリプトを生成"""
        return """// TradePost Pro - Service Worker for Push Notifications
'use strict';

const CACHE_NAME = 'tradepost-pro-v1';
const OFFLINE_URL = '/offline.html';

// インストール
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll([
        '/',
        '/offline.html',
        '/icons/icon-192x192.png',
        '/icons/icon-512x512.png',
        '/icons/badge-72x72.png',
      ]);
    })
  );
  self.skipWaiting();
});

// アクティベーション
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.filter((name) => name !== CACHE_NAME)
          .map((name) => caches.delete(name))
      );
    })
  );
  self.clients.claim();
});

// プッシュ通知受信
self.addEventListener('push', (event) => {
  const data = event.data ? event.data.json() : {};
  const options = {
    body: data.body || '',
    icon: data.icon || '/icons/icon-192x192.png',
    badge: data.badge || '/icons/badge-72x72.png',
    image: data.image || undefined,
    tag: data.tag || 'default',
    data: data.data || {},
    actions: data.actions || [],
    requireInteraction: data.requireInteraction || false,
    silent: data.silent || false,
    vibrate: data.vibrate || [200, 100, 200],
  };

  event.waitUntil(
    self.registration.showNotification(data.title || 'TradePost Pro', options)
  );
});

// 通知クリック
self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const action = event.action;
  const data = event.notification.data || {};
  let url = data.url || '/dashboard';

  if (action === 'retry') {
    url = '/dashboard/posts?retry=true';
  } else if (action === 'share') {
    url = '/dashboard/achievements?share=true';
  } else if (action === 'view') {
    url = data.url || '/dashboard';
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        for (const client of clientList) {
          if (client.url.includes('/dashboard') && 'focus' in client) {
            client.navigate(url);
            return client.focus();
          }
        }
        return clients.openWindow(url);
      })
  );
});

// バックグラウンド同期
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-posts') {
    event.waitUntil(syncPosts());
  }
});

async function syncPosts() {
  // オフライン時のキューされた投稿を同期
  const cache = await caches.open('post-queue');
  const requests = await cache.keys();
  for (const request of requests) {
    try {
      await fetch(request);
      await cache.delete(request);
    } catch (error) {
      console.error('Sync failed:', error);
    }
  }
}

// フェッチハンドラ（オフライン対応）
self.addEventListener('fetch', (event) => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => {
        return caches.match(OFFLINE_URL);
      })
    );
  }
});
"""

    def generate_manifest(self) -> dict:
        """PWAマニフェストを生成"""
        return {
            "name": "TradePost Pro",
            "short_name": "TradePost",
            "description": "FXトレード結果をSNSに自動投稿",
            "start_url": "/dashboard",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#1a1a2e",
            "theme_color": "#4f46e5",
            "lang": "ja",
            "icons": [
                {"src": "/icons/icon-72x72.png", "sizes": "72x72", "type": "image/png"},
                {"src": "/icons/icon-96x96.png", "sizes": "96x96", "type": "image/png"},
                {"src": "/icons/icon-128x128.png", "sizes": "128x128", "type": "image/png"},
                {"src": "/icons/icon-144x144.png", "sizes": "144x144", "type": "image/png"},
                {"src": "/icons/icon-152x152.png", "sizes": "152x152", "type": "image/png"},
                {"src": "/icons/icon-192x192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/icons/icon-384x384.png", "sizes": "384x384", "type": "image/png"},
                {"src": "/icons/icon-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            ],
            "categories": ["finance", "productivity"],
            "screenshots": [
                {"src": "/screenshots/dashboard.png", "sizes": "1280x720", "type": "image/png"},
                {"src": "/screenshots/mobile.png", "sizes": "750x1334", "type": "image/png"},
            ],
            "shortcuts": [
                {"name": "ダッシュボード", "url": "/dashboard", "icons": [{"src": "/icons/shortcut-dashboard.png", "sizes": "96x96"}]},
                {"name": "投稿一覧", "url": "/dashboard/posts", "icons": [{"src": "/icons/shortcut-posts.png", "sizes": "96x96"}]},
                {"name": "取引結果", "url": "/dashboard/trades", "icons": [{"src": "/icons/shortcut-trades.png", "sizes": "96x96"}]},
            ],
        }

    def generate_push_subscription_js(self) -> str:
        """プッシュ通知登録用のJavaScriptを生成"""
        return f"""
// TradePost Pro - Push Notification Registration
async function registerPushNotification() {{
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) {{
    console.warn('Push notifications not supported');
    return null;
  }}

  try {{
    const registration = await navigator.serviceWorker.register('/sw.js');
    console.log('Service Worker registered');

    const permission = await Notification.requestPermission();
    if (permission !== 'granted') {{
      console.warn('Notification permission denied');
      return null;
    }}

    const subscription = await registration.pushManager.subscribe({{
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array('{self.vapid_public_key}'),
    }});

    // サーバーに登録
    const response = await fetch('/api/v1/push/subscribe', {{
      method: 'POST',
      headers: {{
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + getAuthToken(),
      }},
      body: JSON.stringify(subscription),
    }});

    return await response.json();
  }} catch (error) {{
    console.error('Push registration failed:', error);
    return null;
  }}
}}

function urlBase64ToUint8Array(base64String) {{
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {{
    outputArray[i] = rawData.charCodeAt(i);
  }}
  return outputArray;
}}
"""

    def get_notification_stats(self, user_id: str = None) -> dict:
        """通知統計を取得"""
        logs = self.notification_logs
        if user_id:
            logs = [l for l in logs if l.user_id == user_id]

        total = len(logs)
        delivered = sum(1 for l in logs if l.delivered)
        clicked = sum(1 for l in logs if l.clicked)

        by_type = {}
        for log in logs:
            t = log.notification_type.value
            if t not in by_type:
                by_type[t] = 0
            by_type[t] += 1

        return {
            "total_sent": total,
            "total_delivered": delivered,
            "total_clicked": clicked,
            "delivery_rate": (delivered / total * 100) if total > 0 else 0,
            "click_rate": (clicked / total * 100) if total > 0 else 0,
            "by_type": by_type,
            "total_subscribers": sum(len(subs) for subs in self.subscriptions.values()),
        }


# テスト実行
if __name__ == "__main__":
    service = PWAPushService({"vapid_public_key": "BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkOs-N0y0"})

    print("=== PWAプッシュ通知サービス テスト ===")

    # サブスクリプション登録
    print("\n--- サブスクリプション登録 ---")
    result = service.register_subscription("user_001", {
        "endpoint": "https://fcm.googleapis.com/fcm/send/test123",
        "keys": {"p256dh": "test_p256dh", "auth": "test_auth"},
        "user_agent": "Chrome/120",
    })
    print(f"  登録結果: {result}")

    # 通知設定
    print("\n--- 通知設定 ---")
    prefs = service.set_preferences("user_001", {
        "promotion": False,
        "maintenance": True,
    })
    print(f"  設定: {json.dumps(prefs, indent=2)}")

    # 各種通知テスト
    print("\n--- 投稿成功通知 ---")
    result = service.notify_post_success("user_001", "X (Twitter)", "https://x.com/test/123")
    print(f"  結果: {result['success']}, 受信者: {result.get('recipients', 0)}")

    print("\n--- 投稿失敗通知 ---")
    result = service.notify_post_failed("user_001", "Instagram", "API認証エラー")
    print(f"  結果: {result['success']}")

    print("\n--- 取引結果通知 ---")
    result = service.notify_trade_result("user_001", 15000, 66.7)
    print(f"  結果: {result['success']}")
    print(f"  タイトル: {result['payload']['title']}")
    print(f"  本文: {result['payload']['body']}")

    print("\n--- バッジ獲得通知 ---")
    result = service.notify_badge_earned("user_001", "投稿マスター", "📝")
    print(f"  結果: {result['success']}")

    print("\n--- レベルアップ通知 ---")
    result = service.notify_level_up("user_001", 5, "アクティブトレーダー")
    print(f"  結果: {result['success']}")

    # マニフェスト
    print("\n--- PWAマニフェスト ---")
    manifest = service.generate_manifest()
    print(f"  アプリ名: {manifest['name']}")
    print(f"  アイコン数: {len(manifest['icons'])}")
    print(f"  ショートカット数: {len(manifest['shortcuts'])}")

    # Service Worker
    print("\n--- Service Worker ---")
    sw = service.generate_service_worker()
    print(f"  スクリプト長: {len(sw)}文字")

    # 統計
    print("\n--- 通知統計 ---")
    stats = service.get_notification_stats("user_001")
    print(f"  送信数: {stats['total_sent']}")
    print(f"  配信率: {stats['delivery_rate']:.1f}%")
    print(f"  タイプ別: {stats['by_type']}")

    print("\n✓ PWAプッシュ通知サービス テスト完了")
