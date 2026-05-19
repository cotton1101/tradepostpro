"""
ゲーミフィケーションサービス
バッジ、実績、レベルシステムによるユーザーエンゲージメント向上
"""

import math
from datetime import datetime, timedelta
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class BadgeCategory(Enum):
    """バッジカテゴリ"""
    POSTING = "posting"
    TRADING = "trading"
    ENGAGEMENT = "engagement"
    MILESTONE = "milestone"
    SPECIAL = "special"


class BadgeRarity(Enum):
    """バッジレアリティ"""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Badge:
    """バッジ定義"""
    id: str
    name: str
    description: str
    icon: str
    category: BadgeCategory
    rarity: BadgeRarity
    xp_reward: int
    condition: dict
    is_secret: bool = False


@dataclass
class Achievement:
    """実績（段階的なバッジ）"""
    id: str
    name: str
    description: str
    icon: str
    category: BadgeCategory
    tiers: list  # [{threshold: int, name: str, rarity: BadgeRarity, xp: int}]


@dataclass
class UserLevel:
    """ユーザーレベル"""
    level: int
    title: str
    xp_current: int
    xp_required: int
    xp_total: int
    progress_percent: float


@dataclass
class UserBadge:
    """ユーザーが獲得したバッジ"""
    badge_id: str
    earned_at: str
    tier: int = 0


