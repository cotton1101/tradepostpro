"""
TradePost Pro - データエクスポートサービス
取引履歴・投稿履歴をCSV/PDF形式でエクスポート
"""

import csv
import io
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class TradeRecord:
    """取引記録"""
    date: str = ""
    profit: float = 0
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0
    cumulative_profit: float = 0


@dataclass
class PostRecord:
    """投稿記録"""
    date: str = ""
    platform: str = ""
    status: str = ""
    template: str = ""
    text_preview: str = ""
    image_url: str = ""
    error: str = ""


class ExportService:
    """データエクスポートサービス"""

    def __init__(self):
        pass

    # ============================================================
    # CSV エクスポート
    # ============================================================

    def export_trades_csv(self, trades: List[TradeRecord]) -> str:
        """取引履歴をCSVにエクスポート"""
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー
        writer.writerow([
            "日付", "日次損益(¥)", "取引回数", "勝ち", "負け",
            "勝率(%)", "累計損益(¥)"
        ])

        # データ
        for trade in sorted(trades, key=lambda t: t.date):
            writer.writerow([
                trade.date,
                f"{trade.profit:,.0f}",
                trade.total_trades,
                trade.wins,
                trade.losses,
                f"{trade.win_rate:.1f}",
                f"{trade.cumulative_profit:,.0f}",
            ])

        # サマリー行
        if trades:
            total_profit = sum(t.profit for t in trades)
            total_trades = sum(t.total_trades for t in trades)
            total_wins = sum(t.wins for t in trades)
            total_losses = sum(t.losses for t in trades)
            avg_win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0

            writer.writerow([])
            writer.writerow(["=== サマリー ==="])
            writer.writerow(["期間", f"{trades[0].date} 〜 {trades[-1].date}"])
            writer.writerow(["合計損益", f"¥{total_profit:,.0f}"])
            writer.writerow(["合計取引回数", total_trades])
            writer.writerow(["平均勝率", f"{avg_win_rate:.1f}%"])

        return output.getvalue()

    def export_posts_csv(self, posts: List[PostRecord]) -> str:
        """投稿履歴をCSVにエクスポート"""
        output = io.StringIO()
        writer = csv.writer(output)

        # ヘッダー
        writer.writerow([
            "日付", "プラットフォーム", "ステータス", "テンプレート",
            "テキスト（抜粋）", "エラー"
        ])

        # データ
        for post in sorted(posts, key=lambda p: p.date, reverse=True):
            writer.writerow([
                post.date,
                post.platform,
                post.status,
                post.template,
                post.text_preview[:50],
                post.error or "-",
            ])

        # サマリー
        if posts:
            total = len(posts)
            success = sum(1 for p in posts if p.status == "success")
            failed = sum(1 for p in posts if p.status == "failed")

            writer.writerow([])
            writer.writerow(["=== サマリー ==="])
            writer.writerow(["総投稿数", total])
            writer.writerow(["成功", success])
            writer.writerow(["失敗", failed])
            writer.writerow(["成功率", f"{success / total * 100:.1f}%" if total > 0 else "0%"])

        return output.getvalue()

    # ============================================================
    # PDF エクスポート（HTML生成 → WeasyPrint/xhtml2pdf変換用）
    # ============================================================

    def export_trades_pdf_html(self, trades: List[TradeRecord], user_name: str = "ユーザー") -> str:
        """取引履歴のPDF用HTMLを生成"""
        sorted_trades = sorted(trades, key=lambda t: t.date)

        # サマリー計算
        total_profit = sum(t.profit for t in trades) if trades else 0
        total_trades = sum(t.total_trades for t in trades) if trades else 0
        total_wins = sum(t.wins for t in trades) if trades else 0
        total_losses = sum(t.losses for t in trades) if trades else 0
        avg_win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
        profit_color = "#10b981" if total_profit >= 0 else "#ef4444"

        # テーブル行
        rows_html = ""
        for t in sorted_trades:
            p_color = "#10b981" if t.profit >= 0 else "#ef4444"
            rows_html += f"""
            <tr>
                <td>{t.date}</td>
                <td style="color:{p_color};font-weight:bold;">¥{t.profit:,.0f}</td>
                <td>{t.total_trades}</td>
                <td>{t.wins}</td>
                <td>{t.losses}</td>
                <td>{t.win_rate:.1f}%</td>
                <td>¥{t.cumulative_profit:,.0f}</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<style>
    body {{ font-family: 'Noto Sans JP', sans-serif; margin: 40px; color: #333; }}
    h1 {{ color: #1e293b; border-bottom: 3px solid #4f46e5; padding-bottom: 10px; }}
    .header {{ display: flex; justify-content: space-between; margin-bottom: 30px; }}
    .summary {{ background: #f8fafc; border-radius: 8px; padding: 20px; margin-bottom: 30px; }}
    .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; }}
    .summary-item {{ text-align: center; }}
    .summary-item .label {{ color: #64748b; font-size: 12px; }}
    .summary-item .value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #1e293b; color: white; padding: 10px 8px; text-align: left; }}
    td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; }}
    tr:nth-child(even) {{ background: #f8fafc; }}
    .footer {{ margin-top: 30px; text-align: center; color: #94a3b8; font-size: 11px; }}
</style>
</head>
<body>
    <h1>TradePost Pro - 取引レポート</h1>
    <div class="header">
        <div>ユーザー: {user_name}</div>
        <div>出力日: {datetime.now().strftime('%Y年%m月%d日')}</div>
    </div>

    <div class="summary">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="label">合計損益</div>
                <div class="value" style="color:{profit_color}">¥{total_profit:,.0f}</div>
            </div>
            <div class="summary-item">
                <div class="label">取引回数</div>
                <div class="value">{total_trades}</div>
            </div>
            <div class="summary-item">
                <div class="label">勝敗</div>
                <div class="value">{total_wins}勝 {total_losses}敗</div>
            </div>
            <div class="summary-item">
                <div class="label">平均勝率</div>
                <div class="value">{avg_win_rate:.1f}%</div>
            </div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>日付</th><th>日次損益</th><th>取引回数</th>
                <th>勝ち</th><th>負け</th><th>勝率</th><th>累計損益</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <div class="footer">
        TradePost Pro | {datetime.now().strftime('%Y-%m-%d %H:%M')} 生成
    </div>
</body>
</html>"""
        return html

    def export_posts_pdf_html(self, posts: List[PostRecord], user_name: str = "ユーザー") -> str:
        """投稿履歴のPDF用HTMLを生成"""
        sorted_posts = sorted(posts, key=lambda p: p.date, reverse=True)

        total = len(posts)
        success = sum(1 for p in posts if p.status == "success")
        failed = sum(1 for p in posts if p.status == "failed")
        success_rate = success / total * 100 if total > 0 else 0

        rows_html = ""
        for p in sorted_posts:
            status_color = "#10b981" if p.status == "success" else "#ef4444" if p.status == "failed" else "#f59e0b"
            rows_html += f"""
            <tr>
                <td>{p.date}</td>
                <td>{p.platform}</td>
                <td style="color:{status_color};font-weight:bold;">{p.status}</td>
                <td>{p.template}</td>
                <td>{p.text_preview[:40]}...</td>
            </tr>"""

        html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<style>
    body {{ font-family: 'Noto Sans JP', sans-serif; margin: 40px; color: #333; }}
    h1 {{ color: #1e293b; border-bottom: 3px solid #4f46e5; padding-bottom: 10px; }}
    .summary {{ background: #f8fafc; border-radius: 8px; padding: 20px; margin-bottom: 30px; display: flex; gap: 30px; }}
    .stat {{ text-align: center; }}
    .stat .label {{ color: #64748b; font-size: 12px; }}
    .stat .value {{ font-size: 24px; font-weight: bold; margin-top: 5px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th {{ background: #1e293b; color: white; padding: 10px 8px; text-align: left; }}
    td {{ padding: 8px; border-bottom: 1px solid #e2e8f0; }}
    tr:nth-child(even) {{ background: #f8fafc; }}
    .footer {{ margin-top: 30px; text-align: center; color: #94a3b8; font-size: 11px; }}
</style>
</head>
<body>
    <h1>TradePost Pro - 投稿履歴レポート</h1>
    <p>ユーザー: {user_name} | 出力日: {datetime.now().strftime('%Y年%m月%d日')}</p>

    <div class="summary">
        <div class="stat"><div class="label">総投稿数</div><div class="value">{total}</div></div>
        <div class="stat"><div class="label">成功</div><div class="value" style="color:#10b981">{success}</div></div>
        <div class="stat"><div class="label">失敗</div><div class="value" style="color:#ef4444">{failed}</div></div>
        <div class="stat"><div class="label">成功率</div><div class="value">{success_rate:.1f}%</div></div>
    </div>

    <table>
        <thead><tr><th>日付</th><th>SNS</th><th>ステータス</th><th>テンプレート</th><th>テキスト</th></tr></thead>
        <tbody>{rows_html}</tbody>
    </table>

    <div class="footer">TradePost Pro | {datetime.now().strftime('%Y-%m-%d %H:%M')} 生成</div>
</body>
</html>"""
        return html

    # ============================================================
    # JSON エクスポート
    # ============================================================

    def export_trades_json(self, trades: List[TradeRecord]) -> str:
        """取引履歴をJSONにエクスポート"""
        data = {
            "exported_at": datetime.now().isoformat(),
            "total_records": len(trades),
            "records": [
                {
                    "date": t.date,
                    "profit": t.profit,
                    "total_trades": t.total_trades,
                    "wins": t.wins,
                    "losses": t.losses,
                    "win_rate": t.win_rate,
                    "cumulative_profit": t.cumulative_profit,
                }
                for t in sorted(trades, key=lambda t: t.date)
            ]
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# テスト用
if __name__ == "__main__":
    import random

    service = ExportService()

    # サンプル取引データ
    trades = []
    cumulative = 0
    base_date = datetime.now() - timedelta(days=30)
    for i in range(30):
        date = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        profit = random.randint(-15000, 25000)
        total = random.randint(5, 20)
        wins = random.randint(0, total)
        losses = total - wins
        cumulative += profit
        trades.append(TradeRecord(
            date=date, profit=profit, total_trades=total,
            wins=wins, losses=losses,
            win_rate=round(wins / total * 100, 1) if total > 0 else 0,
            cumulative_profit=cumulative,
        ))

    # CSV出力テスト
    csv_data = service.export_trades_csv(trades)
    print(f"CSV出力: {len(csv_data)}文字")
    print(csv_data[:500])

    # PDF HTML出力テスト
    html = service.export_trades_pdf_html(trades, "テストユーザー")
    print(f"\nPDF HTML出力: {len(html)}文字")

    # JSON出力テスト
    json_data = service.export_trades_json(trades)
    print(f"\nJSON出力: {len(json_data)}文字")

    # 投稿履歴テスト
    posts = []
    platforms = ["x", "instagram", "threads", "tiktok", "line"]
    for i in range(50):
        date = (base_date + timedelta(days=i % 30)).strftime("%Y-%m-%d")
        posts.append(PostRecord(
            date=date,
            platform=random.choice(platforms),
            status=random.choice(["success", "success", "success", "failed"]),
            template="dark_classic",
            text_preview="本日のFXトレード結果をお知らせします",
        ))

    posts_csv = service.export_posts_csv(posts)
    print(f"\n投稿CSV出力: {len(posts_csv)}文字")

    print("\n✓ エクスポートサービス テスト完了")
