"""
損益カレンダービューサービス
月次・週次の損益をカレンダー形式で表示
"""

import calendar
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from enum import Enum


class CalendarViewMode(Enum):
    """カレンダー表示モード"""
    MONTHLY = "monthly"
    WEEKLY = "weekly"


@dataclass
class DayPnL:
    """日別損益データ"""
    date: str
    profit: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    best_trade: float = 0
    worst_trade: float = 0
    currency_pairs: dict = field(default_factory=dict)
    notes: str = ""


@dataclass
class CalendarCell:
    """カレンダーセル"""
    date: str
    day: int
    is_current_month: bool
    is_today: bool
    is_weekend: bool
    has_data: bool
    pnl: Optional[DayPnL] = None
    css_class: str = ""


class PnLCalendarService:
    """損益カレンダーサービス"""

    def __init__(self):
        self.pnl_data: Dict[str, Dict[str, DayPnL]] = {}  # user_id -> {date_str -> DayPnL}

    def add_daily_pnl(self, user_id: str, day_pnl: DayPnL) -> bool:
        """日別損益データを追加"""
        if user_id not in self.pnl_data:
            self.pnl_data[user_id] = {}
        self.pnl_data[user_id][day_pnl.date] = day_pnl
        return True

    def get_monthly_calendar(self, user_id: str, year: int, month: int) -> dict:
        """月次カレンダーデータを取得"""
        cal = calendar.Calendar(firstweekday=0)  # 月曜始まり
        today = date.today()
        user_data = self.pnl_data.get(user_id, {})

        weeks = []
        month_profit = 0
        month_trades = 0
        month_wins = 0
        month_losses = 0
        trading_days = 0
        profitable_days = 0
        losing_days = 0

        for week_dates in cal.monthdatescalendar(year, month):
            week = []
            for d in week_dates:
                date_str = d.strftime("%Y-%m-%d")
                is_current_month = d.month == month
                is_today = d == today
                is_weekend = d.weekday() >= 5

                pnl = user_data.get(date_str)
                has_data = pnl is not None

                if has_data and is_current_month:
                    month_profit += pnl.profit
                    month_trades += pnl.trades
                    month_wins += pnl.wins
                    month_losses += pnl.losses
                    trading_days += 1
                    if pnl.profit > 0:
                        profitable_days += 1
                    elif pnl.profit < 0:
                        losing_days += 1

                # CSSクラス決定
                css_class = self._get_cell_css_class(pnl, is_current_month, is_today, is_weekend)

                cell = CalendarCell(
                    date=date_str,
                    day=d.day,
                    is_current_month=is_current_month,
                    is_today=is_today,
                    is_weekend=is_weekend,
                    has_data=has_data,
                    pnl=pnl,
                    css_class=css_class,
                )
                week.append(self._cell_to_dict(cell))
            weeks.append(week)

        # 月次サマリー
        summary = {
            "year": year,
            "month": month,
            "month_name": f"{year}年{month}月",
            "total_profit": month_profit,
            "total_trades": month_trades,
            "total_wins": month_wins,
            "total_losses": month_losses,
            "win_rate": (month_wins / month_trades * 100) if month_trades > 0 else 0,
            "trading_days": trading_days,
            "profitable_days": profitable_days,
            "losing_days": losing_days,
            "break_even_days": trading_days - profitable_days - losing_days,
            "avg_daily_profit": month_profit / trading_days if trading_days > 0 else 0,
        }

        return {
            "weeks": weeks,
            "summary": summary,
            "weekday_headers": ["月", "火", "水", "木", "金", "土", "日"],
        }

    def get_weekly_calendar(self, user_id: str, year: int, week_number: int) -> dict:
        """週次カレンダーデータを取得"""
        # ISO週番号から日付を計算
        jan4 = date(year, 1, 4)
        start_of_week = jan4 + timedelta(weeks=week_number - 1, days=-jan4.weekday())
        user_data = self.pnl_data.get(user_id, {})

        days = []
        week_profit = 0
        week_trades = 0

        for i in range(7):
            d = start_of_week + timedelta(days=i)
            date_str = d.strftime("%Y-%m-%d")
            pnl = user_data.get(date_str)

            if pnl:
                week_profit += pnl.profit
                week_trades += pnl.trades

            days.append({
                "date": date_str,
                "day": d.day,
                "weekday": ["月", "火", "水", "木", "金", "土", "日"][d.weekday()],
                "is_weekend": d.weekday() >= 5,
                "has_data": pnl is not None,
                "pnl": self._pnl_to_dict(pnl) if pnl else None,
            })

        return {
            "days": days,
            "week_number": week_number,
            "start_date": start_of_week.strftime("%Y-%m-%d"),
            "end_date": (start_of_week + timedelta(days=6)).strftime("%Y-%m-%d"),
            "summary": {
                "total_profit": week_profit,
                "total_trades": week_trades,
            },
        }

    def get_yearly_heatmap(self, user_id: str, year: int) -> dict:
        """年間ヒートマップデータを取得"""
        user_data = self.pnl_data.get(user_id, {})
        heatmap = []
        yearly_profit = 0
        monthly_profits = {}

        start = date(year, 1, 1)
        end = date(year, 12, 31)
        current = start

        while current <= end:
            date_str = current.strftime("%Y-%m-%d")
            pnl = user_data.get(date_str)
            profit = pnl.profit if pnl else 0

            if pnl:
                yearly_profit += profit
                month_key = current.strftime("%Y-%m")
                monthly_profits[month_key] = monthly_profits.get(month_key, 0) + profit

            # ヒートマップの色レベル（-4〜+4）
            if pnl is None:
                level = 0
            elif profit > 50000:
                level = 4
            elif profit > 20000:
                level = 3
            elif profit > 5000:
                level = 2
            elif profit > 0:
                level = 1
            elif profit > -5000:
                level = -1
            elif profit > -20000:
                level = -2
            elif profit > -50000:
                level = -3
            else:
                level = -4

            heatmap.append({
                "date": date_str,
                "profit": profit,
                "level": level,
                "has_data": pnl is not None,
            })
            current += timedelta(days=1)

        return {
            "year": year,
            "heatmap": heatmap,
            "yearly_profit": yearly_profit,
            "monthly_profits": monthly_profits,
        }

    def get_streak_info(self, user_id: str) -> dict:
        """連勝・連敗情報を取得"""
        user_data = self.pnl_data.get(user_id, {})
        if not user_data:
            return {"current_streak": 0, "max_win_streak": 0, "max_loss_streak": 0}

        sorted_dates = sorted(user_data.keys())
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        temp_win = 0
        temp_loss = 0

        for date_str in sorted_dates:
            pnl = user_data[date_str]
            if pnl.profit > 0:
                temp_win += 1
                temp_loss = 0
                max_win_streak = max(max_win_streak, temp_win)
            elif pnl.profit < 0:
                temp_loss += 1
                temp_win = 0
                max_loss_streak = max(max_loss_streak, temp_loss)
            else:
                temp_win = 0
                temp_loss = 0

        # 現在のストリーク
        if sorted_dates:
            last_pnl = user_data[sorted_dates[-1]]
            if last_pnl.profit > 0:
                current_streak = temp_win
            elif last_pnl.profit < 0:
                current_streak = -temp_loss

        return {
            "current_streak": current_streak,
            "max_win_streak": max_win_streak,
            "max_loss_streak": max_loss_streak,
            "streak_type": "win" if current_streak > 0 else "loss" if current_streak < 0 else "none",
        }

    def _get_cell_css_class(self, pnl: Optional[DayPnL], is_current_month: bool, is_today: bool, is_weekend: bool) -> str:
        """セルのCSSクラスを決定"""
        classes = []
        if not is_current_month:
            classes.append("text-gray-400")
        if is_today:
            classes.append("ring-2 ring-indigo-500")
        if is_weekend:
            classes.append("bg-gray-50")

        if pnl:
            if pnl.profit > 20000:
                classes.append("bg-green-200 text-green-900")
            elif pnl.profit > 0:
                classes.append("bg-green-100 text-green-800")
            elif pnl.profit < -20000:
                classes.append("bg-red-200 text-red-900")
            elif pnl.profit < 0:
                classes.append("bg-red-100 text-red-800")
            else:
                classes.append("bg-yellow-50 text-yellow-800")

        return " ".join(classes)

    def _cell_to_dict(self, cell: CalendarCell) -> dict:
        """CalendarCellを辞書に変換"""
        return {
            "date": cell.date,
            "day": cell.day,
            "is_current_month": cell.is_current_month,
            "is_today": cell.is_today,
            "is_weekend": cell.is_weekend,
            "has_data": cell.has_data,
            "pnl": self._pnl_to_dict(cell.pnl) if cell.pnl else None,
            "css_class": cell.css_class,
        }

    def _pnl_to_dict(self, pnl: DayPnL) -> dict:
        """DayPnLを辞書に変換"""
        return {
            "date": pnl.date,
            "profit": pnl.profit,
            "trades": pnl.trades,
            "wins": pnl.wins,
            "losses": pnl.losses,
            "win_rate": pnl.win_rate,
            "best_trade": pnl.best_trade,
            "worst_trade": pnl.worst_trade,
        }

    def generate_calendar_html(self, calendar_data: dict) -> str:
        """カレンダーHTMLを生成"""
        summary = calendar_data["summary"]
        profit_color = "text-green-600" if summary["total_profit"] >= 0 else "text-red-600"

        html = f"""
<div class="bg-white rounded-xl shadow-lg p-6">
  <div class="flex justify-between items-center mb-6">
    <h2 class="text-2xl font-bold">{summary['month_name']}</h2>
    <div class="{profit_color} text-xl font-bold">{summary['total_profit']:+,.0f} JPY</div>
  </div>
  <div class="grid grid-cols-7 gap-1">
"""
        # ヘッダー
        for day_name in calendar_data["weekday_headers"]:
            html += f'    <div class="text-center text-sm font-medium text-gray-500 py-2">{day_name}</div>\n'

        # セル
        for week in calendar_data["weeks"]:
            for cell in week:
                css = cell["css_class"]
                day = cell["day"]
                pnl = cell.get("pnl")
                pnl_text = f'<div class="text-xs">{pnl["profit"]:+,.0f}</div>' if pnl else ""
                html += f'    <div class="p-2 min-h-[60px] rounded {css}">\n'
                html += f'      <div class="text-sm font-medium">{day}</div>\n'
                html += f'      {pnl_text}\n'
                html += f'    </div>\n'

        html += """  </div>
</div>"""
        return html


