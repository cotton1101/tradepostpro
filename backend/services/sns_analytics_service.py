"""
TradePost Pro - SNS分析サービス
いいね数、リーチ、フォロワー増減の追跡・分析
"""

import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum


@dataclass
class SnsMetrics:
    """SNSメトリクス（1日分）"""
    date: str = ""
    platform: str = ""
    followers: int = 0
    followers_change: int = 0
    impressions: int = 0
    reach: int = 0
    engagements: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    profile_visits: int = 0
    engagement_rate: float = 0.0


@dataclass
class PostAnalytics:
    """投稿別分析"""
    post_id: str = ""
    platform: str = ""
    posted_at: str = ""
    text_preview: str = ""
    template: str = ""
    impressions: int = 0
    reach: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    clicks: int = 0
    engagement_rate: float = 0.0
    best_performing: bool = False


class SnsAnalyticsService:
    """SNS分析サービス"""

    def __init__(self):
        self.daily_metrics: Dict[str, List[SnsMetrics]] = {}  # user_id -> [metrics]
        self.post_analytics: Dict[str, List[PostAnalytics]] = {}  # user_id -> [analytics]

    # ============================================================
    # メトリクス記録
    # ============================================================

    def record_daily_metrics(self, user_id: str, metrics: SnsMetrics):
        """日次メトリクスを記録"""
        if user_id not in self.daily_metrics:
            self.daily_metrics[user_id] = []
        self.daily_metrics[user_id].append(metrics)

    def record_post_analytics(self, user_id: str, analytics: PostAnalytics):
        """投稿別分析を記録"""
        if user_id not in self.post_analytics:
            self.post_analytics[user_id] = []
        self.post_analytics[user_id].append(analytics)

    # ============================================================
    # ダッシュボード用データ取得
    # ============================================================

    def get_overview(self, user_id: str, days: int = 30) -> Dict:
        """概要データを取得"""
        metrics = self.daily_metrics.get(user_id, [])
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [m for m in metrics if m.date >= cutoff]

        platforms = {}
        for m in recent:
            if m.platform not in platforms:
                platforms[m.platform] = {
                    "total_impressions": 0,
                    "total_engagements": 0,
                    "total_likes": 0,
                    "total_comments": 0,
                    "total_shares": 0,
                    "total_clicks": 0,
                    "follower_change": 0,
                    "latest_followers": 0,
                    "days_tracked": 0,
                }
            p = platforms[m.platform]
            p["total_impressions"] += m.impressions
            p["total_engagements"] += m.engagements
            p["total_likes"] += m.likes
            p["total_comments"] += m.comments
            p["total_shares"] += m.shares
            p["total_clicks"] += m.clicks
            p["follower_change"] += m.followers_change
            p["latest_followers"] = max(p["latest_followers"], m.followers)
            p["days_tracked"] += 1

        # エンゲージメント率計算
        for p_data in platforms.values():
            if p_data["total_impressions"] > 0:
                p_data["avg_engagement_rate"] = round(
                    p_data["total_engagements"] / p_data["total_impressions"] * 100, 2
                )
            else:
                p_data["avg_engagement_rate"] = 0

        total_impressions = sum(p["total_impressions"] for p in platforms.values())
        total_engagements = sum(p["total_engagements"] for p in platforms.values())
        total_followers = sum(p["latest_followers"] for p in platforms.values())

        return {
            "period_days": days,
            "total_impressions": total_impressions,
            "total_engagements": total_engagements,
            "total_followers": total_followers,
            "avg_engagement_rate": round(
                total_engagements / total_impressions * 100, 2
            ) if total_impressions > 0 else 0,
            "platforms": platforms,
        }

    def get_follower_trend(self, user_id: str, platform: str, days: int = 30) -> List[Dict]:
        """フォロワー推移を取得"""
        metrics = self.daily_metrics.get(user_id, [])
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        trend = [
            {"date": m.date, "followers": m.followers, "change": m.followers_change}
            for m in metrics
            if m.platform == platform and m.date >= cutoff
        ]
        return sorted(trend, key=lambda x: x["date"])

    def get_engagement_trend(self, user_id: str, platform: str, days: int = 30) -> List[Dict]:
        """エンゲージメント推移を取得"""
        metrics = self.daily_metrics.get(user_id, [])
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        trend = [
            {
                "date": m.date,
                "impressions": m.impressions,
                "engagements": m.engagements,
                "engagement_rate": m.engagement_rate,
                "likes": m.likes,
                "comments": m.comments,
                "shares": m.shares,
            }
            for m in metrics
            if m.platform == platform and m.date >= cutoff
        ]
        return sorted(trend, key=lambda x: x["date"])

    def get_best_posts(self, user_id: str, platform: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """最もパフォーマンスの良い投稿を取得"""
        analytics = self.post_analytics.get(user_id, [])
        if platform:
            analytics = [a for a in analytics if a.platform == platform]

        sorted_posts = sorted(analytics, key=lambda a: a.engagement_rate, reverse=True)[:limit]

        return [
            {
                "post_id": a.post_id,
                "platform": a.platform,
                "posted_at": a.posted_at,
                "text_preview": a.text_preview,
                "template": a.template,
                "impressions": a.impressions,
                "engagement_rate": a.engagement_rate,
                "likes": a.likes,
                "comments": a.comments,
                "shares": a.shares,
            }
            for a in sorted_posts
        ]

    def get_best_posting_time(self, user_id: str, platform: str) -> Dict:
        """最適な投稿時間を分析"""
        analytics = self.post_analytics.get(user_id, [])
        platform_posts = [a for a in analytics if a.platform == platform]

        hour_stats: Dict[int, Dict] = {}
        for post in platform_posts:
            try:
                hour = datetime.fromisoformat(post.posted_at).hour
            except (ValueError, TypeError):
                continue

            if hour not in hour_stats:
                hour_stats[hour] = {"total_rate": 0, "count": 0}
            hour_stats[hour]["total_rate"] += post.engagement_rate
            hour_stats[hour]["count"] += 1

        best_hours = []
        for hour, stats in hour_stats.items():
            avg_rate = stats["total_rate"] / stats["count"] if stats["count"] > 0 else 0
            best_hours.append({
                "hour": hour,
                "avg_engagement_rate": round(avg_rate, 2),
                "post_count": stats["count"],
            })

        best_hours.sort(key=lambda x: x["avg_engagement_rate"], reverse=True)

        return {
            "platform": platform,
            "best_hours": best_hours[:5],
            "recommendation": f"{best_hours[0]['hour']}時台が最も高いエンゲージメント率です" if best_hours else "データ不足",
        }

    def get_platform_comparison(self, user_id: str, days: int = 30) -> List[Dict]:
        """プラットフォーム間比較"""
        overview = self.get_overview(user_id, days)
        comparison = []
        for platform, data in overview.get("platforms", {}).items():
            comparison.append({
                "platform": platform,
                "followers": data["latest_followers"],
                "follower_change": data["follower_change"],
                "impressions": data["total_impressions"],
                "engagement_rate": data["avg_engagement_rate"],
                "total_likes": data["total_likes"],
                "total_clicks": data["total_clicks"],
            })
        return sorted(comparison, key=lambda x: x["engagement_rate"], reverse=True)


# テスト用
if __name__ == "__main__":
    import random

    service = SnsAnalyticsService()

    # サンプルデータ生成
    platforms = ["x", "instagram", "threads", "tiktok", "line"]
    base_date = datetime.now() - timedelta(days=30)

    for day in range(30):
        date = (base_date + timedelta(days=day)).strftime("%Y-%m-%d")
        for platform in platforms:
            base_followers = {"x": 1500, "instagram": 3000, "threads": 800, "tiktok": 5000, "line": 2000}
            followers = base_followers[platform] + day * random.randint(5, 20)

            metrics = SnsMetrics(
                date=date,
                platform=platform,
                followers=followers,
                followers_change=random.randint(-5, 25),
                impressions=random.randint(500, 5000),
                reach=random.randint(300, 3000),
                engagements=random.randint(50, 500),
                likes=random.randint(30, 300),
                comments=random.randint(5, 50),
                shares=random.randint(2, 30),
                clicks=random.randint(10, 100),
                engagement_rate=round(random.uniform(3, 15), 2),
            )
            service.record_daily_metrics("user_001", metrics)

    # 概要取得
    overview = service.get_overview("user_001", 30)
    print(f"=== 30日間の概要 ===")
    print(f"総インプレッション: {overview['total_impressions']:,}")
    print(f"総エンゲージメント: {overview['total_engagements']:,}")
    print(f"平均エンゲージメント率: {overview['avg_engagement_rate']:.1f}%")
    print(f"総フォロワー: {overview['total_followers']:,}")

    # プラットフォーム比較
    comparison = service.get_platform_comparison("user_001", 30)
    print(f"\n=== プラットフォーム比較 ===")
    for c in comparison:
        print(f"  {c['platform']}: フォロワー {c['followers']:,}, "
              f"エンゲージメント率 {c['engagement_rate']:.1f}%")

    print("\n✓ SNS分析サービス テスト完了")
