"""
TradePost Pro - 自動ハッシュタグ最適化サービス
トレンドに合わせたハッシュタグを自動選定・最適化
"""

import random
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from collections import defaultdict


@dataclass
class HashtagScore:
    """ハッシュタグのスコア"""
    tag: str = ""
    relevance: float = 0.0      # 関連性スコア (0-1)
    popularity: float = 0.0     # 人気度スコア (0-1)
    competition: float = 0.0    # 競合度スコア (0-1, 低い方が良い)
    final_score: float = 0.0    # 最終スコア
    category: str = ""          # カテゴリ


@dataclass
class HashtagSet:
    """最適化されたハッシュタグセット"""
    platform: str = ""
    primary_tags: List[str] = field(default_factory=list)    # メインタグ
    secondary_tags: List[str] = field(default_factory=list)  # サブタグ
    trending_tags: List[str] = field(default_factory=list)   # トレンドタグ
    niche_tags: List[str] = field(default_factory=list)      # ニッチタグ
    all_tags: List[str] = field(default_factory=list)
    total_count: int = 0


class HashtagOptimizer:
    """自動ハッシュタグ最適化サービス"""

    # プラットフォームごとの推奨ハッシュタグ数
    PLATFORM_TAG_LIMITS = {
        "x": 5,
        "instagram": 30,
        "threads": 10,
        "tiktok": 15,
        "line": 5,
    }

    # FXトレード関連のハッシュタグデータベース
    TAG_DATABASE = {
        "core_fx": {
            "tags": ["FX", "為替", "外国為替", "FXトレード", "FXトレーダー"],
            "relevance": 1.0,
            "popularity": 0.9,
            "competition": 0.8,
        },
        "trading_style": {
            "tags": ["デイトレ", "デイトレード", "スキャルピング", "スイングトレード", "自動売買"],
            "relevance": 0.9,
            "popularity": 0.7,
            "competition": 0.6,
        },
        "investment": {
            "tags": ["投資", "資産運用", "投資家", "個人投資家", "投資初心者"],
            "relevance": 0.8,
            "popularity": 0.85,
            "competition": 0.7,
        },
        "beginner": {
            "tags": ["FX初心者", "投資初心者", "トレード初心者", "FX勉強中", "FX始めました"],
            "relevance": 0.85,
            "popularity": 0.8,
            "competition": 0.5,
        },
        "results": {
            "tags": ["トレード結果", "FX結果", "本日の成績", "収支報告", "トレード日記"],
            "relevance": 0.95,
            "popularity": 0.6,
            "competition": 0.4,
        },
        "market": {
            "tags": ["ドル円", "USDJPY", "ユーロドル", "EURUSD", "ポンド円"],
            "relevance": 0.7,
            "popularity": 0.75,
            "competition": 0.5,
        },
        "platform": {
            "tags": ["MT4", "MT5", "MetaTrader", "XM", "XMTrading"],
            "relevance": 0.8,
            "popularity": 0.6,
            "competition": 0.3,
        },
        "lifestyle": {
            "tags": ["副業", "在宅ワーク", "不労所得", "経済的自由", "FIRE"],
            "relevance": 0.6,
            "popularity": 0.85,
            "competition": 0.7,
        },
        "motivation": {
            "tags": ["コツコツ", "継続は力なり", "目標達成", "チャレンジ", "成長"],
            "relevance": 0.5,
            "popularity": 0.7,
            "competition": 0.4,
        },
        "community": {
            "tags": ["FXコミュニティ", "トレード仲間", "投資仲間", "情報交換", "LINE"],
            "relevance": 0.75,
            "popularity": 0.5,
            "competition": 0.3,
        },
    }

    # 曜日別のトレンドタグ
    DAY_SPECIFIC_TAGS = {
        0: ["月曜トレード", "週始め", "今週の目標"],
        1: ["火曜トレード"],
        2: ["水曜トレード", "週の折り返し"],
        3: ["木曜トレード"],
        4: ["金曜トレード", "週末前", "今週のまとめ"],
        5: ["週末分析", "来週の戦略"],
        6: ["週末振り返り", "来週の準備"],
    }

    # 損益に応じたタグ
    PROFIT_TAGS = {
        "big_profit": ["爆益", "大勝ち", "利益確定"],
        "small_profit": ["コツコツ利益", "堅実トレード", "プラス収支"],
        "breakeven": ["トントン", "損益ゼロ"],
        "small_loss": ["損切り", "リスク管理", "次に活かす"],
        "big_loss": ["大敗", "反省", "学び"],
    }

    def __init__(self):
        self.performance_history: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))

    # ============================================================
    # ハッシュタグ最適化
    # ============================================================

    def optimize(
        self,
        platform: str,
        trade_data: Optional[Dict] = None,
        custom_tags: Optional[List[str]] = None,
        max_tags: Optional[int] = None,
    ) -> HashtagSet:
        """プラットフォームと取引データに基づいてハッシュタグを最適化"""
        limit = max_tags or self.PLATFORM_TAG_LIMITS.get(platform, 10)

        # 全候補タグのスコアリング
        scored_tags = self._score_all_tags(platform, trade_data)

        # スコア順にソート
        scored_tags.sort(key=lambda x: x.final_score, reverse=True)

        # カテゴリバランスを考慮して選定
        selected = self._select_balanced(scored_tags, limit)

        # カスタムタグを追加
        if custom_tags:
            for tag in custom_tags:
                if tag not in [s.tag for s in selected]:
                    selected.append(HashtagScore(tag=tag, final_score=0.5, category="custom"))

        # 結果を構築
        primary = [s.tag for s in selected if s.relevance >= 0.8][:3]
        secondary = [s.tag for s in selected if 0.5 <= s.relevance < 0.8][:5]
        trending = self._get_trending_tags(trade_data)
        niche = [s.tag for s in selected if s.competition < 0.4][:5]

        all_tags = list(dict.fromkeys(primary + secondary + trending + niche))[:limit]

        return HashtagSet(
            platform=platform,
            primary_tags=primary,
            secondary_tags=secondary,
            trending_tags=trending,
            niche_tags=niche,
            all_tags=all_tags,
            total_count=len(all_tags),
        )

    def _score_all_tags(
        self,
        platform: str,
        trade_data: Optional[Dict] = None,
    ) -> List[HashtagScore]:
        """全タグのスコアリング"""
        scored = []

        for category, data in self.TAG_DATABASE.items():
            for tag in data["tags"]:
                # 基本スコア
                relevance = data["relevance"]
                popularity = data["popularity"]
                competition = data["competition"]

                # プラットフォーム補正
                if platform == "x" and len(tag) > 10:
                    relevance *= 0.8  # Xでは短いタグが好まれる
                elif platform == "instagram" and category in ["lifestyle", "motivation"]:
                    relevance *= 1.2  # Instagramではライフスタイル系が強い

                # パフォーマンス履歴による補正
                hist_score = self.performance_history.get(platform, {}).get(tag, 0)
                if hist_score > 0:
                    relevance *= (1 + hist_score * 0.1)

                # 最終スコア = 関連性 * 0.4 + 人気度 * 0.3 + (1 - 競合度) * 0.3
                final = relevance * 0.4 + popularity * 0.3 + (1 - competition) * 0.3

                scored.append(HashtagScore(
                    tag=tag,
                    relevance=min(relevance, 1.0),
                    popularity=popularity,
                    competition=competition,
                    final_score=final,
                    category=category,
                ))

        # 損益に応じたタグを追加
        if trade_data:
            profit_tags = self._get_profit_based_tags(trade_data)
            for tag in profit_tags:
                scored.append(HashtagScore(
                    tag=tag,
                    relevance=0.85,
                    popularity=0.6,
                    competition=0.3,
                    final_score=0.7,
                    category="profit_based",
                ))

        return scored

    def _select_balanced(
        self,
        scored_tags: List[HashtagScore],
        limit: int,
    ) -> List[HashtagScore]:
        """カテゴリバランスを考慮した選定"""
        selected = []
        category_counts = defaultdict(int)
        max_per_category = max(2, limit // 4)

        for tag in scored_tags:
            if len(selected) >= limit:
                break
            if category_counts[tag.category] < max_per_category:
                selected.append(tag)
                category_counts[tag.category] += 1

        return selected

    def _get_trending_tags(self, trade_data: Optional[Dict] = None) -> List[str]:
        """トレンドタグを取得"""
        today = datetime.now()
        day_of_week = today.weekday()

        tags = self.DAY_SPECIFIC_TAGS.get(day_of_week, [])

        # 月初・月末の特別タグ
        if today.day <= 3:
            tags.append("月初トレード")
        elif today.day >= 28:
            tags.append("月末トレード")

        return tags[:3]

    def _get_profit_based_tags(self, trade_data: Dict) -> List[str]:
        """損益に応じたタグを取得"""
        profit = trade_data.get("profit", 0)

        if profit > 50000:
            return random.sample(self.PROFIT_TAGS["big_profit"], min(2, len(self.PROFIT_TAGS["big_profit"])))
        elif profit > 0:
            return random.sample(self.PROFIT_TAGS["small_profit"], min(2, len(self.PROFIT_TAGS["small_profit"])))
        elif profit == 0:
            return self.PROFIT_TAGS["breakeven"][:1]
        elif profit > -10000:
            return random.sample(self.PROFIT_TAGS["small_loss"], min(2, len(self.PROFIT_TAGS["small_loss"])))
        else:
            return random.sample(self.PROFIT_TAGS["big_loss"], min(2, len(self.PROFIT_TAGS["big_loss"])))

    # ============================================================
    # パフォーマンス追跡
    # ============================================================

    def record_performance(
        self,
        platform: str,
        tags: List[str],
        engagement_rate: float,
    ) -> None:
        """ハッシュタグのパフォーマンスを記録"""
        for tag in tags:
            current = self.performance_history[platform].get(tag, 0)
            # 移動平均で更新
            self.performance_history[platform][tag] = current * 0.7 + engagement_rate * 0.3

    def get_top_performing_tags(
        self,
        platform: str,
        limit: int = 10,
    ) -> List[Dict]:
        """パフォーマンスの高いタグを取得"""
        tags = self.performance_history.get(platform, {})
        sorted_tags = sorted(tags.items(), key=lambda x: x[1], reverse=True)

        return [
            {"tag": tag, "score": score}
            for tag, score in sorted_tags[:limit]
        ]

    # ============================================================
    # フォーマット
    # ============================================================

    def format_tags(self, hashtag_set: HashtagSet, with_hash: bool = True) -> str:
        """ハッシュタグを投稿用にフォーマット"""
        prefix = "#" if with_hash else ""
        return " ".join(f"{prefix}{tag}" for tag in hashtag_set.all_tags)

    def format_tags_newline(self, hashtag_set: HashtagSet) -> str:
        """ハッシュタグを改行区切りでフォーマット（Instagram向け）"""
        return "\n.\n.\n.\n" + " ".join(f"#{tag}" for tag in hashtag_set.all_tags)


# テスト用
if __name__ == "__main__":
    optimizer = HashtagOptimizer()

    trade_data = {
        "profit": 23500,
        "total_trades": 12,
        "wins": 8,
        "losses": 4,
        "win_rate": 66.7,
    }

    print("=== ハッシュタグ最適化テスト ===")
    for platform in ["x", "instagram", "threads", "tiktok", "line"]:
        result = optimizer.optimize(platform, trade_data)
        formatted = optimizer.format_tags(result)
        print(f"\n[{platform}] ({result.total_count}個)")
        print(f"  メイン: {result.primary_tags}")
        print(f"  サブ: {result.secondary_tags}")
        print(f"  トレンド: {result.trending_tags}")
        print(f"  ニッチ: {result.niche_tags}")
        print(f"  フォーマット: {formatted}")

    # 損失時
    print("\n=== 損失時のハッシュタグ ===")
    loss_data = {"profit": -15000, "wins": 2, "losses": 8, "win_rate": 20.0}
    result = optimizer.optimize("x", loss_data)
    print(f"  タグ: {optimizer.format_tags(result)}")

    print("\n✓ 自動ハッシュタグ最適化サービス テスト完了")
