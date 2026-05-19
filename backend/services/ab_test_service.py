"""
TradePost Pro - A/Bテストサービス
投稿テキスト・画像テンプレートのパターンを比較して最適化
"""

import hashlib
import random
import json
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, List
from enum import Enum


class TestStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VariantType(str, Enum):
    TEXT = "text"
    TEMPLATE = "template"
    HASHTAGS = "hashtags"
    POST_TIME = "post_time"


@dataclass
class Variant:
    """テストバリアント"""
    variant_id: str = ""
    name: str = ""
    variant_type: str = ""
    content: Dict = field(default_factory=dict)
    # メトリクス
    impressions: int = 0
    engagements: int = 0
    clicks: int = 0
    likes: int = 0
    replies: int = 0
    shares: int = 0
    # 計算値
    engagement_rate: float = 0.0
    click_rate: float = 0.0


@dataclass
class ABTest:
    """A/Bテスト"""
    test_id: str = ""
    user_id: str = ""
    name: str = ""
    description: str = ""
    platform: str = ""
    variant_type: str = ""
    variants: List[Variant] = field(default_factory=list)
    status: str = TestStatus.DRAFT
    traffic_split: List[float] = field(default_factory=lambda: [50.0, 50.0])
    # 期間
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    duration_days: int = 7
    # 結果
    winner_variant_id: Optional[str] = None
    confidence_level: float = 0.0
    created_at: str = ""
    updated_at: str = ""


