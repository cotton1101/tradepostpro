"""
TradePost Pro - AI最適投稿時間提案サービス
SNSのエンゲージメントデータから最適な投稿時間を学習・提案
"""

import math
import random
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from collections import defaultdict


@dataclass
class EngagementRecord:
    """エンゲージメント記録"""
    platform: str = ""
    posted_at: datetime = field(default_factory=datetime.now)
    hour: int = 0
    day_of_week: int = 0  # 0=月曜, 6=日曜
    impressions: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0


@dataclass
class TimeRecommendation:
    """投稿時間の推奨"""
    platform: str = ""
    recommended_hour: int = 7
    recommended_minute: int = 0
    recommended_days: List[str] = field(default_factory=list)
    confidence: float = 0.0
    avg_engagement_rate: float = 0.0
    reason: str = ""


class OptimalTimeService:
    """AI最適投稿時間提案サービス"""

    DAY_NAMES_JA = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]

    # プラットフォームごとのデフォルト最適時間（業界データに基づく）
    DEFAULT_OPTIMAL_HOURS = {
        "x": {
            "weekday": [7, 8, 12, 17, 18, 21, 22],
            "weekend": [9, 10, 11, 14, 15, 20, 21],
        },
        "instagram": {
            "weekday": [7, 8, 11, 12, 17, 18, 19],
            "weekend": [9, 10, 11, 14, 15, 16],
        },
        "threads": {
            "weekday": [7, 8, 12, 18, 19, 21],
            "weekend": [9, 10, 14, 15, 20],
        },
        "tiktok": {
            "weekday": [7, 8, 12, 15, 19, 20, 21, 22],
            "weekend": [10, 11, 14, 15, 19, 20, 21],
        },
        "line": {
            "weekday": [7, 8, 12, 18, 19, 20, 21],
            "weekend": [9, 10, 11, 14, 18, 19, 20],
        },
    }

    # FXトレーダー向けの特別な時間帯
    FX_TRADER_HOURS = {
        "market_open_tokyo": 9,
        "market_open_london": 16,
        "market_open_ny": 22,
        "market_close_tokyo": 15,
        "pre_market_morning": 7,
        "post_market_evening": 18,
    }

    def __init__(self):
        self.engagement_history: List[EngagementRecord] = []

    # ============================================================
    # データ収集
    # ============================================================

    def add_engagement_record(self, record: EngagementRecord) -> None:
        """エンゲージメント記録を追加"""
        if record.impressions > 0:
            record.engagement_rate = (
                (record.likes + record.comments + record.shares + record.clicks)
                / record.impressions
            ) * 100
        self.engagement_history.append(record)

    def import_engagement_data(self, data: List[Dict]) -> int:
        """エンゲージメントデータを一括インポート"""
        count = 0
        for item in data:
            record = EngagementRecord(
                platform=item.get("platform", ""),
                posted_at=datetime.fromisoformat(item["posted_at"]) if "posted_at" in item else datetime.now(),
                hour=item.get("hour", 0),
                day_of_week=item.get("day_of_week", 0),
                impressions=item.get("impressions", 0),
                likes=item.get("likes", 0),
                comments=item.get("comments", 0),
                shares=item.get("shares", 0),
                clicks=item.get("clicks", 0),
            )
            self.add_engagement_record(record)
            count += 1
        return count

    # ============================================================
    # 分析・学習
    # ============================================================

    def _analyze_by_hour(self, platform: str) -> Dict[int, float]:
        """時間帯別のエンゲージメント率を分析"""
        hour_data = defaultdict(list)

        for record in self.engagement_history:
            if record.platform == platform:
                hour_data[record.hour].append(record.engagement_rate)

        hour_avg = {}
        for hour, rates in hour_data.items():
            hour_avg[hour] = sum(rates) / len(rates) if rates else 0.0

        return hour_avg

    def _analyze_by_day(self, platform: str) -> Dict[int, float]:
        """曜日別のエンゲージメント率を分析"""
        day_data = defaultdict(list)

        for record in self.engagement_history:
            if record.platform == platform:
                day_data[record.day_of_week].append(record.engagement_rate)

        day_avg = {}
        for day, rates in day_data.items():
            day_avg[day] = sum(rates) / len(rates) if rates else 0.0

        return day_avg

    def _analyze_by_hour_and_day(self, platform: str) -> Dict[Tuple[int, int], float]:
        """時間帯×曜日のエンゲージメント率を分析"""
        combo_data = defaultdict(list)

        for record in self.engagement_history:
            if record.platform == platform:
                key = (record.hour, record.day_of_week)
                combo_data[key].append(record.engagement_rate)

        combo_avg = {}
        for key, rates in combo_data.items():
            combo_avg[key] = sum(rates) / len(rates) if rates else 0.0

        return combo_avg

    # ============================================================
    # 推奨時間の算出
    # ============================================================

    def recommend_time(self, platform: str, user_timezone: str = "Asia/Tokyo") -> TimeRecommendation:
        """最適な投稿時間を推奨"""
        platform_records = [r for r in self.engagement_history if r.platform == platform]

        # データが十分にある場合（30件以上）はデータベース分析
        if len(platform_records) >= 30:
            return self._recommend_from_data(platform)

        # データが少ない場合はデフォルト + FXトレーダー向け最適化
        return self._recommend_default(platform)

    def _recommend_from_data(self, platform: str) -> TimeRecommendation:
        """実データに基づく推奨"""
        hour_avg = self._analyze_by_hour(platform)
        day_avg = self._analyze_by_day(platform)

        # 最もエンゲージメント率が高い時間帯
        if hour_avg:
            best_hour = max(hour_avg, key=hour_avg.get)
            best_rate = hour_avg[best_hour]
        else:
            best_hour = 7
            best_rate = 0.0

        # 最もエンゲージメント率が高い曜日（上位3つ）
        if day_avg:
            sorted_days = sorted(day_avg, key=day_avg.get, reverse=True)
            best_days = sorted_days[:3]
            best_day_names = [self.DAY_NAMES_JA[d] for d in best_days]
        else:
            best_day_names = ["月曜日", "水曜日", "金曜日"]

        # 信頼度の計算（データ量に基づく）
        data_count = len([r for r in self.engagement_history if r.platform == platform])
        confidence = min(1.0, data_count / 100)

        return TimeRecommendation(
            platform=platform,
            recommended_hour=best_hour,
            recommended_minute=0,
            recommended_days=best_day_names,
            confidence=confidence,
            avg_engagement_rate=best_rate,
            reason=f"{data_count}件のエンゲージメントデータに基づく分析結果。{best_hour}時台が最もエンゲージメント率が高い（{best_rate:.2f}%）。",
        )

    def _recommend_default(self, platform: str) -> TimeRecommendation:
        """デフォルトの推奨（FXトレーダー向け最適化）"""
        defaults = self.DEFAULT_OPTIMAL_HOURS.get(platform, self.DEFAULT_OPTIMAL_HOURS["x"])

        # FXトレーダーのターゲット層を考慮
        # 朝の市場前（7-8時）が最も効果的
        best_hour = 7

        # 平日が基本（FX市場は平日のみ）
        best_days = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日"]

        reason = (
            f"FXトレーダー向けの業界データに基づく推奨。"
            f"東京市場オープン前の{best_hour}時台は、トレーダーの情報収集時間帯と重なるため"
            f"高いエンゲージメントが期待できます。"
        )

        return TimeRecommendation(
            platform=platform,
            recommended_hour=best_hour,
            recommended_minute=0,
            recommended_days=best_days,
            confidence=0.5,
            avg_engagement_rate=0.0,
            reason=reason,
        )

    def recommend_all_platforms(self) -> Dict[str, TimeRecommendation]:
        """全プラットフォームの推奨時間を一括取得"""
        platforms = ["x", "instagram", "threads", "tiktok", "line"]
        return {p: self.recommend_time(p) for p in platforms}

    # ============================================================
    # スケジュール最適化
    # ============================================================

    def optimize_schedule(
        self,
        platforms: List[str],
        min_interval_minutes: int = 15,
    ) -> List[Dict]:
        """複数プラットフォームの投稿スケジュールを最適化（間隔を空ける）"""
        recommendations = {p: self.recommend_time(p) for p in platforms}

        # 推奨時間でソート
        sorted_platforms = sorted(
            recommendations.items(),
            key=lambda x: x[1].recommended_hour,
        )

        schedule = []
        last_time = None

        for platform, rec in sorted_platforms:
            proposed_time = datetime.now().replace(
                hour=rec.recommended_hour,
                minute=rec.recommended_minute,
                second=0,
                microsecond=0,
            )

            # 前の投稿との間隔を確保
            if last_time and (proposed_time - last_time).total_seconds() < min_interval_minutes * 60:
                proposed_time = last_time + timedelta(minutes=min_interval_minutes)

            schedule.append({
                "platform": platform,
                "time": proposed_time.strftime("%H:%M"),
                "hour": proposed_time.hour,
                "minute": proposed_time.minute,
                "confidence": rec.confidence,
                "reason": rec.reason,
            })

            last_time = proposed_time

        return schedule

    # ============================================================
    # レポート生成
    # ============================================================

    def generate_report(self, platform: str) -> Dict:
        """投稿時間分析レポートを生成"""
        rec = self.recommend_time(platform)
        hour_avg = self._analyze_by_hour(platform)
        day_avg = self._analyze_by_day(platform)

        # 時間帯別のヒートマップデータ
        heatmap = {}
        for hour in range(24):
            heatmap[f"{hour:02d}:00"] = hour_avg.get(hour, 0.0)

        # 曜日別データ
        day_data = {}
        for day in range(7):
            day_data[self.DAY_NAMES_JA[day]] = day_avg.get(day, 0.0)

        return {
            "platform": platform,
            "recommendation": {
                "hour": rec.recommended_hour,
                "minute": rec.recommended_minute,
                "days": rec.recommended_days,
                "confidence": rec.confidence,
                "reason": rec.reason,
            },
            "hourly_engagement": heatmap,
            "daily_engagement": day_data,
            "total_records": len([r for r in self.engagement_history if r.platform == platform]),
        }


