"""
ポートフォリオ分析サービス
通貨ペア別の分析、リスク指標、パフォーマンス評価
"""

import math
import statistics
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Trade:
    """個別取引データ"""
    id: str
    date: str
    currency_pair: str
    direction: str  # "buy" or "sell"
    lot_size: float
    entry_price: float
    exit_price: float
    profit: float
    pips: float
    duration_minutes: int
    commission: float = 0
    swap: float = 0


@dataclass
class CurrencyPairStats:
    """通貨ペア別統計"""
    pair: str
    total_trades: int
    wins: int
    losses: int
    win_rate: float
    total_profit: float
    avg_profit: float
    max_profit: float
    max_loss: float
    total_pips: float
    avg_pips: float
    avg_duration: float
    profit_factor: float
    expectancy: float


class PortfolioService:
    """ポートフォリオ分析サービス"""

    def __init__(self):
        self.trades: Dict[str, List[Trade]] = {}  # user_id -> [Trade]

    def add_trade(self, user_id: str, trade: Trade) -> bool:
        """取引を追加"""
        if user_id not in self.trades:
            self.trades[user_id] = []
        self.trades[user_id].append(trade)
        return True

    def get_portfolio_summary(self, user_id: str) -> dict:
        """ポートフォリオサマリーを取得"""
        trades = self.trades.get(user_id, [])
        if not trades:
            return {"error": "No trades found"}

        total_profit = sum(t.profit for t in trades)
        total_trades = len(trades)
        wins = [t for t in trades if t.profit > 0]
        losses = [t for t in trades if t.profit <= 0]
        win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0

        gross_profit = sum(t.profit for t in wins) if wins else 0
        gross_loss = abs(sum(t.profit for t in losses)) if losses else 1
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0

        # 日別損益
        daily_profits = {}
        for t in trades:
            daily_profits[t.date] = daily_profits.get(t.date, 0) + t.profit
        daily_values = list(daily_profits.values())

        # リスク指標
        risk_metrics = self._calculate_risk_metrics(daily_values)

        return {
            "total_profit": total_profit,
            "total_trades": total_trades,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "gross_profit": gross_profit,
            "gross_loss": -abs(sum(t.profit for t in losses)) if losses else 0,
            "avg_profit_per_trade": total_profit / total_trades if total_trades > 0 else 0,
            "avg_win": gross_profit / len(wins) if wins else 0,
            "avg_loss": sum(t.profit for t in losses) / len(losses) if losses else 0,
            "largest_win": max(t.profit for t in trades),
            "largest_loss": min(t.profit for t in trades),
            "total_pips": sum(t.pips for t in trades),
            "avg_pips": sum(t.pips for t in trades) / total_trades if total_trades > 0 else 0,
            "total_commission": sum(t.commission for t in trades),
            "total_swap": sum(t.swap for t in trades),
            "trading_days": len(daily_profits),
            "risk_metrics": risk_metrics,
        }

    def get_currency_pair_analysis(self, user_id: str) -> List[dict]:
        """通貨ペア別分析を取得"""
        trades = self.trades.get(user_id, [])
        if not trades:
            return []

        # 通貨ペア別にグループ化
        pair_trades: Dict[str, List[Trade]] = {}
        for t in trades:
            if t.currency_pair not in pair_trades:
                pair_trades[t.currency_pair] = []
            pair_trades[t.currency_pair].append(t)

        results = []
        for pair, pair_trade_list in pair_trades.items():
            wins = [t for t in pair_trade_list if t.profit > 0]
            losses_list = [t for t in pair_trade_list if t.profit <= 0]
            total = len(pair_trade_list)

            gross_profit = sum(t.profit for t in wins) if wins else 0
            gross_loss = abs(sum(t.profit for t in losses_list)) if losses_list else 1

            avg_win = gross_profit / len(wins) if wins else 0
            avg_loss = abs(sum(t.profit for t in losses_list) / len(losses_list)) if losses_list else 0
            win_rate = len(wins) / total if total > 0 else 0
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

            stats = CurrencyPairStats(
                pair=pair,
                total_trades=total,
                wins=len(wins),
                losses=len(losses_list),
                win_rate=win_rate * 100,
                total_profit=sum(t.profit for t in pair_trade_list),
                avg_profit=sum(t.profit for t in pair_trade_list) / total,
                max_profit=max(t.profit for t in pair_trade_list),
                max_loss=min(t.profit for t in pair_trade_list),
                total_pips=sum(t.pips for t in pair_trade_list),
                avg_pips=sum(t.pips for t in pair_trade_list) / total,
                avg_duration=sum(t.duration_minutes for t in pair_trade_list) / total,
                profit_factor=gross_profit / gross_loss if gross_loss > 0 else 0,
                expectancy=expectancy,
            )
            results.append(self._pair_stats_to_dict(stats))

        # 利益順にソート
        results.sort(key=lambda x: x["total_profit"], reverse=True)
        return results

    def get_time_analysis(self, user_id: str) -> dict:
        """時間帯別分析を取得"""
        trades = self.trades.get(user_id, [])
        if not trades:
            return {}

        # 曜日別
        weekday_stats = {i: {"trades": 0, "profit": 0, "wins": 0} for i in range(7)}
        # 月別
        monthly_stats = {}

        for t in trades:
            d = datetime.strptime(t.date, "%Y-%m-%d")
            wd = d.weekday()
            weekday_stats[wd]["trades"] += 1
            weekday_stats[wd]["profit"] += t.profit
            if t.profit > 0:
                weekday_stats[wd]["wins"] += 1

            month_key = d.strftime("%Y-%m")
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {"trades": 0, "profit": 0, "wins": 0}
            monthly_stats[month_key]["trades"] += 1
            monthly_stats[month_key]["profit"] += t.profit
            if t.profit > 0:
                monthly_stats[month_key]["wins"] += 1

        weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
        weekday_result = []
        for i in range(7):
            s = weekday_stats[i]
            weekday_result.append({
                "weekday": weekday_names[i],
                "trades": s["trades"],
                "profit": s["profit"],
                "win_rate": (s["wins"] / s["trades"] * 100) if s["trades"] > 0 else 0,
            })

        monthly_result = []
        for month, s in sorted(monthly_stats.items()):
            monthly_result.append({
                "month": month,
                "trades": s["trades"],
                "profit": s["profit"],
                "win_rate": (s["wins"] / s["trades"] * 100) if s["trades"] > 0 else 0,
            })

        return {
            "by_weekday": weekday_result,
            "by_month": monthly_result,
        }

    def get_drawdown_analysis(self, user_id: str) -> dict:
        """ドローダウン分析を取得"""
        trades = self.trades.get(user_id, [])
        if not trades:
            return {}

        # 累積損益の推移
        sorted_trades = sorted(trades, key=lambda t: t.date)
        equity_curve = []
        cumulative = 0
        peak = 0
        max_drawdown = 0
        max_drawdown_percent = 0
        drawdown_start = ""
        drawdown_end = ""
        current_dd_start = ""

        for t in sorted_trades:
            cumulative += t.profit
            equity_curve.append({
                "date": t.date,
                "equity": cumulative,
                "trade_id": t.id,
            })

            if cumulative > peak:
                peak = cumulative
                current_dd_start = t.date
            else:
                dd = peak - cumulative
                if dd > max_drawdown:
                    max_drawdown = dd
                    max_drawdown_percent = (dd / peak * 100) if peak > 0 else 0
                    drawdown_start = current_dd_start
                    drawdown_end = t.date

        return {
            "max_drawdown": max_drawdown,
            "max_drawdown_percent": max_drawdown_percent,
            "drawdown_start": drawdown_start,
            "drawdown_end": drawdown_end,
            "peak_equity": peak,
            "final_equity": cumulative,
            "equity_curve_points": len(equity_curve),
        }

    def _calculate_risk_metrics(self, daily_returns: List[float]) -> dict:
        """リスク指標を計算"""
        if not daily_returns or len(daily_returns) < 2:
            return {
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "max_daily_profit": 0,
                "max_daily_loss": 0,
                "volatility": 0,
                "avg_daily_return": 0,
            }

        avg_return = statistics.mean(daily_returns)
        std_dev = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0

        # シャープレシオ（年率化、リスクフリーレート0%）
        sharpe = (avg_return / std_dev * math.sqrt(252)) if std_dev > 0 else 0

        # ソルティノレシオ
        downside_returns = [r for r in daily_returns if r < 0]
        downside_dev = statistics.stdev(downside_returns) if len(downside_returns) > 1 else 1
        sortino = (avg_return / downside_dev * math.sqrt(252)) if downside_dev > 0 else 0

        return {
            "sharpe_ratio": round(sharpe, 2),
            "sortino_ratio": round(sortino, 2),
            "max_daily_profit": max(daily_returns),
            "max_daily_loss": min(daily_returns),
            "volatility": round(std_dev, 2),
            "avg_daily_return": round(avg_return, 2),
        }

    def _pair_stats_to_dict(self, stats: CurrencyPairStats) -> dict:
        """CurrencyPairStatsを辞書に変換"""
        return {
            "pair": stats.pair,
            "total_trades": stats.total_trades,
            "wins": stats.wins,
            "losses": stats.losses,
            "win_rate": round(stats.win_rate, 1),
            "total_profit": round(stats.total_profit),
            "avg_profit": round(stats.avg_profit),
            "max_profit": round(stats.max_profit),
            "max_loss": round(stats.max_loss),
            "total_pips": round(stats.total_pips, 1),
            "avg_pips": round(stats.avg_pips, 1),
            "avg_duration_min": round(stats.avg_duration),
            "profit_factor": round(stats.profit_factor, 2),
            "expectancy": round(stats.expectancy),
        }