class GamificationService:
    """ゲーミフィケーション管理サービス"""

    # レベルタイトル
    LEVEL_TITLES = {
        1: "ルーキートレーダー",
        5: "アクティブトレーダー",
        10: "エキスパートトレーダー",
        15: "マスタートレーダー",
        20: "エリートトレーダー",
        25: "レジェンドトレーダー",
        30: "グランドマスター",
        40: "トレードキング",
        50: "アルティメットトレーダー",
    }

    def __init__(self):
        self.badges = self._define_badges()
        self.achievements = self._define_achievements()
        self.user_data: dict = {}  # user_id -> {xp, badges, streaks, etc.}

    def _define_badges(self) -> dict:
        """バッジ定義"""
        badges = {
            # 投稿系バッジ
            "first_post": Badge(
                id="first_post", name="初投稿", description="初めてのSNS自動投稿を完了",
                icon="🎯", category=BadgeCategory.POSTING, rarity=BadgeRarity.COMMON,
                xp_reward=50, condition={"type": "post_count", "value": 1},
            ),
            "post_10": Badge(
                id="post_10", name="投稿マスター", description="10回のSNS投稿を達成",
                icon="📝", category=BadgeCategory.POSTING, rarity=BadgeRarity.UNCOMMON,
                xp_reward=100, condition={"type": "post_count", "value": 10},
            ),
            "post_100": Badge(
                id="post_100", name="投稿エキスパート", description="100回のSNS投稿を達成",
                icon="📰", category=BadgeCategory.POSTING, rarity=BadgeRarity.RARE,
                xp_reward=500, condition={"type": "post_count", "value": 100},
            ),
            "post_1000": Badge(
                id="post_1000", name="投稿レジェンド", description="1000回のSNS投稿を達成",
                icon="🏆", category=BadgeCategory.POSTING, rarity=BadgeRarity.LEGENDARY,
                xp_reward=2000, condition={"type": "post_count", "value": 1000},
            ),
            "multi_sns": Badge(
                id="multi_sns", name="マルチプラットフォーム", description="3つ以上のSNSに同時投稿",
                icon="🌐", category=BadgeCategory.POSTING, rarity=BadgeRarity.UNCOMMON,
                xp_reward=150, condition={"type": "sns_platforms", "value": 3},
            ),
            "all_sns": Badge(
                id="all_sns", name="SNSコンプリート", description="5つ全てのSNSに投稿",
                icon="⭐", category=BadgeCategory.POSTING, rarity=BadgeRarity.EPIC,
                xp_reward=500, condition={"type": "sns_platforms", "value": 5},
            ),

            # トレード系バッジ
            "first_profit": Badge(
                id="first_profit", name="初利益", description="初めてのプラス収支を記録",
                icon="💰", category=BadgeCategory.TRADING, rarity=BadgeRarity.COMMON,
                xp_reward=50, condition={"type": "first_profit", "value": True},
            ),
            "win_streak_5": Badge(
                id="win_streak_5", name="5連勝", description="5日連続でプラス収支",
                icon="🔥", category=BadgeCategory.TRADING, rarity=BadgeRarity.RARE,
                xp_reward=300, condition={"type": "win_streak", "value": 5},
            ),
            "win_streak_10": Badge(
                id="win_streak_10", name="10連勝", description="10日連続でプラス収支",
                icon="🌟", category=BadgeCategory.TRADING, rarity=BadgeRarity.EPIC,
                xp_reward=1000, condition={"type": "win_streak", "value": 10},
            ),
            "high_win_rate": Badge(
                id="high_win_rate", name="精密トレーダー", description="月間勝率80%以上を達成",
                icon="🎯", category=BadgeCategory.TRADING, rarity=BadgeRarity.EPIC,
                xp_reward=800, condition={"type": "monthly_win_rate", "value": 80},
            ),
            "profit_10k": Badge(
                id="profit_10k", name="1万円突破", description="累計利益1万円を達成",
                icon="💵", category=BadgeCategory.TRADING, rarity=BadgeRarity.COMMON,
                xp_reward=100, condition={"type": "cumulative_profit", "value": 10000},
            ),
            "profit_100k": Badge(
                id="profit_100k", name="10万円突破", description="累計利益10万円を達成",
                icon="💎", category=BadgeCategory.TRADING, rarity=BadgeRarity.RARE,
                xp_reward=500, condition={"type": "cumulative_profit", "value": 100000},
            ),
            "profit_1m": Badge(
                id="profit_1m", name="ミリオントレーダー", description="累計利益100万円を達成",
                icon="👑", category=BadgeCategory.TRADING, rarity=BadgeRarity.LEGENDARY,
                xp_reward=5000, condition={"type": "cumulative_profit", "value": 1000000},
            ),

            # エンゲージメント系バッジ
            "daily_login_7": Badge(
                id="daily_login_7", name="週間ログイン", description="7日連続ログイン",
                icon="📅", category=BadgeCategory.ENGAGEMENT, rarity=BadgeRarity.UNCOMMON,
                xp_reward=100, condition={"type": "login_streak", "value": 7},
            ),
            "daily_login_30": Badge(
                id="daily_login_30", name="月間ログイン", description="30日連続ログイン",
                icon="🗓️", category=BadgeCategory.ENGAGEMENT, rarity=BadgeRarity.RARE,
                xp_reward=500, condition={"type": "login_streak", "value": 30},
            ),
            "daily_login_365": Badge(
                id="daily_login_365", name="年間ログイン", description="365日連続ログイン",
                icon="🎖️", category=BadgeCategory.ENGAGEMENT, rarity=BadgeRarity.LEGENDARY,
                xp_reward=5000, condition={"type": "login_streak", "value": 365},
            ),
            "template_creator": Badge(
                id="template_creator", name="テンプレートクリエイター", description="カスタムテンプレートを作成",
                icon="🎨", category=BadgeCategory.ENGAGEMENT, rarity=BadgeRarity.UNCOMMON,
                xp_reward=200, condition={"type": "custom_template", "value": 1},
            ),
            "referral_1": Badge(
                id="referral_1", name="紹介者", description="1人のユーザーを紹介",
                icon="🤝", category=BadgeCategory.ENGAGEMENT, rarity=BadgeRarity.UNCOMMON,
                xp_reward=200, condition={"type": "referral_count", "value": 1},
            ),
            "referral_10": Badge(
                id="referral_10", name="アンバサダー", description="10人のユーザーを紹介",
                icon="🏅", category=BadgeCategory.ENGAGEMENT, rarity=BadgeRarity.EPIC,
                xp_reward=1000, condition={"type": "referral_count", "value": 10},
            ),

            # 特別バッジ
            "early_adopter": Badge(
                id="early_adopter", name="アーリーアダプター", description="サービス開始から1ヶ月以内に登録",
                icon="🚀", category=BadgeCategory.SPECIAL, rarity=BadgeRarity.EPIC,
                xp_reward=500, condition={"type": "registration_date", "value": "2026-04-30"},
                is_secret=False,
            ),
            "night_trader": Badge(
                id="night_trader", name="ナイトトレーダー", description="深夜0時〜5時にトレード結果を投稿",
                icon="🌙", category=BadgeCategory.SPECIAL, rarity=BadgeRarity.UNCOMMON,
                xp_reward=100, condition={"type": "post_time_range", "value": [0, 5]},
                is_secret=True,
            ),
            "premium_member": Badge(
                id="premium_member", name="プレミアムメンバー", description="プレミアムプランに加入",
                icon="💎", category=BadgeCategory.SPECIAL, rarity=BadgeRarity.RARE,
                xp_reward=300, condition={"type": "plan", "value": "premium"},
            ),
        }
        return badges

    def _define_achievements(self) -> dict:
        """段階的実績定義"""
        return {
            "posting_master": Achievement(
                id="posting_master",
                name="投稿マスター",
                description="SNS投稿回数の実績",
                icon="📝",
                category=BadgeCategory.POSTING,
                tiers=[
                    {"threshold": 1, "name": "ブロンズ", "rarity": BadgeRarity.COMMON, "xp": 50},
                    {"threshold": 10, "name": "シルバー", "rarity": BadgeRarity.UNCOMMON, "xp": 100},
                    {"threshold": 50, "name": "ゴールド", "rarity": BadgeRarity.RARE, "xp": 300},
                    {"threshold": 100, "name": "プラチナ", "rarity": BadgeRarity.EPIC, "xp": 500},
                    {"threshold": 500, "name": "ダイヤモンド", "rarity": BadgeRarity.LEGENDARY, "xp": 2000},
                ],
            ),
            "profit_milestone": Achievement(
                id="profit_milestone",
                name="利益マイルストーン",
                description="累計利益の実績",
                icon="💰",
                category=BadgeCategory.TRADING,
                tiers=[
                    {"threshold": 10000, "name": "1万円", "rarity": BadgeRarity.COMMON, "xp": 100},
                    {"threshold": 50000, "name": "5万円", "rarity": BadgeRarity.UNCOMMON, "xp": 300},
                    {"threshold": 100000, "name": "10万円", "rarity": BadgeRarity.RARE, "xp": 500},
                    {"threshold": 500000, "name": "50万円", "rarity": BadgeRarity.EPIC, "xp": 1000},
                    {"threshold": 1000000, "name": "100万円", "rarity": BadgeRarity.LEGENDARY, "xp": 5000},
                ],
            ),
        }

    def calculate_level(self, total_xp: int) -> UserLevel:
        """XPからレベルを計算"""
        # レベル計算式: level = floor(sqrt(xp / 100))
        level = max(1, int(math.sqrt(total_xp / 100)))
        xp_for_current = (level ** 2) * 100
        xp_for_next = ((level + 1) ** 2) * 100
        xp_in_level = total_xp - xp_for_current
        xp_needed = xp_for_next - xp_for_current
        progress = (xp_in_level / xp_needed * 100) if xp_needed > 0 else 100

        # タイトル取得
        title = "ルーキートレーダー"
        for lvl, t in sorted(self.LEVEL_TITLES.items()):
            if level >= lvl:
                title = t

        return UserLevel(
            level=level,
            title=title,
            xp_current=xp_in_level,
            xp_required=xp_needed,
            xp_total=total_xp,
            progress_percent=round(progress, 1),
        )

    def check_badges(self, user_id: str, user_stats: dict) -> List[Badge]:
        """ユーザーの統計に基づいてバッジ獲得をチェック"""
        earned = []
        user = self.user_data.get(user_id, {"badges": [], "xp": 0})
        earned_ids = [b.badge_id for b in user.get("badges", [])]

        for badge_id, badge in self.badges.items():
            if badge_id in earned_ids:
                continue

            cond = badge.condition
            cond_type = cond["type"]
            cond_value = cond["value"]

            if cond_type == "post_count" and user_stats.get("total_posts", 0) >= cond_value:
                earned.append(badge)
            elif cond_type == "sns_platforms" and user_stats.get("connected_sns", 0) >= cond_value:
                earned.append(badge)
            elif cond_type == "first_profit" and user_stats.get("has_profit", False):
                earned.append(badge)
            elif cond_type == "win_streak" and user_stats.get("current_win_streak", 0) >= cond_value:
                earned.append(badge)
            elif cond_type == "monthly_win_rate" and user_stats.get("monthly_win_rate", 0) >= cond_value:
                earned.append(badge)
            elif cond_type == "cumulative_profit" and user_stats.get("cumulative_profit", 0) >= cond_value:
                earned.append(badge)
            elif cond_type == "login_streak" and user_stats.get("login_streak", 0) >= cond_value:
                earned.append(badge)
            elif cond_type == "referral_count" and user_stats.get("referral_count", 0) >= cond_value:
                earned.append(badge)
            elif cond_type == "plan" and user_stats.get("plan") == cond_value:
                earned.append(badge)

        return earned

    def award_badge(self, user_id: str, badge: Badge) -> dict:
        """バッジを付与"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {"badges": [], "xp": 0}

        user = self.user_data[user_id]
        user_badge = UserBadge(
            badge_id=badge.id,
            earned_at=datetime.now().isoformat(),
        )
        user["badges"].append(user_badge)
        user["xp"] += badge.xp_reward

        return {
            "badge": badge.name,
            "icon": badge.icon,
            "rarity": badge.rarity.value,
            "xp_earned": badge.xp_reward,
            "total_xp": user["xp"],
            "level": self.calculate_level(user["xp"]),
        }

    def add_xp(self, user_id: str, amount: int, reason: str = "") -> dict:
        """XPを付与"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {"badges": [], "xp": 0}

        old_level = self.calculate_level(self.user_data[user_id]["xp"])
        self.user_data[user_id]["xp"] += amount
        new_level = self.calculate_level(self.user_data[user_id]["xp"])

        result = {
            "xp_earned": amount,
            "total_xp": self.user_data[user_id]["xp"],
            "level": new_level,
            "level_up": new_level.level > old_level.level,
        }

        if result["level_up"]:
            result["new_title"] = new_level.title

        return result

    def get_user_profile(self, user_id: str) -> dict:
        """ユーザーのゲーミフィケーションプロフィールを取得"""
        user = self.user_data.get(user_id, {"badges": [], "xp": 0})
        level = self.calculate_level(user["xp"])

        earned_badges = []
        for ub in user.get("badges", []):
            badge = self.badges.get(ub.badge_id)
            if badge:
                earned_badges.append({
                    "id": badge.id,
                    "name": badge.name,
                    "icon": badge.icon,
                    "rarity": badge.rarity.value,
                    "category": badge.category.value,
                    "earned_at": ub.earned_at,
                })

        return {
            "level": level.level,
            "title": level.title,
            "xp_total": level.xp_total,
            "xp_current": level.xp_current,
            "xp_required": level.xp_required,
            "progress_percent": level.progress_percent,
            "badges_earned": len(earned_badges),
            "badges_total": len(self.badges),
            "badges": earned_badges,
        }

    def get_leaderboard(self, limit: int = 10) -> list:
        """XPリーダーボードを取得"""
        sorted_users = sorted(
            self.user_data.items(),
            key=lambda x: x[1].get("xp", 0),
            reverse=True,
        )
        leaderboard = []
        for rank, (user_id, data) in enumerate(sorted_users[:limit], 1):
            level = self.calculate_level(data.get("xp", 0))
            leaderboard.append({
                "rank": rank,
                "user_id": user_id,
                "xp": data.get("xp", 0),
                "level": level.level,
                "title": level.title,
                "badges_count": len(data.get("badges", [])),
            })
        return leaderboard

    def get_all_badges(self, include_secret: bool = False) -> list:
        """全バッジ一覧を取得"""
        result = []
        for badge in self.badges.values():
            if badge.is_secret and not include_secret:
                continue
            result.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon": badge.icon,
                "category": badge.category.value,
                "rarity": badge.rarity.value,
                "xp_reward": badge.xp_reward,
                "is_secret": badge.is_secret,
            })
        return result


