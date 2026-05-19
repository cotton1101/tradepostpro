"""
TradePost Pro - リアルタイムサービス
WebSocketで損益データ・投稿状態をリアルタイム配信
"""

import json
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List, Set, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ChannelType(str, Enum):
    """チャンネル種別"""
    TRADE_UPDATE = "trade.update"         # 取引データ更新
    POST_STATUS = "post.status"           # 投稿ステータス変更
    SYSTEM_ALERT = "system.alert"         # システムアラート
    ACCOUNT_UPDATE = "account.update"     # アカウント情報更新
    REALTIME_PNL = "realtime.pnl"         # リアルタイム損益


@dataclass
class WebSocketClient:
    """WebSocketクライアント情報"""
    client_id: str = ""
    user_id: str = ""
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: str = ""
    last_ping: str = ""
    is_active: bool = True


@dataclass
class RealtimeMessage:
    """リアルタイムメッセージ"""
    channel: str
    event: str
    data: Dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class RealtimeService:
    """リアルタイム配信サービス"""

    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}
        self.user_clients: Dict[str, Set[str]] = {}  # user_id -> {client_id}
        self.message_queue: List[RealtimeMessage] = []
        self._handlers: Dict[str, List] = {}

    # ============================================================
    # クライアント管理
    # ============================================================

    def register_client(self, client_id: str, user_id: str) -> WebSocketClient:
        """クライアント登録"""
        client = WebSocketClient(
            client_id=client_id,
            user_id=user_id,
            connected_at=datetime.now().isoformat(),
            last_ping=datetime.now().isoformat(),
        )
        self.clients[client_id] = client

        if user_id not in self.user_clients:
            self.user_clients[user_id] = set()
        self.user_clients[user_id].add(client_id)

        logger.info(f"WebSocket接続: client={client_id}, user={user_id}")
        return client

    def unregister_client(self, client_id: str):
        """クライアント登録解除"""
        client = self.clients.get(client_id)
        if client:
            if client.user_id in self.user_clients:
                self.user_clients[client.user_id].discard(client_id)
            del self.clients[client_id]
            logger.info(f"WebSocket切断: client={client_id}")

    def subscribe(self, client_id: str, channel: str) -> bool:
        """チャンネル購読"""
        client = self.clients.get(client_id)
        if not client:
            return False
        client.subscriptions.add(channel)
        logger.debug(f"購読追加: client={client_id}, channel={channel}")
        return True

    def unsubscribe(self, client_id: str, channel: str) -> bool:
        """チャンネル購読解除"""
        client = self.clients.get(client_id)
        if not client:
            return False
        client.subscriptions.discard(channel)
        return True

    # ============================================================
    # メッセージ配信
    # ============================================================

    def broadcast_to_user(self, user_id: str, message: RealtimeMessage) -> int:
        """特定ユーザーの全クライアントに配信"""
        client_ids = self.user_clients.get(user_id, set())
        sent_count = 0

        for client_id in client_ids:
            client = self.clients.get(client_id)
            if client and client.is_active:
                if message.channel in client.subscriptions or "*" in client.subscriptions:
                    self._deliver(client_id, message)
                    sent_count += 1

        return sent_count

    def broadcast_all(self, message: RealtimeMessage) -> int:
        """全クライアントに配信"""
        sent_count = 0
        for client_id, client in self.clients.items():
            if client.is_active:
                if message.channel in client.subscriptions or "*" in client.subscriptions:
                    self._deliver(client_id, message)
                    sent_count += 1
        return sent_count

    def _deliver(self, client_id: str, message: RealtimeMessage):
        """メッセージ配信（実際のWebSocket送信はFastAPIのWebSocketハンドラで実行）"""
        self.message_queue.append(message)
        # 実際の実装ではここでWebSocket.send()を呼ぶ
        logger.debug(f"配信: client={client_id}, channel={message.channel}")

    # ============================================================
    # イベント発火ヘルパー
    # ============================================================

    def emit_trade_update(self, user_id: str, trade_data: Dict):
        """取引データ更新を配信"""
        message = RealtimeMessage(
            channel=ChannelType.TRADE_UPDATE,
            event="update",
            data={
                "date": trade_data.get("date", ""),
                "profit": trade_data.get("profit", 0),
                "total_trades": trade_data.get("total_trades", 0),
                "wins": trade_data.get("wins", 0),
                "losses": trade_data.get("losses", 0),
                "win_rate": trade_data.get("win_rate", 0),
                "cumulative_profit": trade_data.get("cumulative_profit", 0),
            }
        )
        return self.broadcast_to_user(user_id, message)

    def emit_post_status(self, user_id: str, post_id: str, platform: str, status: str, detail: str = ""):
        """投稿ステータス変更を配信"""
        message = RealtimeMessage(
            channel=ChannelType.POST_STATUS,
            event=status,
            data={
                "post_id": post_id,
                "platform": platform,
                "status": status,
                "detail": detail,
            }
        )
        return self.broadcast_to_user(user_id, message)

    def emit_system_alert(self, user_id: str, alert_type: str, title: str, body: str):
        """システムアラートを配信"""
        message = RealtimeMessage(
            channel=ChannelType.SYSTEM_ALERT,
            event=alert_type,
            data={
                "type": alert_type,
                "title": title,
                "body": body,
            }
        )
        return self.broadcast_to_user(user_id, message)

    def emit_realtime_pnl(self, user_id: str, pnl_data: Dict):
        """リアルタイム損益を配信"""
        message = RealtimeMessage(
            channel=ChannelType.REALTIME_PNL,
            event="tick",
            data=pnl_data
        )
        return self.broadcast_to_user(user_id, message)

    # ============================================================
    # 統計
    # ============================================================

    def get_stats(self) -> Dict:
        """接続統計"""
        active = sum(1 for c in self.clients.values() if c.is_active)
        return {
            "total_clients": len(self.clients),
            "active_clients": active,
            "total_users": len(self.user_clients),
            "total_messages_queued": len(self.message_queue),
        }

    def get_client_info(self, client_id: str) -> Optional[Dict]:
        """クライアント情報取得"""
        client = self.clients.get(client_id)
        if not client:
            return None
        return {
            "client_id": client.client_id,
            "user_id": client.user_id,
            "subscriptions": list(client.subscriptions),
            "connected_at": client.connected_at,
            "is_active": client.is_active,
        }