# テスト実行
if __name__ == "__main__":
    import random
    random.seed(42)

    service = PortfolioService()

    # サンプル取引データ生成
    pairs = ["USDJPY", "EURUSD", "GBPJPY", "EURJPY", "AUDUSD"]
    for i in range(100):
        day = 1 + (i % 20)
        pair = random.choice(pairs)
        direction = random.choice(["buy", "sell"])
        pips = random.uniform(-30, 40)
        profit = pips * random.uniform(100, 500)
        trade = Trade(
            id=f"trade_{i:04d}",
            date=f"2026-02-{day:02d}",
            currency_pair=pair,
            direction=direction,
            lot_size=random.choice([0.01, 0.05, 0.1, 0.5]),
            entry_price=random.uniform(100, 160),
            exit_price=random.uniform(100, 160),
            profit=round(profit),
            pips=round(pips, 1),
            duration_minutes=random.randint(5, 480),
            commission=round(random.uniform(50, 200)),
            swap=round(random.uniform(-100, 100)),
        )
        service.add_trade("user_001", trade)

    print("=== ポートフォリオサマリー ===")
    summary = service.get_portfolio_summary("user_001")
    print(f"  総損益: {summary['total_profit']:+,.0f} JPY")
    print(f"  総取引数: {summary['total_trades']}")
    print(f"  勝率: {summary['win_rate']:.1f}%")
    print(f"  PF: {summary['profit_factor']:.2f}")
    print(f"  平均利益: {summary['avg_profit_per_trade']:+,.0f} JPY")
    print(f"  最大利益: {summary['largest_win']:+,.0f} JPY")
    print(f"  最大損失: {summary['largest_loss']:+,.0f} JPY")
    print(f"  シャープレシオ: {summary['risk_metrics']['sharpe_ratio']}")
    print(f"  ソルティノレシオ: {summary['risk_metrics']['sortino_ratio']}")

    print("\n=== 通貨ペア別分析 ===")
    pair_analysis = service.get_currency_pair_analysis("user_001")
    print(f"  {'ペア':<10} {'取引数':>6} {'勝率':>6} {'損益':>10} {'PF':>6} {'期待値':>8}")
    print(f"  {'-'*50}")
    for p in pair_analysis:
        print(f"  {p['pair']:<10} {p['total_trades']:>6} {p['win_rate']:>5.1f}% {p['total_profit']:>+10,} {p['profit_factor']:>6.2f} {p['expectancy']:>+8,}")

    print("\n=== 時間帯別分析 ===")
    time_analysis = service.get_time_analysis("user_001")
    print("  曜日別:")
    for wd in time_analysis["by_weekday"]:
        if wd["trades"] > 0:
            print(f"    {wd['weekday']}: {wd['trades']}取引, {wd['profit']:+,.0f} JPY, 勝率{wd['win_rate']:.1f}%")

    print("\n=== ドローダウン分析 ===")
    dd = service.get_drawdown_analysis("user_001")
    print(f"  最大DD: {dd['max_drawdown']:,.0f} JPY ({dd['max_drawdown_percent']:.1f}%)")
    print(f"  ピーク: {dd['peak_equity']:,.0f} JPY")
    print(f"  最終: {dd['final_equity']:,.0f} JPY")

    print("\n✓ ポートフォリオ分析サービス テスト完了")
