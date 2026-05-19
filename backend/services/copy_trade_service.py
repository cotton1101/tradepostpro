"""
TradePost Pro - コピートレード連携サービス
成績の良いトレーダーのシグナルを共有する仕組み
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class SignalType(str, Enum):
    BUY = "buy"
    SELL = "sell"
    CLOSE = "close"


class SignalStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class TradeSignal:
    """トレードシグナル"""
    signal_id: str = ""
    provider_id: str = ""
    provider_name: str = ""
    signal_type: str = ""
    symbol: str = ""
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    lot_size: float = 0.01
    status: str = "active"
    created_at: str = ""
    closed_at: str = ""
    result_pips: float = 0.0
    result_profit: float = 0.0
    comment: str = ""


@dataclass
class SignalProvider:
    """シグナルプロバイダー（トレーダー）"""
    user_id: str = ""
    display_name: str = ""
    is_approved: bool = False
    total_signals: int = 0
    win_rate: float = 0.0
    avg_profit_pips: float = 0.0
    total_followers: int = 0
    monthly_profit: float = 0.0
    risk_score: float = 0.0   # 0-10 (低い方が安全)
    rating: float = 0.0       # 0-5
    description: str = ""


@dataclass
class FollowerStats:
    """フォロワー統計"""
    follower_id: str = ""
    provider_id: str = ""
    followed_since: str = ""
    signals_received: int = 0
    signals_executed: int = 0
    total_profit: float = 0.0


class CopyTradeService:
    """コピートレード連携サービス"""

    # プロバイダー承認基準
    APPROVAL_CRITERIA = {
        "min_trades": 50,           # 最低取引回数
        "min_win_rate": 55.0,       # 最低勝率
        "min_days_active": 30,      # 最低活動日数
        "max_risk_score": 7.0,      # 最大リスクスコア
        "min_avg_profit_pips": 5.0, # 最低平均利益pips
    }

    def __init__(self):
        self.providers: Dict[str, SignalProvider] = {}
        self.signals: List[TradeSignal] = []
        self.followers: Dict[str, List[str]] = {}  # provider_id -> [follower_ids]
        self.follower_stats: Dict[str, Dict[str, FollowerStats]] = {}

    # ============================================================
    # プロバイダー管理
    # ============================================================

    def register_provider(
        self,
        user_id: str,
        display_name: str,
        description: str = "",
        trade_history: Optional[Dict] = None,
    ) -> Dict:
        """シグナルプロバイダーとして登録"""
        # 承認基準チェック
        is_approved = False
        rejection_reasons = []

        if trade_history:
            if trade_history.get("total_trades", 0) < self.APPROVAL_CRITERIA["min_trades"]:
                rejection_reasons.append(f"取引回数が{self.APPROVAL_CRITERIA['min_trades']}回未満")
            if trade_history.get("win_rate", 0) < self.APPROVAL_CRITERIA["min_win_rate"]:
                rejection_reasons.append(f"勝率が{self.APPROVAL_CRITERIA['min_win_rate']}%未満")

            if not rejection_reasons:
                is_approved = True

        provider = SignalProvider(
            user_id=user_id,
            display_name=display_name,
            is_approved=is_approved,
            total_signals=0,
            win_rate=trade_history.get("win_rate", 0) if trade_history else 0,
            avg_profit_pips=trade_history.get("avg_profit_pips", 0) if trade_history else 0,
            total_followers=0,
            monthly_profit=trade_history.get("monthly_profit", 0) if trade_history else 0,
            risk_score=self._calculate_risk_score(trade_history) if trade_history else 5.0,
            rating=0.0,
            description=description,
        )

        self.providers[user_id] = provider
        self.followers[user_id] = []

        if is_approved:
            return {"status": "approved", "message": "シグナルプロバイダーとして承認されました"}
        else:
            return {
                "status": "pending",
                "message": "承認基準を満たしていません",
                "reasons": rejection_reasons,
            }

    def _calculate_risk_score(self, trade_history: Dict) -> float:
        """リスクスコアを計算（0-10）"""
        max_drawdown = trade_history.get("max_drawdown_pct", 0)
        avg_loss = abs(trade_history.get("avg_loss_pips", 0))
        volatility = trade_history.get("profit_volatility", 0)

        score = 0.0
        score += min(max_drawdown / 5, 4.0)   # 最大DD 20%で4点
        score += min(avg_loss / 50, 3.0)       # 平均損失50pipsで3点
        score += min(volatility / 100, 3.0)    # ボラティリティ

        return min(round(score, 1), 10.0)

    def get_providers(
        self,
        sort_by: str = "win_rate",
        approved_only: bool = True,
        limit: int = 20,
    ) -> List[SignalProvider]:
        """プロバイダー一覧を取得"""
        providers = list(self.providers.values())

        if approved_only:
            providers = [p for p in providers if p.is_approved]

        sort_keys = {
            "win_rate": lambda p: p.win_rate,
            "followers": lambda p: p.total_followers,
            "profit": lambda p: p.monthly_profit,
            "rating": lambda p: p.rating,
            "risk": lambda p: -p.risk_score,
        }

        key_func = sort_keys.get(sort_by, sort_keys["win_rate"])
        providers.sort(key=key_func, reverse=True)

        return providers[:limit]

    # ============================================================
    # フォロー管理
    # ============================================================

    def follow_provider(self, follower_id: str, provider_id: str) -> Dict:
        """プロバイダーをフォロー"""
        if provider_id not in self.providers:
            return {"status": "error", "message": "プロバイダーが見つかりません"}

        if not self.providers[provider_id].is_approved:
            return {"status": "error", "message": "このプロバイダーは未承認です"}

        if follower_id in self.followers.get(provider_id, []):
            return {"status": "error", "message": "既にフォロー中です"}

        self.followers.setdefault(provider_id, []).append(follower_id)
        self.providers[provider_id].total_followers += 1

        # フォロワー統計を初期化
        if follower_id not in self.follower_stats:
            self.follower_stats[follower_id] = {}
        self.follower_stats[follower_id][provider_id] = FollowerStats(
            follower_id=follower_id,
            provider_id=provider_id,
            followed_since=datetime.now().isoformat(),
        )

        return {"status": "success", "message": f"{self.providers[provider_id].display_name}をフォローしました"}

    def unfollow_provider(self, follower_id: str, provider_id: str) -> Dict:
        """フォロー解除"""
        if provider_id in self.followers and follower_id in self.followers[provider_id]:
            self.followers[provider_id].remove(follower_id)
            self.providers[provider_id].total_followers -= 1
            return {"status": "success", "message": "フォローを解除しました"}
        return {"status": "error", "message": "フォロー関係が見つかりません"}

    # ============================================================
    # シグナル管理
    # ============================================================

    def create_signal(
        self,
        provider_id: str,
        signal_type: SignalType,
        symbol: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        lot_size: float = 0.01,
        comment: str = "",
    ) -> Dict:
        """シグナルを作成"""
        if provider_id not in self.providers or not self.providers[provider_id].is_approved:
            return {"status": "error", "message": "承認されたプロバイダーのみシグナルを発信できます"}

        signal_id = f"SIG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{len(self.signals)+1}"

        signal = TradeSignal(
            signal_id=signal_id,
            provider_id=provider_id,
            provider_name=self.providers[provider_id].display_name,
            signal_type=signal_type.value,
            symbol=symbol,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            lot_size=lot_size,
            status=SignalStatus.ACTIVE.value,
            created_at=datetime.now().isoformat(),
            comment=comment,
        )

        self.signals.append(signal)
        self.providers[provider_id].total_signals += 1

        # フォロワーに通知
        follower_count = len(self.followers.get(provider_id, []))

        return {
            "status": "success",
            "signal_id": signal_id,
            "notified_followers": follower_count,
        }

    def close_signal(
        self,
        signal_id: str,
        close_price: float,
    ) -> Dict:
        """シグナルをクローズ"""
        for signal in self.signals:
            if signal.signal_id == signal_id and signal.status == SignalStatus.ACTIVE.value:
                signal.status = SignalStatus.CLOSED.value
                signal.closed_at = datetime.now().isoformat()

                # 結果計算
                if signal.signal_type == SignalType.BUY.value:
                    signal.result_pips = round((close_price - signal.entry_price) * 10000, 1)
                else:
                    signal.result_pips = round((signal.entry_price - close_price) * 10000, 1)

                signal.result_profit = round(signal.result_pips * signal.lot_size * 1000, 2)

                return {
                    "status": "success",
                    "result_pips": signal.result_pips,
                    "result_profit": signal.result_profit,
                }

        return {"status": "error", "message": "シグナルが見つかりません"}

    def get_active_signals(self, provider_id: Optional[str] = None) -> List[TradeSignal]:
        """アクティブなシグナルを取得"""
        signals = [s for s in self.signals if s.status == SignalStatus.ACTIVE.value]
        if provider_id:
            signals = [s for s in signals if s.provider_id == provider_id]
        return signals

    # ============================================================
    # SNS投稿用フォーマット
    # ============================================================

    def format_signal_for_sns(self, signal: TradeSignal) -> str:
        """シグナルをSNS投稿用にフォーマット"""
        emoji = "🟢" if signal.signal_type == SignalType.BUY.value else "🔴"
        action = "買い" if signal.signal_type == SignalType.BUY.value else "売り"

        lines = [
            f"{emoji} 【シグナル配信】{signal.symbol} {action}",
            f"",
            f"📍 エントリー: {signal.entry_price}",
            f"🛡️ 損切り: {signal.stop_loss}",
            f"🎯 利確: {signal.take_profit}",
            f"📊 ロット: {signal.lot_size}",
        ]

        if signal.comment:
            lines.append(f"💬 {signal.comment}")

        lines.append(f"\n配信者: {signal.provider_name}")

        return "\n".join(lines)

    def format_result_for_sns(self, signal: TradeSignal) -> str:
        """シグナル結果をSNS投稿用にフォーマット"""
        emoji = "✅" if signal.result_pips > 0 else "❌"
        pips_str = f"+{signal.result_pips}" if signal.result_pips > 0 else f"{signal.result_pips}"

        return (
            f"{emoji} 【シグナル結果】{signal.symbol}\n"
            f"結果: {pips_str} pips ({signal.result_profit:+,.0f}円)\n"
            f"配信者: {signal.provider_name}"
        )

    # ============================================================
    # 統計
    # ============================================================

    def get_provider_stats(self, provider_id: str) -> Dict:
        """プロバイダーの統計情報"""
        provider_signals = [s for s in self.signals if s.provider_id == provider_id]
        closed_signals = [s for s in provider_signals if s.status == SignalStatus.CLOSED.value]

        if not closed_signals:
            return {"total": 0, "wins": 0, "losses": 0, "win_rate": 0, "total_pips": 0}

        wins = len([s for s in closed_signals if s.result_pips > 0])
        losses = len([s for s in closed_signals if s.result_pips <= 0])
        total_pips = sum(s.result_pips for s in closed_signals)

        return {
            "total": len(closed_signals),
            "active": len([s for s in provider_signals if s.status == SignalStatus.ACTIVE.value]),
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / len(closed_signals) * 100, 1) if closed_signals else 0,
            "total_pips": round(total_pips, 1),
            "avg_pips": round(total_pips / len(closed_signals), 1) if closed_signals else 0,
            "followers": len(self.followers.get(provider_id, [])),
        }


# テスト用
if __name__ == "__main__":
    service = CopyTradeService()

    # プロバイダー登録
    print("=== プロバイダー登録 ===")
    result = service.register_provider("trader1", "プロトレーダーA", "10年以上の経験", {
        "total_trades": 100, "win_rate": 68.5, "avg_profit_pips": 15.2,
        "monthly_profit": 150000, "max_drawdown_pct": 8, "avg_loss_pips": 20, "profit_volatility": 30,
    })
    print(f"  trader1: {result}")

    result2 = service.register_provider("trader2", "初心者B", "始めたばかり", {
        "total_trades": 10, "win_rate": 40.0, "avg_profit_pips": 3.0,
    })
    print(f"  trader2: {result2}")

    # フォロー
    print("\n=== フォロー ===")
    print(service.follow_provider("user1", "trader1"))
    print(service.follow_provider("user2", "trader1"))

    # シグナル発信
    print("\n=== シグナル発信 ===")
    sig = service.create_signal("trader1", SignalType.BUY, "USDJPY", 149.500, 149.200, 150.000, 0.1, "東京市場オープンの上昇を狙う")
    print(f"  {sig}")

    # シグナルフォーマット
    active = service.get_active_signals("trader1")
    if active:
        print(f"\n=== SNS投稿フォーマット ===")
        print(service.format_signal_for_sns(active[0]))

    # シグナルクローズ
    if active:
        result = service.close_signal(active[0].signal_id, 149.850)
        print(f"\n=== シグナルクローズ ===")
        print(f"  {result}")
        print(service.format_result_for_sns(service.signals[0]))

    # 統計
    print(f"\n=== プロバイダー統計 ===")
    stats = service.get_provider_stats("trader1")
    print(f"  {stats}")

    print("\n✓ コピートレード連携サービス テスト完了")
