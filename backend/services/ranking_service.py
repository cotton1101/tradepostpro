"""
TradePost Pro - ランキング機能サービス
ユーザー間の月間損益ランキング（オプトイン方式）
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class RankingPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ALL_TIME = "all_time"


class RankingCategory(str, Enum):
    PROFIT = "profit"           # 損益額ランキング
    WIN_RATE = "win_rate"       # 勝率ランキング
    CONSISTENCY = "consistency" # 安定性ランキング（連続プラス日数）
    TRADE_COUNT = "trade_count" # 取引回数ランキング


@dataclass
class RankingEntry:
    """ランキングエントリ"""
    rank: int = 0
    user_id: str = ""
    display_name: str = ""
    avatar_url: str = ""
    value: float = 0.0
    formatted_value: str = ""
    change: int = 0          # 前回からの順位変動（+上昇, -下降）
    badge: str = ""          # 特別バッジ
    streak_days: int = 0     # 連続日数


@dataclass
class RankingBoard:
    """ランキングボード"""
    category: str = ""
    period: str = ""
    entries: List[RankingEntry] = field(default_factory=list)
    total_participants: int = 0
    updated_at: str = ""
    my_rank: Optional[RankingEntry] = None


class RankingService:
    """ランキング機能サービス"""

    BADGES = {
        1: "👑",    # 1位
        2: "🥈",    # 2位
        3: "🥉",    # 3位
        "streak_7": "🔥",     # 7日連続プラス
        "streak_30": "⚡",    # 30日連続プラス
        "newcomer": "🌟",     # 新規参加者
        "consistent": "💎",   # 安定トレーダー
    }

    def __init__(self):
        self.opted_in_users: Dict[str, Dict] = {}
        self.trade_records: List[Dict] = []
        self.previous_rankings: Dict[str, Dict[str, int]] = {}

    # ============================================================
    # オプトイン管理
    # ============================================================

    def opt_in(self, user_id: str, display_name: str, avatar_url: str = "") -> Dict:
        """ランキングに参加"""
        self.opted_in_users[user_id] = {
            "user_id": user_id,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "opted_in_at": datetime.now().isoformat(),
            "is_active": True,
        }
        return {"status": "success", "message": f"{display_name}がランキングに参加しました"}

    def opt_out(self, user_id: str) -> Dict:
        """ランキングから脱退"""
        if user_id in self.opted_in_users:
            self.opted_in_users[user_id]["is_active"] = False
            return {"status": "success", "message": "ランキングから脱退しました"}
        return {"status": "error", "message": "ユーザーが見つかりません"}

    def is_opted_in(self, user_id: str) -> bool:
        """参加状態を確認"""
        user = self.opted_in_users.get(user_id)
        return user is not None and user.get("is_active", False)

    # ============================================================
    # データ記録
    # ============================================================

    def record_trade_result(
        self,
        user_id: str,
        date: str,
        profit: float,
        wins: int,
        losses: int,
        win_rate: float,
        total_trades: int,
    ) -> None:
        """取引結果を記録"""
        if not self.is_opted_in(user_id):
            return

        self.trade_records.append({
            "user_id": user_id,
            "date": date,
            "profit": profit,
            "wins": wins,
            "losses": losses,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "recorded_at": datetime.now().isoformat(),
        })

    # ============================================================
    # ランキング生成
    # ============================================================

    def get_ranking(
        self,
        category: RankingCategory = RankingCategory.PROFIT,
        period: RankingPeriod = RankingPeriod.MONTHLY,
        limit: int = 50,
        requesting_user_id: Optional[str] = None,
    ) -> RankingBoard:
        """ランキングを取得"""
        # 期間でフィルタ
        filtered = self._filter_by_period(period)

        # アクティブユーザーのみ
        active_users = {uid for uid, data in self.opted_in_users.items() if data.get("is_active")}
        filtered = [r for r in filtered if r["user_id"] in active_users]

        # カテゴリ別に集計
        if category == RankingCategory.PROFIT:
            aggregated = self._aggregate_profit(filtered)
        elif category == RankingCategory.WIN_RATE:
            aggregated = self._aggregate_win_rate(filtered)
        elif category == RankingCategory.CONSISTENCY:
            aggregated = self._aggregate_consistency(filtered)
        elif category == RankingCategory.TRADE_COUNT:
            aggregated = self._aggregate_trade_count(filtered)
        else:
            aggregated = self._aggregate_profit(filtered)

        # ソート
        sorted_entries = sorted(aggregated, key=lambda x: x["value"], reverse=True)

        # ランキングエントリ生成
        entries = []
        for i, entry in enumerate(sorted_entries[:limit]):
            rank = i + 1
            user_data = self.opted_in_users.get(entry["user_id"], {})

            # 順位変動の計算
            prev_key = f"{category.value}_{period.value}"
            prev_rank = self.previous_rankings.get(prev_key, {}).get(entry["user_id"], 0)
            change = prev_rank - rank if prev_rank > 0 else 0

            # バッジ
            badge = self.BADGES.get(rank, "")

            entries.append(RankingEntry(
                rank=rank,
                user_id=entry["user_id"],
                display_name=user_data.get("display_name", "Unknown"),
                avatar_url=user_data.get("avatar_url", ""),
                value=entry["value"],
                formatted_value=entry.get("formatted", f"{entry['value']:,.0f}"),
                change=change,
                badge=badge,
                streak_days=entry.get("streak", 0),
            ))

        # 自分の順位
        my_rank = None
        if requesting_user_id:
            for entry in entries:
                if entry.user_id == requesting_user_id:
                    my_rank = entry
                    break

        # 前回ランキングを保存
        prev_key = f"{category.value}_{period.value}"
        self.previous_rankings[prev_key] = {
            e.user_id: e.rank for e in entries
        }

        return RankingBoard(
            category=category.value,
            period=period.value,
            entries=entries,
            total_participants=len(active_users),
            updated_at=datetime.now().isoformat(),
            my_rank=my_rank,
        )

    # ============================================================
    # 集計ロジック
    # ============================================================

    def _filter_by_period(self, period: RankingPeriod) -> List[Dict]:
        """期間でフィルタ"""
        now = datetime.now()

        if period == RankingPeriod.DAILY:
            cutoff = now.strftime("%Y-%m-%d")
            return [r for r in self.trade_records if r["date"] == cutoff]
        elif period == RankingPeriod.WEEKLY:
            cutoff = (now - timedelta(days=7)).strftime("%Y-%m-%d")
            return [r for r in self.trade_records if r["date"] >= cutoff]
        elif period == RankingPeriod.MONTHLY:
            cutoff = (now - timedelta(days=30)).strftime("%Y-%m-%d")
            return [r for r in self.trade_records if r["date"] >= cutoff]
        else:
            return self.trade_records

    def _aggregate_profit(self, records: List[Dict]) -> List[Dict]:
        """損益額で集計"""
        user_profits = {}
        for r in records:
            uid = r["user_id"]
            user_profits[uid] = user_profits.get(uid, 0) + r["profit"]

        return [
            {"user_id": uid, "value": profit, "formatted": f"{profit:+,.0f}円"}
            for uid, profit in user_profits.items()
        ]

    def _aggregate_win_rate(self, records: List[Dict]) -> List[Dict]:
        """勝率で集計"""
        user_stats = {}
        for r in records:
            uid = r["user_id"]
            if uid not in user_stats:
                user_stats[uid] = {"wins": 0, "total": 0}
            user_stats[uid]["wins"] += r["wins"]
            user_stats[uid]["total"] += r["wins"] + r["losses"]

        return [
            {
                "user_id": uid,
                "value": (stats["wins"] / stats["total"] * 100) if stats["total"] > 0 else 0,
                "formatted": f"{(stats['wins'] / stats['total'] * 100):.1f}%" if stats["total"] > 0 else "0.0%",
            }
            for uid, stats in user_stats.items()
        ]

    def _aggregate_consistency(self, records: List[Dict]) -> List[Dict]:
        """安定性（連続プラス日数）で集計"""
        user_dates = {}
        for r in records:
            uid = r["user_id"]
            if uid not in user_dates:
                user_dates[uid] = {}
            user_dates[uid][r["date"]] = r["profit"]

        results = []
        for uid, dates in user_dates.items():
            sorted_dates = sorted(dates.keys(), reverse=True)
            streak = 0
            for date in sorted_dates:
                if dates[date] > 0:
                    streak += 1
                else:
                    break
            results.append({
                "user_id": uid,
                "value": streak,
                "formatted": f"{streak}日連続",
                "streak": streak,
            })

        return results

    def _aggregate_trade_count(self, records: List[Dict]) -> List[Dict]:
        """取引回数で集計"""
        user_counts = {}
        for r in records:
            uid = r["user_id"]
            user_counts[uid] = user_counts.get(uid, 0) + r["total_trades"]

        return [
            {"user_id": uid, "value": count, "formatted": f"{count:,}回"}
            for uid, count in user_counts.items()
        ]

    # ============================================================
    # SNS投稿用フォーマット
    # ============================================================

    def format_for_sns(self, board: RankingBoard, top_n: int = 5) -> str:
        """ランキングをSNS投稿用にフォーマット"""
        period_names = {
            "daily": "本日", "weekly": "今週", "monthly": "今月", "all_time": "累計"
        }
        category_names = {
            "profit": "損益額", "win_rate": "勝率",
            "consistency": "連続プラス", "trade_count": "取引回数"
        }

        period_name = period_names.get(board.period, board.period)
        category_name = category_names.get(board.category, board.category)

        lines = [f"🏆 {period_name}の{category_name}ランキング", ""]

        for entry in board.entries[:top_n]:
            badge = entry.badge or f"{entry.rank}."
            change_str = ""
            if entry.change > 0:
                change_str = f" (↑{entry.change})"
            elif entry.change < 0:
                change_str = f" (↓{abs(entry.change)})"

            lines.append(f"{badge} {entry.display_name}: {entry.formatted_value}{change_str}")

        lines.append(f"\n参加者: {board.total_participants}名")
        return "\n".join(lines)


# テスト用
if __name__ == "__main__":
    service = RankingService()

    # ユーザー登録
    users = [
        ("user1", "トレーダーA"), ("user2", "FXマスターB"),
        ("user3", "初心者C"), ("user4", "プロD"), ("user5", "チャレンジャーE"),
    ]
    for uid, name in users:
        service.opt_in(uid, name)

    # 取引データ登録
    import random
    today = datetime.now().strftime("%Y-%m-%d")
    for uid, _ in users:
        for i in range(10):
            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            profit = random.randint(-20000, 50000)
            wins = random.randint(3, 10)
            losses = random.randint(1, 7)
            service.record_trade_result(uid, date, profit, wins, losses,
                                        wins / (wins + losses) * 100, wins + losses)

    # ランキング取得
    print("=== 月間損益ランキング ===")
    board = service.get_ranking(RankingCategory.PROFIT, RankingPeriod.MONTHLY, requesting_user_id="user3")
    print(service.format_for_sns(board))

    print("\n=== 月間勝率ランキング ===")
    board2 = service.get_ranking(RankingCategory.WIN_RATE, RankingPeriod.MONTHLY)
    print(service.format_for_sns(board2))

    print("\n=== 連続プラスランキング ===")
    board3 = service.get_ranking(RankingCategory.CONSISTENCY, RankingPeriod.ALL_TIME)
    print(service.format_for_sns(board3))

    # オプトアウト
    service.opt_out("user3")
    print(f"\nuser3 参加状態: {service.is_opted_in('user3')}")

    print("\n✓ ランキングサービス テスト完了")