# FastAPI WebSocketエンドポイント用のコード例
WEBSOCKET_ENDPOINT_CODE = '''
# FastAPI WebSocketエンドポイント（app.pyに追加）
from fastapi import WebSocket, WebSocketDisconnect
import uuid

realtime = RealtimeService()

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    client_id = str(uuid.uuid4())[:8]
    client = realtime.register_client(client_id, user_id)

    # デフォルトで全チャンネルを購読
    for channel in ChannelType:
        realtime.subscribe(client_id, channel.value)

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

            elif msg.get("type") == "subscribe":
                realtime.subscribe(client_id, msg["channel"])

            elif msg.get("type") == "unsubscribe":
                realtime.unsubscribe(client_id, msg["channel"])

    except WebSocketDisconnect:
        realtime.unregister_client(client_id)
'''


# テスト用
if __name__ == "__main__":
    service = RealtimeService()

    # クライアント登録
    client = service.register_client("ws_001", "user_001")
    service.subscribe("ws_001", ChannelType.TRADE_UPDATE)
    service.subscribe("ws_001", ChannelType.POST_STATUS)
    print(f"クライアント登録: {client.client_id}")

    # 取引データ更新配信
    count = service.emit_trade_update("user_001", {
        "date": "2026-03-11",
        "profit": 17000,
        "total_trades": 12,
        "wins": 8,
        "losses": 4,
        "win_rate": 66.7,
    })
    print(f"取引更新配信: {count}クライアント")

    # 投稿ステータス配信
    count = service.emit_post_status("user_001", "post_123", "x", "completed")
    print(f"投稿ステータス配信: {count}クライアント")

    # 統計
    stats = service.get_stats()
    print(f"\n接続統計: {json.dumps(stats, indent=2)}")

    print("\n✓ リアルタイムサービス テスト完了")
