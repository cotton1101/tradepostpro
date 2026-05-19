"""
TradePost Pro - 週次・月次レポート生成モジュール
日次データを集計して週次/月次のサマリーレポートを生成する
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
FONT_BOLD = os.path.join(ASSETS_DIR, "fonts", "NotoSansJP-Bold.otf")
FONT_REGULAR = os.path.join(ASSETS_DIR, "fonts", "NotoSansJP-Regular.otf")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")


@dataclass
class DailyRecord:
    """日次レコード"""
    date: str
    net_profit: float
    total_trades: int
    winning_trades: int
    losing_trades: int


@dataclass
class PeriodReport:
    """期間レポート"""
    period_type: str  # "weekly" or "monthly"
    start_date: str
    end_date: str
    total_net_profit: float
    total_trades: int
    total_wins: int
    total_losses: int
    win_rate: float
    trading_days: int
    best_day: Optional[Tuple[str, float]] = None  # (date, profit)
    worst_day: Optional[Tuple[str, float]] = None  # (date, profit)
    average_daily: float = 0.0
    daily_records: List[DailyRecord] = field(default_factory=list)
    cumulative_profit: float = 0.0


class PeriodicReportGenerator:
    """週次・月次レポート生成器"""

    def __init__(self, data_store_path: Optional[str] = None):
        self.data_store_path = data_store_path or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "data", "daily_records.json"
        )
        self._records: List[DailyRecord] = []
        self._load_records()

    def _load_records(self):
        """保存済みの日次レコードを読み込み"""
        if os.path.exists(self.data_store_path):
            try:
                with open(self.data_store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._records = [DailyRecord(**r) for r in data]
                logger.info(f"{len(self._records)}件の日次レコードを読み込みました")
            except Exception as e:
                logger.error(f"日次レコードの読み込みに失敗: {e}")
                self._records = []

    def save_records(self):
        """日次レコードを保存"""
        os.makedirs(os.path.dirname(self.data_store_path), exist_ok=True)
        data = [
            {
                "date": r.date,
                "net_profit": r.net_profit,
                "total_trades": r.total_trades,
                "winning_trades": r.winning_trades,
                "losing_trades": r.losing_trades,
            }
            for r in self._records
        ]
        with open(self.data_store_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"{len(self._records)}件の日次レコードを保存しました")

    def add_daily_record(self, record: DailyRecord):
        """日次レコードを追加"""
        # 同日のレコードがあれば上書き
        self._records = [r for r in self._records if r.date != record.date]
        self._records.append(record)
        self._records.sort(key=lambda r: r.date)
        self.save_records()

    def generate_weekly_report(self, target_date: Optional[date] = None) -> PeriodReport:
        """週次レポートを生成（月曜〜日曜）"""
        target = target_date or date.today()
        # 直近の月曜日を取得
        monday = target - timedelta(days=target.weekday())
        sunday = monday + timedelta(days=6)

        return self._generate_period_report(
            period_type="weekly",
            start_date=monday,
            end_date=min(sunday, target),
        )

    def generate_monthly_report(self, target_date: Optional[date] = None) -> PeriodReport:
        """月次レポートを生成"""
        target = target_date or date.today()
        first_day = target.replace(day=1)

        return self._generate_period_report(
            period_type="monthly",
            start_date=first_day,
            end_date=target,
        )

    def _generate_period_report(
        self, period_type: str, start_date: date, end_date: date
    ) -> PeriodReport:
        """期間レポートを生成"""
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        # 期間内のレコードを抽出
        period_records = [
            r for r in self._records
            if start_str <= r.date <= end_str
        ]

        if not period_records:
            return PeriodReport(
                period_type=period_type,
                start_date=start_str,
                end_date=end_str,
                total_net_profit=0,
                total_trades=0,
                total_wins=0,
                total_losses=0,
                win_rate=0.0,
                trading_days=0,
                daily_records=[],
            )

        total_profit = sum(r.net_profit for r in period_records)
        total_trades = sum(r.total_trades for r in period_records)
        total_wins = sum(r.winning_trades for r in period_records)
        total_losses = sum(r.losing_trades for r in period_records)
        trading_days = len(period_records)

        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0
        avg_daily = total_profit / trading_days if trading_days > 0 else 0.0

        best = max(period_records, key=lambda r: r.net_profit)
        worst = min(period_records, key=lambda r: r.net_profit)

        # 累計損益を計算
        cumulative = 0
        for r in period_records:
            cumulative += r.net_profit

        return PeriodReport(
            period_type=period_type,
            start_date=start_str,
            end_date=end_str,
            total_net_profit=total_profit,
            total_trades=total_trades,
            total_wins=total_wins,
            total_losses=total_losses,
            win_rate=round(win_rate, 1),
            trading_days=trading_days,
            best_day=(best.date, best.net_profit),
            worst_day=(worst.date, worst.net_profit),
            average_daily=round(avg_daily, 0),
            daily_records=period_records,
            cumulative_profit=cumulative,
        )

    def generate_report_image(
        self,
        report: PeriodReport,
        output_path: Optional[str] = None,
        line_url: str = "",
    ) -> str:
        """レポート画像を生成"""
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        width, height = 1080, 1350
        img = Image.new("RGB", (width, height), "#0d1117")
        draw = ImageDraw.Draw(img)

        # フォント読み込み
        try:
            font_title = ImageFont.truetype(FONT_BOLD, 42)
            font_large = ImageFont.truetype(FONT_BOLD, 56)
            font_medium = ImageFont.truetype(FONT_BOLD, 28)
            font_small = ImageFont.truetype(FONT_REGULAR, 22)
            font_tiny = ImageFont.truetype(FONT_REGULAR, 18)
        except Exception:
            font_title = ImageFont.load_default()
            font_large = font_title
            font_medium = font_title
            font_small = font_title
            font_tiny = font_title

        # ヘッダー背景
        draw.rectangle([(0, 0), (width, 120)], fill="#1a1f2e")

        # タイトル
        if report.period_type == "weekly":
            title = "📊 週次トレードレポート"
        else:
            title = "📊 月次トレードレポート"
        draw.text((40, 35), title, fill="#ffffff", font=font_title)

        # 期間
        period_text = f"{report.start_date} 〜 {report.end_date}"
        draw.text((40, 140), period_text, fill="#8b949e", font=font_medium)

        # メイン損益
        y = 200
        profit_color = "#00d4aa" if report.total_net_profit >= 0 else "#ff4757"
        sign = "+" if report.total_net_profit >= 0 else ""
        profit_text = f"{sign}{report.total_net_profit:,.0f}円"
        draw.text((40, y), "合計損益", fill="#8b949e", font=font_medium)
        draw.text((40, y + 40), profit_text, fill=profit_color, font=font_large)

        # 統計カード
        y = 340
        cards = [
            ("取引日数", f"{report.trading_days}日"),
            ("総取引回数", f"{report.total_trades}回"),
            ("勝率", f"{report.win_rate}%"),
            ("日平均", f"{report.average_daily:+,.0f}円"),
        ]

        card_width = (width - 80 - 30) // 2
        for i, (label, value) in enumerate(cards):
            col = i % 2
            row = i // 2
            cx = 40 + col * (card_width + 30)
            cy = y + row * 120

            draw.rounded_rectangle(
                [(cx, cy), (cx + card_width, cy + 100)],
                radius=12,
                fill="#161b22",
                outline="#30363d",
            )
            draw.text((cx + 20, cy + 15), label, fill="#8b949e", font=font_small)
            draw.text((cx + 20, cy + 50), value, fill="#ffffff", font=font_medium)

        # 勝敗
        y = 600
        draw.rounded_rectangle(
            [(40, y), (width - 40, y + 80)],
            radius=12,
            fill="#161b22",
            outline="#30363d",
        )
        draw.text((60, y + 25), f"🏆 {report.total_wins}勝", fill="#00d4aa", font=font_medium)
        draw.text((300, y + 25), f"💔 {report.total_losses}敗", fill="#ff4757", font=font_medium)

        # ベスト/ワースト
        y = 710
        if report.best_day:
            draw.rounded_rectangle(
                [(40, y), (width // 2 - 15, y + 90)],
                radius=12,
                fill="#0d2818",
                outline="#1a5c30",
            )
            draw.text((60, y + 10), "最高日", fill="#00d4aa", font=font_small)
            draw.text(
                (60, y + 45),
                f"+{report.best_day[1]:,.0f}円",
                fill="#00d4aa",
                font=font_medium,
            )

        if report.worst_day:
            draw.rounded_rectangle(
                [(width // 2 + 15, y), (width - 40, y + 90)],
                radius=12,
                fill="#2d0f0f",
                outline="#5c1a1a",
            )
            draw.text((width // 2 + 35, y + 10), "最低日", fill="#ff4757", font=font_small)
            draw.text(
                (width // 2 + 35, y + 45),
                f"{report.worst_day[1]:,.0f}円",
                fill="#ff4757",
                font=font_medium,
            )

        # 日次損益バーチャート
        y = 830
        draw.text((40, y), "日次損益推移", fill="#8b949e", font=font_medium)
        y += 40

        if report.daily_records:
            max_abs = max(abs(r.net_profit) for r in report.daily_records) or 1
            bar_area_width = width - 160
            bar_height = 20
            max_bars = min(len(report.daily_records), 14)
            records_to_show = report.daily_records[-max_bars:]

            for i, record in enumerate(records_to_show):
                by = y + i * (bar_height + 8)
                if by + bar_height > height - 80:
                    break

                # 日付ラベル
                day_label = record.date[-5:]  # MM-DD
                draw.text((40, by), day_label, fill="#8b949e", font=font_tiny)

                # バー
                bar_len = int(abs(record.net_profit) / max_abs * (bar_area_width // 2))
                center_x = 120 + bar_area_width // 2

                if record.net_profit >= 0:
                    draw.rectangle(
                        [(center_x, by), (center_x + bar_len, by + bar_height)],
                        fill="#00d4aa",
                    )
                else:
                    draw.rectangle(
                        [(center_x - bar_len, by), (center_x, by + bar_height)],
                        fill="#ff4757",
                    )

        # フッター
        draw.rectangle([(0, height - 60), (width, height)], fill="#00d4aa")
        footer = "TradePost Pro"
        if line_url:
            footer += f" | LINEオープンチャット参加はこちら"
        draw.text((40, height - 45), footer, fill="#0d1117", font=font_medium)

        # 保存
        if output_path is None:
            suffix = "weekly" if report.period_type == "weekly" else "monthly"
            output_path = os.path.join(
                OUTPUT_DIR,
                f"trade_{suffix}_{report.end_date}.jpg",
            )

        img.save(output_path, "JPEG", quality=95)
        logger.info(f"レポート画像を生成: {output_path}")
        return output_path


if __name__ == "__main__":
    import random

    # サンプルデータで週次・月次レポートを生成
    generator = PeriodicReportGenerator(
        data_store_path="/tmp/test_daily_records.json"
    )

    # 過去30日分のサンプルデータを生成
    today = date.today()
    for i in range(30):
        d = today - timedelta(days=29 - i)
        if d.weekday() < 5:  # 平日のみ
            profit = random.randint(-20000, 30000)
            wins = random.randint(1, 8)
            losses = random.randint(0, 5)
            generator.add_daily_record(DailyRecord(
                date=d.isoformat(),
                net_profit=profit,
                total_trades=wins + losses,
                winning_trades=wins,
                losing_trades=losses,
            ))

    # 週次レポート
    weekly = generator.generate_weekly_report()
    print(f"=== 週次レポート ===")
    print(f"期間: {weekly.start_date} 〜 {weekly.end_date}")
    print(f"損益: {weekly.total_net_profit:+,.0f}円")
    print(f"取引: {weekly.total_trades}回 ({weekly.total_wins}勝{weekly.total_losses}敗)")
    print(f"勝率: {weekly.win_rate}%")
    print(f"日平均: {weekly.average_daily:+,.0f}円")
    if weekly.best_day:
        print(f"最高日: {weekly.best_day[0]} ({weekly.best_day[1]:+,.0f}円)")
    if weekly.worst_day:
        print(f"最低日: {weekly.worst_day[0]} ({weekly.worst_day[1]:+,.0f}円)")

    weekly_img = generator.generate_report_image(weekly)
    print(f"画像: {weekly_img}")

    # 月次レポート
    monthly = generator.generate_monthly_report()
    print(f"\n=== 月次レポート ===")
    print(f"期間: {monthly.start_date} 〜 {monthly.end_date}")
    print(f"損益: {monthly.total_net_profit:+,.0f}円")
    print(f"取引: {monthly.total_trades}回 ({monthly.total_wins}勝{monthly.total_losses}敗)")
    print(f"勝率: {monthly.win_rate}%")
    print(f"取引日数: {monthly.trading_days}日")

    monthly_img = generator.generate_report_image(monthly)
    print(f"画像: {monthly_img}")