# テスト用
if __name__ == "__main__":
    service = OptimalTimeService()

    # サンプルデータ生成
    print("=== サンプルデータ生成 ===")
    sample_data = []
    for _ in range(50):
        hour = random.choice([7, 8, 12, 17, 18, 21, 22])
        day = random.randint(0, 6)
        impressions = random.randint(100, 5000)
        likes = random.randint(5, int(impressions * 0.1))
        sample_data.append({
            "platform": "x",
            "hour": hour,
            "day_of_week": day,
            "impressions": impressions,
            "likes": likes,
            "comments": random.randint(0, 10),
            "shares": random.randint(0, 5),
            "clicks": random.randint(0, 50),
        })

    imported = service.import_engagement_data(sample_data)
    print(f"インポート: {imported}件")

    # 推奨時間
    print("\n=== 推奨投稿時間 ===")
    for platform in ["x", "instagram", "threads", "tiktok", "line"]:
        rec = service.recommend_time(platform)
        print(f"[{platform}] {rec.recommended_hour}:{rec.recommended_minute:02d} "
              f"(信頼度: {rec.confidence:.0%}) - {rec.reason[:60]}...")

    # スケジュール最適化
    print("\n=== 最適化スケジュール ===")
    schedule = service.optimize_schedule(["x", "instagram", "threads", "tiktok", "line"])
    for item in schedule:
        print(f"  {item['time']} - {item['platform']} (信頼度: {item['confidence']:.0%})")

    # レポート
    print("\n=== X分析レポート ===")
    report = service.generate_report("x")
    print(f"  データ数: {report['total_records']}件")
    print(f"  推奨: {report['recommendation']['hour']}時")

    print("\n✓ AI最適投稿時間提案サービス テスト完了")