# テスト実行
if __name__ == "__main__":
    import random
    random.seed(42)

    service = PnLCalendarService()

    # サンプルデータ生成（2026年2月）
    print("=== サンプルデータ投入 ===")
    for day in range(1, 29):
        d = date(2026, 2, day)
        if d.weekday() < 5:  # 平日のみ
            trades = random.randint(5, 15)
            wins = random.randint(2, trades)
            losses = trades - wins
            profit = random.randint(-25000, 35000)
            pnl = DayPnL(
                date=d.strftime("%Y-%m-%d"),
                profit=profit,
                trades=trades,
                wins=wins,
                losses=losses,
                win_rate=(wins / trades * 100) if trades > 0 else 0,
                best_trade=random.randint(5000, 15000),
                worst_trade=random.randint(-15000, -3000),
            )
            service.add_daily_pnl("user_001", pnl)
    print(f"  投入日数: {len(service.pnl_data.get('user_001', {}))}")

    # 月次カレンダー
    print("\n=== 月次カレンダー (2026年2月) ===")
    cal_data = service.get_monthly_calendar("user_001", 2026, 2)
    summary = cal_data["summary"]
    print(f"  月間損益: {summary['total_profit']:+,.0f} JPY")
    print(f"  取引日数: {summary['trading_days']}")
    print(f"  勝率: {summary['win_rate']:.1f}%")
    print(f"  勝ち日/負け日: {summary['profitable_days']}/{summary['losing_days']}")
    print(f"  平均日次損益: {summary['avg_daily_profit']:+,.0f} JPY")
    print(f"  週数: {len(cal_data['weeks'])}")

    # カレンダー表示
    print("\n  カレンダー:")
    print(f"  {'  '.join(cal_data['weekday_headers'])}")
    for week in cal_data["weeks"]:
        row = []
        for cell in week:
            if not cell["is_current_month"]:
                row.append("  --")
            elif cell["has_data"]:
                p = cell["pnl"]["profit"]
                sign = "+" if p >= 0 else ""
                row.append(f"{sign}{p//1000:>3}k")
            else:
                row.append(f"  {cell['day']:>2}")
        print(f"  {'  '.join(row)}")

    # 週次カレンダー
    print("\n=== 週次カレンダー (2026年 第7週) ===")
    week_data = service.get_weekly_calendar("user_001", 2026, 7)
    print(f"  期間: {week_data['start_date']} - {week_data['end_date']}")
    print(f"  週間損益: {week_data['summary']['total_profit']:+,.0f} JPY")
    for day in week_data["days"]:
        pnl_str = f"{day['pnl']['profit']:+,.0f}" if day["has_data"] else "---"
        print(f"    {day['weekday']} {day['date']}: {pnl_str}")

    # ストリーク情報
    print("\n=== ストリーク情報 ===")
    streak = service.get_streak_info("user_001")
    print(f"  現在のストリーク: {streak['current_streak']} ({streak['streak_type']})")
    print(f"  最大連勝: {streak['max_win_streak']}")
    print(f"  最大連敗: {streak['max_loss_streak']}")

    print("\n✓ 損益カレンダービューサービス テスト完了")
