"""
GraphQL APIサービス
Strawberry GraphQLを使用したGraphQLエンドポイント
"""

import strawberry
from strawberry.fastapi import GraphQLRouter
from typing import Optional, List
from datetime import datetime, date
from enum import Enum


# ========== GraphQL Types ==========

@strawberry.enum
class PlanType(Enum):
    LIGHT = "light"
    STANDARD = "standard"
    PREMIUM = "premium"


@strawberry.enum
class SNSPlatform(Enum):
    TWITTER = "twitter"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    THREADS = "threads"
    LINE = "line"


@strawberry.enum
class PostStatus(Enum):
    PENDING = "pending"
    POSTED = "posted"
    FAILED = "failed"
    SCHEDULED = "scheduled"


@strawberry.type
class User:
    id: str
    email: str
    username: str
    plan: PlanType
    is_active: bool
    created_at: str
    timezone: str = "Asia/Tokyo"
    language: str = "ja"

    @strawberry.field
    def display_name(self) -> str:
        return self.username or self.email.split("@")[0]


@strawberry.type
class TradeResult:
    id: str
    date: str
    daily_profit: float
    cumulative_profit: float
    win_rate: float
    total_trades: int
    wins: int
    losses: int
    currency_pair: Optional[str] = None
    platform: str = "MT4"


@strawberry.type
class SNSPost:
    id: str
    user_id: str
    platform: SNSPlatform
    content: str
    image_url: Optional[str]
    video_url: Optional[str]
    status: PostStatus
    posted_at: Optional[str]
    created_at: str
    engagement: Optional["PostEngagement"] = None


@strawberry.type
class PostEngagement:
    likes: int = 0
    comments: int = 0
    shares: int = 0
    impressions: int = 0
    clicks: int = 0


@strawberry.type
class SNSAccount:
    id: str
    platform: SNSPlatform
    account_name: str
    is_connected: bool
    followers_count: int = 0
    last_posted_at: Optional[str] = None


@strawberry.type
class Template:
    id: str
    name: str
    description: str
    preview_url: Optional[str]
    is_premium: bool = False
    category: str = "default"


@strawberry.type
class Subscription:
    id: str
    plan: PlanType
    status: str
    current_period_start: str
    current_period_end: str
    amount: int
    currency: str = "JPY"


@strawberry.type
class DashboardStats:
    total_posts: int
    posts_today: int
    total_profit: float
    win_rate: float
    connected_accounts: int
    active_templates: int


@strawberry.type
class PaginationInfo:
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_prev: bool


@strawberry.type
class PostConnection:
    items: List[SNSPost]
    pagination: PaginationInfo


@strawberry.type
class TradeConnection:
    items: List[TradeResult]
    pagination: PaginationInfo


# ========== Input Types ==========

@strawberry.input
class PostFilterInput:
    platform: Optional[SNSPlatform] = None
    status: Optional[PostStatus] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None


@strawberry.input
class TradeFilterInput:
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    currency_pair: Optional[str] = None
    min_profit: Optional[float] = None


@strawberry.input
class CreatePostInput:
    platform: SNSPlatform
    content: str
    template_id: Optional[str] = None
    scheduled_at: Optional[str] = None


@strawberry.input
class UpdateProfileInput:
    username: Optional[str] = None
    timezone: Optional[str] = None
    language: Optional[str] = None


# ========== Mock Data Provider ==========

class DataProvider:
    """データプロバイダー（実際にはDB接続）"""

    @staticmethod
    def get_sample_user() -> User:
        return User(
            id="user_001",
            email="trader@example.com",
            username="FXTrader",
            plan=PlanType.PREMIUM,
            is_active=True,
            created_at="2026-01-15T09:00:00",
            timezone="Asia/Tokyo",
            language="ja",
        )

    @staticmethod
    def get_sample_trades(page: int = 1, per_page: int = 10) -> TradeConnection:
        trades = [
            TradeResult(
                id=f"trade_{i}",
                date=f"2026-03-{11-i:02d}",
                daily_profit=15000 - (i * 3000),
                cumulative_profit=285000 - (i * 3000),
                win_rate=66.7 - (i * 2),
                total_trades=12 - i,
                wins=8 - i,
                losses=4,
                currency_pair="USD/JPY",
                platform="MT4",
            )
            for i in range(5)
        ]
        total = len(trades)
        return TradeConnection(
            items=trades[:per_page],
            pagination=PaginationInfo(
                total=total,
                page=page,
                per_page=per_page,
                total_pages=(total + per_page - 1) // per_page,
                has_next=page * per_page < total,
                has_prev=page > 1,
            ),
        )

    @staticmethod
    def get_sample_posts(page: int = 1, per_page: int = 10) -> PostConnection:
        posts = [
            SNSPost(
                id=f"post_{i}",
                user_id="user_001",
                platform=SNSPlatform.TWITTER,
                content=f"本日のトレード結果: +{15000 - i * 1000}円",
                image_url=f"https://storage.example.com/images/post_{i}.png",
                video_url=None,
                status=PostStatus.POSTED,
                posted_at=f"2026-03-{11-i:02d}T07:00:00",
                created_at=f"2026-03-{11-i:02d}T06:55:00",
                engagement=PostEngagement(
                    likes=50 + i * 10,
                    comments=5 + i,
                    shares=3 + i,
                    impressions=1000 + i * 200,
                    clicks=30 + i * 5,
                ),
            )
            for i in range(5)
        ]
        total = len(posts)
        return PostConnection(
            items=posts[:per_page],
            pagination=PaginationInfo(
                total=total,
                page=page,
                per_page=per_page,
                total_pages=(total + per_page - 1) // per_page,
                has_next=page * per_page < total,
                has_prev=page > 1,
            ),
        )

    @staticmethod
    def get_dashboard_stats() -> DashboardStats:
        return DashboardStats(
            total_posts=156,
            posts_today=3,
            total_profit=285000,
            win_rate=66.7,
            connected_accounts=4,
            active_templates=3,
        )


# ========== Query ==========

@strawberry.type
class Query:
    @strawberry.field(description="現在のユーザー情報を取得")
    def me(self) -> User:
        return DataProvider.get_sample_user()

    @strawberry.field(description="ダッシュボード統計を取得")
    def dashboard_stats(self) -> DashboardStats:
        return DataProvider.get_dashboard_stats()

    @strawberry.field(description="取引結果一覧を取得")
    def trades(
        self,
        page: int = 1,
        per_page: int = 10,
        filter: Optional[TradeFilterInput] = None,
    ) -> TradeConnection:
        return DataProvider.get_sample_trades(page, per_page)

    @strawberry.field(description="SNS投稿一覧を取得")
    def posts(
        self,
        page: int = 1,
        per_page: int = 10,
        filter: Optional[PostFilterInput] = None,
    ) -> PostConnection:
        return DataProvider.get_sample_posts(page, per_page)

    @strawberry.field(description="利用可能なテンプレート一覧を取得")
    def templates(self) -> List[Template]:
        return [
            Template(id="dark_classic", name="ダーククラシック", description="プロフェッショナルなダークテーマ", preview_url=None, is_premium=False, category="classic"),
            Template(id="neon_glow", name="ネオングロー", description="サイバーパンク風のネオンテーマ", preview_url=None, is_premium=False, category="modern"),
            Template(id="minimal_white", name="ミニマルホワイト", description="シンプルで清潔感のあるテーマ", preview_url=None, is_premium=False, category="minimal"),
            Template(id="gold_luxury", name="ゴールドラグジュアリー", description="高級感のあるゴールドテーマ", preview_url=None, is_premium=True, category="luxury"),
            Template(id="gradient_wave", name="グラデーションウェーブ", description="モダンなグラデーションテーマ", preview_url=None, is_premium=True, category="modern"),
        ]

    @strawberry.field(description="連携済みSNSアカウント一覧を取得")
    def sns_accounts(self) -> List[SNSAccount]:
        return [
            SNSAccount(id="acc_1", platform=SNSPlatform.TWITTER, account_name="@fx_trader", is_connected=True, followers_count=1500),
            SNSAccount(id="acc_2", platform=SNSPlatform.INSTAGRAM, account_name="fx_trader_jp", is_connected=True, followers_count=800),
            SNSAccount(id="acc_3", platform=SNSPlatform.TIKTOK, account_name="fx_trader", is_connected=True, followers_count=2000),
            SNSAccount(id="acc_4", platform=SNSPlatform.LINE, account_name="FXトレーダー", is_connected=True, followers_count=500),
        ]

    @strawberry.field(description="サブスクリプション情報を取得")
    def subscription(self) -> Subscription:
        return Subscription(
            id="sub_001",
            plan=PlanType.PREMIUM,
            status="active",
            current_period_start="2026-03-01",
            current_period_end="2026-03-31",
            amount=4980,
            currency="JPY",
        )


# ========== Mutation ==========

@strawberry.type
class Mutation:
    @strawberry.mutation(description="新しいSNS投稿を作成")
    def create_post(self, input: CreatePostInput) -> SNSPost:
        return SNSPost(
            id="post_new",
            user_id="user_001",
            platform=input.platform,
            content=input.content,
            image_url=None,
            video_url=None,
            status=PostStatus.SCHEDULED if input.scheduled_at else PostStatus.PENDING,
            posted_at=None,
            created_at=datetime.now().isoformat(),
        )

    @strawberry.mutation(description="プロフィールを更新")
    def update_profile(self, input: UpdateProfileInput) -> User:
        user = DataProvider.get_sample_user()
        if input.username:
            user.username = input.username
        if input.timezone:
            user.timezone = input.timezone
        if input.language:
            user.language = input.language
        return user

    @strawberry.mutation(description="SNS投稿を削除")
    def delete_post(self, post_id: str) -> bool:
        return True

    @strawberry.mutation(description="SNSアカウントを切断")
    def disconnect_sns(self, account_id: str) -> bool:
        return True

    @strawberry.mutation(description="手動で投稿を実行")
    def trigger_post(self, post_id: str) -> SNSPost:
        return SNSPost(
            id=post_id,
            user_id="user_001",
            platform=SNSPlatform.TWITTER,
            content="手動投稿テスト",
            image_url=None,
            video_url=None,
            status=PostStatus.POSTED,
            posted_at=datetime.now().isoformat(),
            created_at=datetime.now().isoformat(),
        )


# ========== Schema ==========

schema = strawberry.Schema(query=Query, mutation=Mutation)


def get_graphql_router() -> GraphQLRouter:
    """FastAPI用のGraphQLルーターを取得"""
    return GraphQLRouter(schema, path="/graphql")


# テスト実行
if __name__ == "__main__":
    import json

    # スキーマのイントロスペクション
    print("=== GraphQL Schema ===")
    print(f"  Schema created successfully")

    # クエリテスト
    result = schema.execute_sync("""
    query {
        me {
            id
            email
            username
            plan
            displayName
        }
    }
    """)
    print(f"\n=== me クエリ ===")
    print(f"  結果: {json.dumps(result.data, ensure_ascii=False, indent=2)}")

    # ダッシュボード統計テスト
    result = schema.execute_sync("""
    query {
        dashboardStats {
            totalPosts
            postsToday
            totalProfit
            winRate
            connectedAccounts
        }
    }
    """)
    print(f"\n=== dashboardStats クエリ ===")
    print(f"  結果: {json.dumps(result.data, ensure_ascii=False, indent=2)}")

    # 取引結果テスト
    result = schema.execute_sync("""
    query {
        trades(page: 1, perPage: 3) {
            items {
                id
                date
                dailyProfit
                winRate
            }
            pagination {
                total
                page
                totalPages
            }
        }
    }
    """)
    print(f"\n=== trades クエリ ===")
    print(f"  結果: {json.dumps(result.data, ensure_ascii=False, indent=2)}")

    # テンプレート一覧テスト
    result = schema.execute_sync("""
    query {
        templates {
            id
            name
            isPremium
        }
    }
    """)
    print(f"\n=== templates クエリ ===")
    print(f"  結果: {json.dumps(result.data, ensure_ascii=False, indent=2)}")

    # ミューテーションテスト
    result = schema.execute_sync("""
    mutation {
        createPost(input: {
            platform: TWITTER,
            content: "本日のトレード結果: +15,000円"
        }) {
            id
            platform
            content
            status
        }
    }
    """)
    print(f"\n=== createPost ミューテーション ===")
    print(f"  結果: {json.dumps(result.data, ensure_ascii=False, indent=2)}")

    # スキーマSDL出力
    sdl = schema.as_str()
    print(f"\n=== Schema SDL ===")
    print(f"  SDL長: {len(sdl)}文字")
    print(f"  Type数: {sdl.count('type ')}")

    print("\n✓ GraphQL APIサービス テスト完了")