# テスト実行
if __name__ == "__main__":
    service = GamificationService()

    print("=== バッジ一覧 ===")
    all_badges = service.get_all_badges(include_secret=True)
    for badge in all_badges:
        print(f"  {badge['icon']} {badge['name']} ({badge['rarity']}) - {badge['xp_reward']}XP")
    print(f"  合計: {len(all_badges)}個のバッジ")

    print("\n=== レベル計算テスト ===")
    for xp in [0, 100, 500, 1000, 2500, 5000, 10000, 25000]:
        level = service.calculate_level(xp)
        print(f"  XP {xp:>6}: Lv.{level.level} {level.title} ({level.progress_percent}%)")

    print("\n=== バッジ獲得テスト ===")
    user_stats = {
        "total_posts": 15,
        "connected_sns": 4,
        "has_profit": True,
        "current_win_streak": 6,
        "cumulative_profit": 150000,
        "login_streak": 8,
        "plan": "premium",
    }

    earned = service.check_badges("user_001", user_stats)
    print(f"  獲得可能バッジ: {len(earned)}個")
    for badge in earned:
        result = service.award_badge("user_001", badge)
        print(f"    {badge.icon} {badge.name} (+{badge.xp_reward}XP) -> Lv.{result['level'].level}")

    print("\n=== XP付与テスト ===")
    xp_result = service.add_xp("user_001", 200, "daily_post")
    print(f"  +200XP: 合計{xp_result['total_xp']}XP, Lv.{xp_result['level'].level}")
    print(f"  レベルアップ: {xp_result['level_up']}")

    print("\n=== ユーザープロフィール ===")
    profile = service.get_user_profile("user_001")
    print(f"  レベル: {profile['level']} ({profile['title']})")
    print(f"  XP: {profile['xp_current']}/{profile['xp_required']} ({profile['progress_percent']}%)")
    print(f"  バッジ: {profile['badges_earned']}/{profile['badges_total']}")

    print("\n=== リーダーボード ===")
    # 追加ユーザーを作成
    service.add_xp("user_002", 3000, "test")
    service.add_xp("user_003", 1500, "test")
    leaderboard = service.get_leaderboard()
    for entry in leaderboard:
        print(f"  #{entry['rank']} {entry['user_id']}: {entry['xp']}XP (Lv.{entry['level']} {entry['title']})")

    print("\n✓ ゲーミフィケーションサービス テスト完了")
