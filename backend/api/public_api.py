"""
TradePost Pro - Public API
外部開発者向けのREST APIエンドポイント
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime, date
import hashlib
import time
import json

router = APIRouter(prefix="/api/v1", tags=["Public API"])


# ============================================================
# リクエスト/レスポンスモデル
# ============================================================

class TradeDataRequest(BaseModel):
    """取引データ送信リクエスト"""
    date: str = Field(..., description="取引日 (YYYY-MM-DD)", example="2026-03-11")
    profit: float = Field(..., description="日次損益（円）", example=17000)
    total_trades: int = Field(..., description="取引回数", example=12)
    wins: int = Field(..., description="勝ち数", example=8)
    losses: int = Field(..., description="負け数", example=4)
    cumulative_profit: Optional[float] = Field(None, description="累計損益（円）", example=250000)
    account_id: Optional[str] = Field(None, description="口座ID", example="MT5-12345")
    platform: Optional[str] = Field("mt5", description="プラットフォーム (mt4/mt5)", example="mt5")


class PostRequest(BaseModel):
    """投稿リクエスト"""
    platforms: List[str] = Field(..., description="投稿先SNS", example=["x", "instagram"])
    template: Optional[str] = Field("dark_classic", description="画像テンプレート名")
    language: Optional[str] = Field("ja", description="言語 (ja/en/zh)")
    custom_text: Optional[str] = Field(None, description="カスタムテキスト")
    include_affiliate_link: Optional[bool] = Field(True, description="アフィリエイトリンクを含める")


class ScheduleRequest(BaseModel):
    """スケジュール設定リクエスト"""
    post_time: str = Field(..., description="投稿時刻 (HH:MM)", example="07:00")
    timezone: Optional[str] = Field("Asia/Tokyo", description="タイムゾーン")
    platforms: List[str] = Field(..., description="投稿先SNS")
    template: Optional[str] = Field("dark_classic", description="画像テンプレート名")
    enabled: Optional[bool] = Field(True, description="有効/無効")


class ApiKeyInfo(BaseModel):
    """APIキー情報"""
    key_id: str
    name: str
    permissions: List[str]
    created_at: str
    last_used: Optional[str]
    rate_limit: int


class ApiResponse(BaseModel):
    """標準APIレスポンス"""
    success: bool
    data: Optional[Dict] = None
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class PaginatedResponse(BaseModel):
    """ページネーション付きレスポンス"""
    success: bool = True
    data: List[Dict]
    total: int
    page: int
    per_page: int
    has_next: bool


# ============================================================
# レート制限（簡易実装）
# ============================================================

class RateLimiter:
    """APIレート制限"""
    def __init__(self):
        self.requests: Dict[str, List[float]] = {}
        self.limits = {
            "free": 60,       # 60 req/hour
            "light": 300,     # 300 req/hour
            "standard": 1000, # 1000 req/hour
            "premium": 5000,  # 5000 req/hour
        }

    def check(self, api_key: str, plan: str = "light") -> bool:
        now = time.time()
        hour_ago = now - 3600

        if api_key not in self.requests:
            self.requests[api_key] = []

        # 1時間以上前のリクエストを削除
        self.requests[api_key] = [t for t in self.requests[api_key] if t > hour_ago]

        limit = self.limits.get(plan, 60)
        if len(self.requests[api_key]) >= limit:
            return False

        self.requests[api_key].append(now)
        return True

    def get_remaining(self, api_key: str, plan: str = "light") -> int:
        now = time.time()
        hour_ago = now - 3600
        if api_key not in self.requests:
            return self.limits.get(plan, 60)
        recent = [t for t in self.requests[api_key] if t > hour_ago]
        return max(0, self.limits.get(plan, 60) - len(recent))


rate_limiter = RateLimiter()


# ============================================================
# 認証ヘルパー
# ============================================================

async def verify_api_key(x_api_key: str = Header(..., description="APIキー")):
    """APIキー検証"""
    if not x_api_key or len(x_api_key) < 10:
        raise HTTPException(status_code=401, detail={
            "error": "invalid_api_key",
            "message": "有効なAPIキーを指定してください"
        })

    if not rate_limiter.check(x_api_key):
        raise HTTPException(status_code=429, detail={
            "error": "rate_limit_exceeded",
            "message": "レート制限を超えました。しばらくしてから再試行してください"
        })

    return {"api_key": x_api_key, "user_id": "user_from_key", "plan": "standard"}


# ============================================================
# エンドポイント: 取引データ
# ============================================================

@router.post("/trades", response_model=ApiResponse, summary="取引データを送信")
async def submit_trade_data(
    data: TradeDataRequest,
    auth: dict = Depends(verify_api_key)
):
    """
    MT4/MT5の日次取引データを送信します。

    - **date**: 取引日（YYYY-MM-DD形式）
    - **profit**: 日次損益（円）
    - **total_trades**: 取引回数
    - **wins/losses**: 勝敗数
    """
    win_rate = (data.wins / data.total_trades * 100) if data.total_trades > 0 else 0

    return ApiResponse(
        success=True,
        data={
            "trade_id": hashlib.md5(f"{auth['user_id']}:{data.date}".encode()).hexdigest()[:16],
            "date": data.date,
            "profit": data.profit,
            "win_rate": round(win_rate, 1),
            "status": "received"
        },
        message="取引データを受信しました"
    )


@router.get("/trades", response_model=PaginatedResponse, summary="取引履歴を取得")
async def get_trade_history(
    start_date: Optional[str] = Query(None, description="開始日 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="終了日 (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="ページ番号"),
    per_page: int = Query(20, ge=1, le=100, description="1ページあたりの件数"),
    auth: dict = Depends(verify_api_key)
):
    """取引履歴をページネーション付きで取得します。"""
    return PaginatedResponse(
        data=[],
        total=0,
        page=page,
        per_page=per_page,
        has_next=False
    )


@router.get("/trades/summary", response_model=ApiResponse, summary="取引サマリーを取得")
async def get_trade_summary(
    period: str = Query("daily", description="期間 (daily/weekly/monthly)"),
    auth: dict = Depends(verify_api_key)
):
    """指定期間の取引サマリーを取得します。"""
    return ApiResponse(
        success=True,
        data={
            "period": period,
            "total_profit": 0,
            "total_trades": 0,
            "win_rate": 0,
            "best_day": None,
            "worst_day": None,
        }
    )


# ============================================================
# エンドポイント: 投稿
# ============================================================

@router.post("/posts", response_model=ApiResponse, summary="SNSに投稿")
async def create_post(
    data: PostRequest,
    auth: dict = Depends(verify_api_key)
):
    """
    最新の取引データを使用してSNSに投稿します。

    - **platforms**: 投稿先のSNSリスト（x, instagram, threads, tiktok, line）
    - **template**: 使用する画像テンプレート名
    """
    post_id = hashlib.md5(
        f"{auth['user_id']}:{datetime.now().isoformat()}".encode()
    ).hexdigest()[:16]

    return ApiResponse(
        success=True,
        data={
            "post_id": post_id,
            "platforms": data.platforms,
            "template": data.template,
            "status": "queued",
            "estimated_completion": "30秒以内"
        },
        message="投稿ジョブをキューに追加しました"
    )


@router.get("/posts", response_model=PaginatedResponse, summary="投稿履歴を取得")
async def get_post_history(
    platform: Optional[str] = Query(None, description="SNSフィルター"),
    status: Optional[str] = Query(None, description="ステータスフィルター"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    auth: dict = Depends(verify_api_key)
):
    """投稿履歴をページネーション付きで取得します。"""
    return PaginatedResponse(
        data=[],
        total=0,
        page=page,
        per_page=per_page,
        has_next=False
    )


@router.get("/posts/{post_id}", response_model=ApiResponse, summary="投稿詳細を取得")
async def get_post_detail(
    post_id: str,
    auth: dict = Depends(verify_api_key)
):
    """特定の投稿の詳細情報を取得します。"""
    return ApiResponse(
        success=True,
        data={
            "post_id": post_id,
            "status": "not_found"
        }
    )


# ============================================================
# エンドポイント: スケジュール
# ============================================================

@router.post("/schedules", response_model=ApiResponse, summary="投稿スケジュールを設定")
async def create_schedule(
    data: ScheduleRequest,
    auth: dict = Depends(verify_api_key)
):
    """毎日の自動投稿スケジュールを設定します。"""
    return ApiResponse(
        success=True,
        data={
            "schedule_id": hashlib.md5(
                f"{auth['user_id']}:schedule".encode()
            ).hexdigest()[:16],
            "post_time": data.post_time,
            "timezone": data.timezone,
            "platforms": data.platforms,
            "enabled": data.enabled,
        },
        message="スケジュールを設定しました"
    )


@router.get("/schedules", response_model=ApiResponse, summary="スケジュール一覧を取得")
async def get_schedules(auth: dict = Depends(verify_api_key)):
    """設定済みの投稿スケジュール一覧を取得します。"""
    return ApiResponse(success=True, data={"schedules": []})


@router.delete("/schedules/{schedule_id}", response_model=ApiResponse, summary="スケジュールを削除")
async def delete_schedule(
    schedule_id: str,
    auth: dict = Depends(verify_api_key)
):
    """投稿スケジュールを削除します。"""
    return ApiResponse(success=True, message="スケジュールを削除しました")


# ============================================================
# エンドポイント: テンプレート
# ============================================================

@router.get("/templates", response_model=ApiResponse, summary="利用可能なテンプレート一覧")
async def get_templates(auth: dict = Depends(verify_api_key)):
    """利用可能な画像テンプレートの一覧を取得します。"""
    templates = [
        {"id": "dark_classic", "name": "ダーククラシック", "plan": "light", "preview_url": ""},
        {"id": "neon_glow", "name": "ネオングロー", "plan": "light", "preview_url": ""},
        {"id": "minimal_white", "name": "ミニマルホワイト", "plan": "light", "preview_url": ""},
        {"id": "gold_luxury", "name": "ゴールドラグジュアリー", "plan": "standard", "preview_url": ""},
        {"id": "gradient_wave", "name": "グラデーションウェーブ", "plan": "standard", "preview_url": ""},
    ]
    return ApiResponse(success=True, data={"templates": templates})


# ============================================================
# エンドポイント: アカウント
# ============================================================

@router.get("/account", response_model=ApiResponse, summary="アカウント情報を取得")
async def get_account(auth: dict = Depends(verify_api_key)):
    """現在のアカウント情報とプラン詳細を取得します。"""
    return ApiResponse(
        success=True,
        data={
            "user_id": auth["user_id"],
            "plan": auth["plan"],
            "api_rate_limit": rate_limiter.limits.get(auth["plan"], 60),
            "api_remaining": rate_limiter.get_remaining(auth["api_key"], auth["plan"]),
        }
    )


@router.get("/account/usage", response_model=ApiResponse, summary="API使用量を取得")
async def get_usage(auth: dict = Depends(verify_api_key)):
    """今月のAPI使用量と残り制限を取得します。"""
    return ApiResponse(
        success=True,
        data={
            "period": datetime.now().strftime("%Y-%m"),
            "api_calls": 0,
            "posts_created": 0,
            "images_generated": 0,
            "videos_generated": 0,
        }
    )


# ============================================================
# エンドポイント: Webhook管理
# ============================================================

@router.get("/webhooks", response_model=ApiResponse, summary="Webhook一覧を取得")
async def get_webhooks(auth: dict = Depends(verify_api_key)):
    """登録済みのWebhook一覧を取得します。"""
    return ApiResponse(success=True, data={"webhooks": []})


# ============================================================
# ヘルスチェック & メタ情報
# ============================================================

@router.get("/status", summary="APIステータス")
async def api_status():
    """APIの稼働状態を確認します（認証不要）。"""
    return {
        "status": "operational",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }
