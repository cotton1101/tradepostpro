"""
PDFレポート自動生成サービス
週次・月次のトレードレポートをPDFで自動生成
"""

from __future__ import annotations

import io
import os
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False
    FPDF = None  # type: ignore


class ReportPeriod(Enum):
    """レポート期間"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


@dataclass
class ReportConfig:
    """レポート設定"""
    period: ReportPeriod
    start_date: str
    end_date: str
    include_charts: bool = True
    include_trade_details: bool = True
    include_sns_stats: bool = True
    include_recommendations: bool = True
    language: str = "ja"
    branding: dict = field(default_factory=dict)


@dataclass
class TradeData:
    """レポート用取引データ"""
    date: str
    profit: float
    trades: int
    wins: int
    losses: int
    win_rate: float
    currency_pairs: dict = field(default_factory=dict)


class PDFReportService:
    """PDFレポート生成サービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.output_dir = self.config.get("output_dir", "/tmp/reports")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_report(self, user_id: str, report_config: ReportConfig, trade_data: List[TradeData]) -> dict:
        """PDFレポートを生成"""
        if not HAS_FPDF:
            return {"success": False, "error": "fpdf2 library not installed"}

        try:
            pdf = self._create_pdf(user_id, report_config, trade_data)
            filename = f"trade_report_{user_id}_{report_config.period.value}_{report_config.start_date.replace('-', '')}.pdf"
            filepath = os.path.join(self.output_dir, filename)
            pdf.output(filepath)

            return {
                "success": True,
                "filepath": filepath,
                "filename": filename,
                "period": report_config.period.value,
                "start_date": report_config.start_date,
                "end_date": report_config.end_date,
                "pages": pdf.page,
                "file_size": os.path.getsize(filepath),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _create_pdf(self, user_id: str, config: ReportConfig, data: List[TradeData]) -> FPDF:
        """PDFドキュメントを作成"""
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.set_auto_page_break(auto=True, margin=15)

        # フォント設定（日本語対応）
        font_path = "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"
        if os.path.exists(font_path):
            pdf.add_font("IPAGothic", "", font_path, uni=True)
            pdf.add_font("IPAGothic", "B", font_path, uni=True)
            default_font = "IPAGothic"
        else:
            default_font = "Helvetica"

        # 集計データ計算
        summary = self._calculate_summary(data)

        # ===== 表紙 =====
        pdf.add_page()
        self._render_cover_page(pdf, config, summary, default_font)

        # ===== サマリーページ =====
        pdf.add_page()
        self._render_summary_page(pdf, config, summary, default_font)

        # ===== 日別詳細ページ =====
        if config.include_trade_details and data:
            pdf.add_page()
            self._render_daily_details(pdf, data, default_font)

        # ===== SNS統計ページ =====
        if config.include_sns_stats:
            pdf.add_page()
            self._render_sns_stats(pdf, default_font)

        # ===== 推奨事項ページ =====
        if config.include_recommendations:
            pdf.add_page()
            self._render_recommendations(pdf, summary, default_font)

        return pdf

    def _calculate_summary(self, data: List[TradeData]) -> dict:
        """データの集計"""
        if not data:
            return {
                "total_profit": 0, "total_trades": 0, "total_wins": 0,
                "total_losses": 0, "win_rate": 0, "trading_days": 0,
                "avg_daily_profit": 0, "max_profit": 0, "max_loss": 0,
                "profitable_days": 0, "losing_days": 0, "best_day": "",
                "worst_day": "", "profit_factor": 0,
            }

        total_profit = sum(d.profit for d in data)
        total_trades = sum(d.trades for d in data)
        total_wins = sum(d.wins for d in data)
        total_losses = sum(d.losses for d in data)
        trading_days = len(data)
        profitable_days = sum(1 for d in data if d.profit > 0)
        losing_days = sum(1 for d in data if d.profit < 0)

        profits = [d.profit for d in data if d.profit > 0]
        losses = [abs(d.profit) for d in data if d.profit < 0]
        gross_profit = sum(profits) if profits else 0
        gross_loss = sum(losses) if losses else 1

        best_day_data = max(data, key=lambda d: d.profit)
        worst_day_data = min(data, key=lambda d: d.profit)

        return {
            "total_profit": total_profit,
            "total_trades": total_trades,
            "total_wins": total_wins,
            "total_losses": total_losses,
            "win_rate": (total_wins / total_trades * 100) if total_trades > 0 else 0,
            "trading_days": trading_days,
            "avg_daily_profit": total_profit / trading_days if trading_days > 0 else 0,
            "max_profit": best_day_data.profit,
            "max_loss": worst_day_data.profit,
            "profitable_days": profitable_days,
            "losing_days": losing_days,
            "best_day": best_day_data.date,
            "worst_day": worst_day_data.date,
            "profit_factor": gross_profit / gross_loss if gross_loss > 0 else 0,
        }

    def _render_cover_page(self, pdf: FPDF, config: ReportConfig, summary: dict, font: str):
        """表紙を描画"""
        # 背景色
        pdf.set_fill_color(26, 26, 46)
        pdf.rect(0, 0, 210, 297, 'F')

        # タイトル
        pdf.set_text_color(255, 255, 255)
        pdf.set_font(font, 'B', 28)
        pdf.set_y(80)
        pdf.cell(0, 15, "TRADE REPORT", ln=True, align='C')

        # 期間
        period_map = {
            ReportPeriod.DAILY: "Daily",
            ReportPeriod.WEEKLY: "Weekly",
            ReportPeriod.MONTHLY: "Monthly",
            ReportPeriod.QUARTERLY: "Quarterly",
        }
        pdf.set_font(font, '', 16)
        pdf.set_text_color(150, 150, 200)
        pdf.cell(0, 10, f"{period_map.get(config.period, 'Custom')} Report", ln=True, align='C')

        # 日付範囲
        pdf.set_y(120)
        pdf.set_font(font, '', 14)
        pdf.set_text_color(200, 200, 220)
        pdf.cell(0, 8, f"{config.start_date}  -  {config.end_date}", ln=True, align='C')

        # サマリーハイライト
        pdf.set_y(160)
        pdf.set_font(font, 'B', 36)
        color = (100, 255, 100) if summary["total_profit"] >= 0 else (255, 100, 100)
        pdf.set_text_color(*color)
        pdf.cell(0, 20, f"{summary['total_profit']:+,.0f} JPY", ln=True, align='C')

        pdf.set_font(font, '', 12)
        pdf.set_text_color(180, 180, 200)
        pdf.cell(0, 8, f"Win Rate: {summary['win_rate']:.1f}%  |  Trades: {summary['total_trades']}", ln=True, align='C')

        # フッター
        pdf.set_y(260)
        pdf.set_font(font, '', 10)
        pdf.set_text_color(100, 100, 130)
        pdf.cell(0, 6, "Generated by TradePost Pro", ln=True, align='C')
        pdf.cell(0, 6, datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"), ln=True, align='C')

    def _render_summary_page(self, pdf: FPDF, config: ReportConfig, summary: dict, font: str):
        """サマリーページを描画"""
        pdf.set_text_color(30, 30, 50)
        pdf.set_font(font, 'B', 20)
        pdf.cell(0, 12, "Performance Summary", ln=True)
        pdf.ln(5)

        # サマリーテーブル
        metrics = [
            ("Total P&L", f"{summary['total_profit']:+,.0f} JPY"),
            ("Total Trades", f"{summary['total_trades']}"),
            ("Win Rate", f"{summary['win_rate']:.1f}%"),
            ("Wins / Losses", f"{summary['total_wins']} / {summary['total_losses']}"),
            ("Trading Days", f"{summary['trading_days']}"),
            ("Avg Daily P&L", f"{summary['avg_daily_profit']:+,.0f} JPY"),
            ("Best Day", f"{summary['best_day']} ({summary['max_profit']:+,.0f} JPY)"),
            ("Worst Day", f"{summary['worst_day']} ({summary['max_loss']:+,.0f} JPY)"),
            ("Profitable Days", f"{summary['profitable_days']} / {summary['trading_days']}"),
            ("Profit Factor", f"{summary['profit_factor']:.2f}"),
        ]

        pdf.set_font(font, '', 11)
        for i, (label, value) in enumerate(metrics):
            if i % 2 == 0:
                pdf.set_fill_color(240, 240, 250)
            else:
                pdf.set_fill_color(255, 255, 255)
            pdf.cell(90, 8, f"  {label}", border=1, fill=True)
            pdf.cell(90, 8, f"  {value}", border=1, fill=True, ln=True)

    def _render_daily_details(self, pdf: FPDF, data: List[TradeData], font: str):
        """日別詳細を描画"""
        pdf.set_text_color(30, 30, 50)
        pdf.set_font(font, 'B', 20)
        pdf.cell(0, 12, "Daily Details", ln=True)
        pdf.ln(5)

        # テーブルヘッダー
        pdf.set_font(font, 'B', 9)
        pdf.set_fill_color(79, 70, 229)
        pdf.set_text_color(255, 255, 255)
        headers = ["Date", "P&L", "Trades", "Wins", "Losses", "Win Rate"]
        widths = [35, 35, 25, 25, 25, 35]
        for header, width in zip(headers, widths):
            pdf.cell(width, 8, header, border=1, fill=True, align='C')
        pdf.ln()

        # テーブルボディ
        pdf.set_font(font, '', 9)
        for i, trade in enumerate(data):
            if i % 2 == 0:
                pdf.set_fill_color(245, 245, 255)
            else:
                pdf.set_fill_color(255, 255, 255)

            pdf.set_text_color(30, 30, 50)
            pdf.cell(35, 7, trade.date, border=1, fill=True, align='C')

            # P&L色分け
            if trade.profit >= 0:
                pdf.set_text_color(0, 150, 0)
            else:
                pdf.set_text_color(200, 0, 0)
            pdf.cell(35, 7, f"{trade.profit:+,.0f}", border=1, fill=True, align='R')

            pdf.set_text_color(30, 30, 50)
            pdf.cell(25, 7, str(trade.trades), border=1, fill=True, align='C')
            pdf.cell(25, 7, str(trade.wins), border=1, fill=True, align='C')
            pdf.cell(25, 7, str(trade.losses), border=1, fill=True, align='C')
            pdf.cell(35, 7, f"{trade.win_rate:.1f}%", border=1, fill=True, align='C')
            pdf.ln()

    def _render_sns_stats(self, pdf: FPDF, font: str):
        """SNS統計を描画"""
        pdf.set_text_color(30, 30, 50)
        pdf.set_font(font, 'B', 20)
        pdf.cell(0, 12, "SNS Performance", ln=True)
        pdf.ln(5)

        # サンプルSNS統計
        sns_data = [
            ("X (Twitter)", "45", "1,250", "320", "15,800"),
            ("Instagram", "30", "890", "180", "8,500"),
            ("TikTok", "20", "2,100", "450", "25,000"),
            ("Threads", "25", "340", "85", "4,200"),
            ("LINE", "45", "-", "-", "500"),
        ]

        pdf.set_font(font, 'B', 9)
        pdf.set_fill_color(79, 70, 229)
        pdf.set_text_color(255, 255, 255)
        sns_headers = ["Platform", "Posts", "Likes", "Comments", "Impressions"]
        sns_widths = [36, 36, 36, 36, 36]
        for header, width in zip(sns_headers, sns_widths):
            pdf.cell(width, 8, header, border=1, fill=True, align='C')
        pdf.ln()

        pdf.set_font(font, '', 9)
        pdf.set_text_color(30, 30, 50)
        for i, (platform, posts, likes, comments, impressions) in enumerate(sns_data):
            fill_color = (245, 245, 255) if i % 2 == 0 else (255, 255, 255)
            pdf.set_fill_color(*fill_color)
            pdf.cell(36, 7, platform, border=1, fill=True, align='C')
            pdf.cell(36, 7, posts, border=1, fill=True, align='C')
            pdf.cell(36, 7, likes, border=1, fill=True, align='C')
            pdf.cell(36, 7, comments, border=1, fill=True, align='C')
            pdf.cell(36, 7, impressions, border=1, fill=True, align='C')
            pdf.ln()

    def _render_recommendations(self, pdf: FPDF, summary: dict, font: str):
        """推奨事項を描画"""
        pdf.set_text_color(30, 30, 50)
        pdf.set_font(font, 'B', 20)
        pdf.cell(0, 12, "Recommendations", ln=True)
        pdf.ln(5)

        recommendations = []

        if summary["win_rate"] < 50:
            recommendations.append("Win rate is below 50%. Consider reviewing entry criteria and risk management.")
        if summary["profit_factor"] < 1.5:
            recommendations.append("Profit factor could be improved. Focus on letting winners run and cutting losses early.")
        if summary["trading_days"] < 15:
            recommendations.append("Limited trading days in this period. Consistency is key to long-term success.")
        if summary["max_loss"] < -50000:
            recommendations.append("Large single-day loss detected. Consider implementing stricter daily loss limits.")

        if not recommendations:
            recommendations.append("Great performance! Keep maintaining your current strategy and risk management.")
            recommendations.append("Consider diversifying across more currency pairs for additional opportunities.")

        recommendations.append("Continue posting results on SNS to build your trading community.")
        recommendations.append("Review your posting schedule to maximize engagement during peak hours.")

        pdf.set_font(font, '', 11)
        for i, rec in enumerate(recommendations, 1):
            pdf.set_fill_color(240, 248, 255)
            pdf.multi_cell(0, 8, f"  {i}. {rec}", border=0, fill=True)
            pdf.ln(2)

    def generate_weekly_report(self, user_id: str, trade_data: List[TradeData]) -> dict:
        """週次レポートを生成"""
        if not trade_data:
            return {"success": False, "error": "No trade data available"}

        dates = [d.date for d in trade_data]
        config = ReportConfig(
            period=ReportPeriod.WEEKLY,
            start_date=min(dates),
            end_date=max(dates),
        )
        return self.generate_report(user_id, config, trade_data)

    def generate_monthly_report(self, user_id: str, trade_data: List[TradeData]) -> dict:
        """月次レポートを生成"""
        if not trade_data:
            return {"success": False, "error": "No trade data available"}

        dates = [d.date for d in trade_data]
        config = ReportConfig(
            period=ReportPeriod.MONTHLY,
            start_date=min(dates),
            end_date=max(dates),
        )
        return self.generate_report(user_id, config, trade_data)


# テスト実行
if __name__ == "__main__":
    service = PDFReportService({"output_dir": "/tmp/reports"})

    # サンプルデータ
    sample_data = []
    import random
    random.seed(42)
    for i in range(20):
        day = 20 - i
        trades = random.randint(5, 15)
        wins = random.randint(3, trades)
        losses = trades - wins
        profit = random.randint(-20000, 30000)
        sample_data.append(TradeData(
            date=f"2026-02-{day:02d}",
            profit=profit,
            trades=trades,
            wins=wins,
            losses=losses,
            win_rate=(wins / trades * 100) if trades > 0 else 0,
        ))

    print("=== 週次レポート生成 ===")
    result = service.generate_weekly_report("user_001", sample_data[:7])
    print(f"  成功: {result['success']}")
    if result['success']:
        print(f"  ファイル: {result['filepath']}")
        print(f"  ページ数: {result['pages']}")
        print(f"  サイズ: {result['file_size']:,} bytes")

    print("\n=== 月次レポート生成 ===")
    result = service.generate_monthly_report("user_001", sample_data)
    print(f"  成功: {result['success']}")
    if result['success']:
        print(f"  ファイル: {result['filepath']}")
        print(f"  ページ数: {result['pages']}")
        print(f"  サイズ: {result['file_size']:,} bytes")
        print(f"  期間: {result['start_date']} - {result['end_date']}")

    print("\n✓ PDFレポート自動生成サービス テスト完了")