class ABTestService:
    """A/Bテスト管理サービス"""

    def __init__(self):
        self.tests: Dict[str, ABTest] = {}
        self.user_tests: Dict[str, List[str]] = {}

    def create_test(
        self,
        user_id: str,
        name: str,
        platform: str,
        variant_type: str,
        variants_data: List[Dict],
        duration_days: int = 7,
        description: str = "",
    ) -> ABTest:
        """A/Bテスト作成"""
        test_id = hashlib.md5(
            f"{user_id}:{name}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:12]

        variants = []
        split = 100.0 / len(variants_data)
        for i, vdata in enumerate(variants_data):
            variant = Variant(
                variant_id=f"{test_id}_v{i}",
                name=vdata.get("name", f"バリアント {chr(65+i)}"),
                variant_type=variant_type,
                content=vdata.get("content", {}),
            )
            variants.append(variant)

        test = ABTest(
            test_id=test_id,
            user_id=user_id,
            name=name,
            description=description,
            platform=platform,
            variant_type=variant_type,
            variants=variants,
            traffic_split=[split] * len(variants),
            duration_days=duration_days,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        self.tests[test_id] = test
        if user_id not in self.user_tests:
            self.user_tests[user_id] = []
        self.user_tests[user_id].append(test_id)

        return test

    def start_test(self, test_id: str) -> Optional[ABTest]:
        """テスト開始"""
        test = self.tests.get(test_id)
        if not test or test.status != TestStatus.DRAFT:
            return None

        test.status = TestStatus.RUNNING
        test.start_date = datetime.now().isoformat()
        test.end_date = (datetime.now() + timedelta(days=test.duration_days)).isoformat()
        test.updated_at = datetime.now().isoformat()
        return test

    def select_variant(self, test_id: str) -> Optional[Variant]:
        """トラフィック分割に基づいてバリアントを選択"""
        test = self.tests.get(test_id)
        if not test or test.status != TestStatus.RUNNING:
            return None

        rand = random.uniform(0, 100)
        cumulative = 0
        for i, split in enumerate(test.traffic_split):
            cumulative += split
            if rand <= cumulative:
                return test.variants[i]

        return test.variants[-1]

    def record_metrics(
        self,
        test_id: str,
        variant_id: str,
        impressions: int = 0,
        engagements: int = 0,
        clicks: int = 0,
        likes: int = 0,
        replies: int = 0,
        shares: int = 0,
    ) -> bool:
        """メトリクスを記録"""
        test = self.tests.get(test_id)
        if not test:
            return False

        for variant in test.variants:
            if variant.variant_id == variant_id:
                variant.impressions += impressions
                variant.engagements += engagements
                variant.clicks += clicks
                variant.likes += likes
                variant.replies += replies
                variant.shares += shares

                # レート計算
                if variant.impressions > 0:
                    variant.engagement_rate = round(
                        variant.engagements / variant.impressions * 100, 2
                    )
                    variant.click_rate = round(
                        variant.clicks / variant.impressions * 100, 2
                    )

                test.updated_at = datetime.now().isoformat()
                return True

        return False

    def analyze_results(self, test_id: str) -> Dict:
        """テスト結果を分析"""
        test = self.tests.get(test_id)
        if not test:
            return {}

        results = []
        for variant in test.variants:
            results.append({
                "variant_id": variant.variant_id,
                "name": variant.name,
                "impressions": variant.impressions,
                "engagements": variant.engagements,
                "clicks": variant.clicks,
                "likes": variant.likes,
                "engagement_rate": variant.engagement_rate,
                "click_rate": variant.click_rate,
            })

        # 勝者判定（エンゲージメント率ベース）
        winner = None
        max_rate = 0
        for r in results:
            if r["engagement_rate"] > max_rate:
                max_rate = r["engagement_rate"]
                winner = r

        # 信頼度計算（簡易版：サンプルサイズベース）
        total_impressions = sum(r["impressions"] for r in results)
        confidence = min(95.0, total_impressions / 10)  # 1000インプレッションで95%

        return {
            "test_id": test_id,
            "name": test.name,
            "status": test.status,
            "variants": results,
            "winner": winner,
            "confidence_level": round(confidence, 1),
            "recommendation": self._generate_recommendation(results, confidence),
        }

    def _generate_recommendation(self, results: List[Dict], confidence: float) -> str:
        """推奨アクションを生成"""
        if confidence < 80:
            return "まだ十分なデータが集まっていません。テストを継続してください。"

        if len(results) < 2:
            return "比較するバリアントが不足しています。"

        sorted_results = sorted(results, key=lambda r: r["engagement_rate"], reverse=True)
        best = sorted_results[0]
        second = sorted_results[1]

        diff = best["engagement_rate"] - second["engagement_rate"]
        if diff < 0.5:
            return f"「{best['name']}」と「{second['name']}」の差は僅かです（{diff:.1f}%）。テストを延長することをお勧めします。"

        return f"「{best['name']}」が最も高いエンゲージメント率（{best['engagement_rate']:.1f}%）を記録しています。このバリアントの採用をお勧めします。"

    def complete_test(self, test_id: str) -> Optional[Dict]:
        """テスト完了"""
        test = self.tests.get(test_id)
        if not test:
            return None

        test.status = TestStatus.COMPLETED
        test.updated_at = datetime.now().isoformat()

        analysis = self.analyze_results(test_id)
        if analysis.get("winner"):
            test.winner_variant_id = analysis["winner"]["variant_id"]
            test.confidence_level = analysis["confidence_level"]

        return analysis

    def get_user_tests(self, user_id: str) -> List[ABTest]:
        """ユーザーのテスト一覧"""
        test_ids = self.user_tests.get(user_id, [])
        return [self.tests[tid] for tid in test_ids if tid in self.tests]

    def get_active_test(self, user_id: str, platform: str) -> Optional[ABTest]:
        """アクティブなテストを取得"""
        for test in self.get_user_tests(user_id):
            if test.platform == platform and test.status == TestStatus.RUNNING:
                return test
        return None


# テスト用
if __name__ == "__main__":
    service = ABTestService()

    # テスト作成
    test = service.create_test(
        user_id="user_001",
        name="投稿テキスト比較テスト",
        platform="x",
        variant_type=VariantType.TEXT,
        variants_data=[
            {"name": "フォーマルスタイル", "content": {"text": "本日のFXトレード結果をご報告します。"}},
            {"name": "カジュアルスタイル", "content": {"text": "今日のトレード結果！爆益きた！"}},
        ],
        duration_days=7,
    )
    print(f"テスト作成: {test.test_id} ({test.name})")
    print(f"バリアント数: {len(test.variants)}")

    # テスト開始
    service.start_test(test.test_id)
    print(f"ステータス: {test.status}")

    # メトリクス記録（シミュレーション）
    for _ in range(100):
        variant = service.select_variant(test.test_id)
        if variant:
            service.record_metrics(
                test.test_id,
                variant.variant_id,
                impressions=random.randint(50, 200),
                engagements=random.randint(5, 30),
                clicks=random.randint(1, 10),
                likes=random.randint(3, 20),
            )

    # 結果分析
    analysis = service.analyze_results(test.test_id)
    print(f"\n分析結果:")
    for v in analysis["variants"]:
        print(f"  {v['name']}: エンゲージメント率 {v['engagement_rate']:.1f}%, "
              f"クリック率 {v['click_rate']:.1f}%")

    if analysis["winner"]:
        print(f"\n勝者: {analysis['winner']['name']}")
    print(f"信頼度: {analysis['confidence_level']:.1f}%")
    print(f"推奨: {analysis['recommendation']}")

    print("\n✓ A/Bテストサービス テスト完了")
