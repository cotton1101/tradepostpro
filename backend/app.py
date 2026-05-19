"""
XM Affiliate SNS Auto Poster - バックエンドAPI
================================================
FastAPIベースのバックエンドAPIサーバー。
ConoHa VPS上で稼働し、以下の機能を提供します：

- ユーザー認証（JWT / APIキー）
- 取引データの受信・保存
- 画像生成・アップロード
- SNS自動投稿の実行
- 投稿履歴の管理
- プラン管理

【起動方法】
    uvicorn backend.app:app --host 0.0.0.0 --port 8000
"""

import os
import re
import sys
import time
import random
import string
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

# プロジェクトルートをパスに追加
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# .envファイルを読み込み
from dotenv import load_dotenv
load_dotenv(BASE_DIR / ".env")

from backend.models.database import (
    init_db, get_db, User, SNSAccount, TradeDataRecord,
    PostHistory, PostTemplate, PlanType, PlatformType, PostStatus
)
from backend.middleware.auth import (
    get_current_user_by_api_key, get_current_user_by_jwt,
    hash_password, verify_password, create_jwt_token,
    decode_jwt_token, generate_api_key
)
from backend.services.plan_service import PlanService
from backend.middleware.plan_guard import PlanGuard
from backend.api.stripe_routes import router as stripe_router
from backend.services.email_service import EmailService

logger = logging.getLogger(__name__)

# ============================================================
# FastAPIアプリケーション
# ============================================================

app = FastAPI(
    title="XM Affiliate SNS Auto Poster API",
    description="取引結果のSNS自動投稿を管理するバックエンドAPI",
    version="2.1.0"
)

# Stripeルーターの登録
app.include_router(stripe_router)

# CORS設定
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8080,http://localhost:3000,http://localhost:8000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# セキュリティミドルウェア
# ============================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """セキュリティヘッダーを追加"""
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response

app.add_middleware(SecurityHeadersMiddleware)


# ============================================================
# レート制限
# ============================================================

class RateLimiter:
    """シンプルなIPベースのレート制限"""
    def __init__(self):
        self._requests: Dict[str, list] = defaultdict(list)

    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        # 古いエントリを削除
        self._requests[key] = [t for t in self._requests[key] if now - t < window_seconds]
        if len(self._requests[key]) >= max_requests:
            return False
        self._requests[key].append(now)
        return True

rate_limiter = RateLimiter()

# レート制限設定 (パス -> (最大回数, 秒数))
RATE_LIMITS = {
    "/api/auth/login": (5, 60),         # 5回/分
    "/api/auth/register": (3, 3600),     # 3回/時
    "/api/contact": (2, 600),            # 2回/10分
    "/api/auth/2fa/verify": (5, 300),    # 5回/5分
}


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """レート制限ミドルウェア"""
    path = request.url.path
    if path in RATE_LIMITS and request.method == "POST":
        client_ip = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.client.host
        max_req, window = RATE_LIMITS[path]
        key = f"{client_ip}:{path}"
        if not rate_limiter.is_allowed(key, max_req, window):
            return JSONResponse(
                status_code=429,
                content={"detail": "リクエストが多すぎます。しばらくしてからお試しください。"},
                headers={"Retry-After": str(window)},
            )
    return await call_next(request)


# ============================================================
# メールサービス・2FAコード管理
# ============================================================

email_service = EmailService()

# 2FA認証コード一時保存 { "user_id:code": {"code": "123456", "expires": timestamp} }
_2fa_pending: Dict[str, dict] = {}


def generate_2fa_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def create_2fa_temp_token(user_id: int) -> str:
    """2FA検証用の一時トークン（5分有効）"""
    import jwt
    from datetime import timedelta
    payload = {
        "user_id": user_id,
        "type": "2fa_pending",
        "exp": datetime.utcnow() + timedelta(minutes=5),
        "iat": datetime.utcnow(),
    }
    JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_2fa_temp_token(token: str) -> Optional[dict]:
    """2FA一時トークンをデコード"""
    try:
        import jwt
        JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "2fa_pending":
            return None
        return payload
    except Exception:
        return None


# フロントエンド静的ファイル配信
FRONTEND_DIR = BASE_DIR / "frontend"


@app.get("/", include_in_schema=False)
async def serve_frontend():
    """フロントエンドのindex.htmlを配信"""
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/download/DailyTradeExporter.mq4", include_in_schema=False)
async def download_mq4():
    """MT4用EA（MQ4ファイル）のダウンロード"""
    mq4_path = BASE_DIR / "mt4_ea" / "DailyTradeExporter.mq4"
    if not mq4_path.exists():
        raise HTTPException(status_code=404, detail="MQ4ファイルが見つかりません")
    return FileResponse(
        str(mq4_path),
        media_type="application/octet-stream",
        filename="DailyTradeExporter.mq4"
    )


if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="frontend")


# ============================================================
# Pydanticスキーマ
# ============================================================

class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    plan: str
    is_active: bool
    is_admin: bool = False
    api_key: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    two_factor_enabled: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class TwoFAResponse(BaseModel):
    requires_2fa: bool = True
    temp_token: str

class TwoFAVerifyRequest(BaseModel):
    temp_token: str
    code: str

class TwoFAToggleRequest(BaseModel):
    password: str

class ChangeEmailRequest(BaseModel):
    new_email: str
    password: str

class ChangeNameRequest(BaseModel):
    new_name: str

class ContactFormInput(BaseModel):
    name: str
    email: str
    subject: str
    message: str

class TradeDataInput(BaseModel):
    date: str
    platform: str = "MT5"
    account_balance: float = 0
    daily_profit: float = 0
    daily_loss: float = 0
    net_profit: float = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0
    cumulative_profit: float = 0
    currency: str = "JPY"

class SNSAccountInput(BaseModel):
    platform: str
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    user_id_external: Optional[str] = None
    group_id: Optional[str] = None

class PostRequest(BaseModel):
    date: Optional[str] = None
    platforms: Optional[List[str]] = None
    template_id: Optional[int] = None
    custom_template_id: Optional[int] = None
    generate_video: bool = False
    video_effect: Optional[str] = None

class BgUploadRequest(BaseModel):
    image_data: str  # Base64

class TemplateElement(BaseModel):
    type: str
    x: float
    y: float
    fontSize: int = 32
    color: str = "#ffffff"
    bold: bool = False
    text: Optional[str] = None
    profitColor: str = "#00ff00"
    lossColor: str = "#ff0000"

class CustomTemplateSaveRequest(BaseModel):
    name: str
    background: str = ""
    elements: List[TemplateElement] = []
    text_template: str = ""
    template_id: Optional[int] = None  # 更新時

class CustomTemplatePreviewRequest(BaseModel):
    background: str = ""
    elements: List[TemplateElement] = []

class PostHistoryResponse(BaseModel):
    id: int
    date: str
    platform: str
    status: str
    post_text: Optional[str] = None
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# パスワードバリデーション
# ============================================================

def validate_password(password: str) -> Optional[str]:
    """パスワード強度をチェック。問題なければNone、問題あればエラーメッセージを返す"""
    if len(password) < 8:
        return "パスワードは8文字以上にしてください"
    if not re.search(r"[a-zA-Z]", password):
        return "パスワードには英字を含めてください"
    if not re.search(r"[0-9]", password):
        return "パスワードには数字を含めてください"
    return None


# ============================================================
# 起動イベント
# ============================================================

@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時にDBを初期化します。"""
    init_db()


# ============================================================
# ヘルスチェック
# ============================================================

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "2.1.0"}


# ============================================================
# 認証API
# ============================================================

def _make_user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        plan=user.plan.value,
        is_active=user.is_active,
        is_admin=user.is_admin,
        api_key=user.api_key,
        stripe_subscription_id=user.stripe_subscription_id,
        two_factor_enabled=user.two_factor_enabled,
        created_at=user.created_at
    )


@app.post("/api/auth/register", response_model=TokenResponse)
async def register(data: UserRegister, db: Session = Depends(get_db)):
    """新規ユーザー登録"""
    # パスワード強度チェック
    pw_error = validate_password(data.password)
    if pw_error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=pw_error)

    # メールアドレスの重複チェック
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に登録されています"
        )

    # ユーザーの作成
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        name=data.name,
        plan=PlanType.FREE,
        api_key=generate_api_key()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 管理者へ通知メール（非同期的にエラーを無視）
    try:
        email_service.send_admin_new_registration({
            "name": user.name,
            "email": user.email,
            "plan": "FREE",
        })
    except Exception as e:
        logger.warning(f"管理者通知メール送信失敗: {e}")

    # ウェルカムメール
    try:
        email_service.send_welcome(user.email, {"name": user.name})
    except Exception as e:
        logger.warning(f"ウェルカムメール送信失敗: {e}")

    # JWTトークンの生成
    token = create_jwt_token(user.id)

    return TokenResponse(access_token=token, user=_make_user_response(user))


@app.post("/api/auth/login")
async def login(data: UserLogin, db: Session = Depends(get_db)):
    """ログイン"""
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません"
        )

    # 2FA有効の場合
    if user.two_factor_enabled:
        code = generate_2fa_code()
        temp_token = create_2fa_temp_token(user.id)
        _2fa_pending[f"{user.id}"] = {
            "code": code,
            "expires": time.time() + 600,  # 10分
        }
        # 認証コードをメール送信
        try:
            email_service.send_2fa_code(user.email, code)
        except Exception as e:
            logger.error(f"2FAコード送信失敗: {e}")
            raise HTTPException(status_code=500, detail="認証コードの送信に失敗しました")

        return {"requires_2fa": True, "temp_token": temp_token}

    # 通常ログイン
    token = create_jwt_token(user.id)
    return TokenResponse(access_token=token, user=_make_user_response(user))


@app.post("/api/auth/2fa/verify")
async def verify_2fa(data: TwoFAVerifyRequest, db: Session = Depends(get_db)):
    """2FA認証コード検証"""
    payload = decode_2fa_temp_token(data.temp_token)
    if not payload:
        raise HTTPException(status_code=401, detail="無効または期限切れのトークンです")

    user_id = payload["user_id"]
    pending = _2fa_pending.get(f"{user_id}")
    if not pending:
        raise HTTPException(status_code=401, detail="認証コードが見つかりません。再度ログインしてください。")

    if time.time() > pending["expires"]:
        _2fa_pending.pop(f"{user_id}", None)
        raise HTTPException(status_code=401, detail="認証コードの有効期限が切れました。再度ログインしてください。")

    if data.code != pending["code"]:
        raise HTTPException(status_code=401, detail="認証コードが正しくありません")

    # コード消費
    _2fa_pending.pop(f"{user_id}", None)

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="ユーザーが見つかりません")

    token = create_jwt_token(user.id)
    return TokenResponse(access_token=token, user=_make_user_response(user))


@app.post("/api/auth/2fa/enable")
async def enable_2fa(
    data: TwoFAToggleRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """2段階認証を有効化"""
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="パスワードが正しくありません")

    if user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2段階認証は既に有効です")

    user.two_factor_enabled = True
    db.commit()
    return {"message": "2段階認証を有効にしました"}


@app.post("/api/auth/2fa/disable")
async def disable_2fa(
    data: TwoFAToggleRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """2段階認証を無効化"""
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="パスワードが正しくありません")

    if not user.two_factor_enabled:
        raise HTTPException(status_code=400, detail="2段階認証は既に無効です")

    user.two_factor_enabled = False
    db.commit()
    return {"message": "2段階認証を無効にしました"}


# ============================================================
# お問い合わせAPI
# ============================================================

@app.post("/api/contact")
async def contact(data: ContactFormInput):
    """お問い合わせフォーム"""
    # バリデーション
    if not data.name.strip() or not data.email.strip() or not data.message.strip():
        raise HTTPException(status_code=400, detail="全ての項目を入力してください")

    if len(data.message) > 5000:
        raise HTTPException(status_code=400, detail="メッセージは5000文字以内にしてください")

    try:
        email_service.send_admin_contact_form({
            "name": data.name,
            "email": data.email,
            "subject": data.subject or "一般的なお問い合わせ",
            "message": data.message,
        })
    except Exception as e:
        logger.error(f"お問い合わせメール送信失敗: {e}")
        raise HTTPException(status_code=500, detail="送信に失敗しました。しばらくしてからお試しください。")

    return {"success": True, "message": "お問い合わせを送信しました。"}


# ============================================================
# ユーザーAPI
# ============================================================

@app.get("/api/user/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user_by_jwt)):
    """現在のユーザー情報を取得"""
    return _make_user_response(user)


@app.post("/api/user/regenerate-api-key")
async def regenerate_api_key(
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """APIキーを再生成"""
    user.api_key = generate_api_key()
    db.commit()
    return {"api_key": user.api_key}


@app.post("/api/user/change-email")
async def change_email(
    data: ChangeEmailRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """メールアドレスを変更"""
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="パスワードが正しくありません")
    existing = db.query(User).filter(User.email == data.new_email).first()
    if existing:
        raise HTTPException(status_code=400, detail="このメールアドレスは既に使用されています")
    user.email = data.new_email
    db.commit()
    return {"message": "メールアドレスを変更しました", "email": user.email}


@app.post("/api/user/change-name")
async def change_name(
    data: ChangeNameRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """名前を変更"""
    if not data.new_name.strip():
        raise HTTPException(status_code=400, detail="名前を入力してください")
    user.name = data.new_name.strip()
    db.commit()
    return {"message": "名前を変更しました", "name": user.name}


# ============================================================
# プランAPI
# ============================================================

@app.get("/api/plans")
async def get_plans():
    """利用可能なプラン一覧を取得"""
    return PlanService.get_all_plans()


# ============================================================
# SNSアカウントAPI
# ============================================================

@app.get("/api/sns-accounts")
async def get_sns_accounts(
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """ユーザーのSNSアカウント一覧を取得"""
    accounts = db.query(SNSAccount).filter(
        SNSAccount.user_id == user.id
    ).all()

    return [
        {
            "id": acc.id,
            "platform": acc.platform.value,
            "is_enabled": acc.is_enabled,
            "has_token": bool(acc.access_token),
            "user_id_external": acc.user_id_external,
        }
        for acc in accounts
    ]


@app.post("/api/sns-accounts")
async def add_sns_account(
    data: SNSAccountInput,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """SNSアカウントを追加"""
    enabled_count = db.query(SNSAccount).filter(
        SNSAccount.user_id == user.id,
        SNSAccount.is_enabled == True
    ).count()

    if not PlanService.can_use_platform(user.plan, enabled_count):
        plan_config = PlanService.get_plan_config(user.plan)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{plan_config.name}プランでは最大{plan_config.max_sns_count}つまでのSNSが利用可能です。"
        )

    existing = db.query(SNSAccount).filter(
        SNSAccount.user_id == user.id,
        SNSAccount.platform == data.platform
    ).first()

    if existing:
        existing.access_token = data.access_token or existing.access_token
        existing.access_token_secret = data.access_token_secret or existing.access_token_secret
        existing.api_key = data.api_key or existing.api_key
        existing.api_secret = data.api_secret or existing.api_secret
        existing.user_id_external = data.user_id_external or existing.user_id_external
        existing.group_id = data.group_id or existing.group_id
        existing.is_enabled = True
        db.commit()
        return {"message": "SNSアカウントを更新しました", "id": existing.id}
    else:
        account = SNSAccount(
            user_id=user.id,
            platform=data.platform,
            access_token=data.access_token,
            access_token_secret=data.access_token_secret,
            api_key=data.api_key,
            api_secret=data.api_secret,
            user_id_external=data.user_id_external,
            group_id=data.group_id,
        )
        db.add(account)
        db.commit()
        return {"message": "SNSアカウントを追加しました", "id": account.id}


@app.delete("/api/sns-accounts/{account_id}")
async def delete_sns_account(
    account_id: int,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """SNSアカウントを削除"""
    account = db.query(SNSAccount).filter(
        SNSAccount.id == account_id,
        SNSAccount.user_id == user.id
    ).first()

    if not account:
        raise HTTPException(status_code=404, detail="アカウントが見つかりません")

    db.delete(account)
    db.commit()
    return {"message": "SNSアカウントを削除しました"}


# ============================================================
# 取引データAPI
# ============================================================

@app.post("/api/trade-data")
async def submit_trade_data(
    data: TradeDataInput,
    user: User = Depends(get_current_user_by_api_key),
    db: Session = Depends(get_db)
):
    """取引データを送信（VPS上のスクリプトから呼び出し）"""
    record = TradeDataRecord(
        user_id=user.id,
        date=data.date,
        platform=data.platform,
        account_balance=data.account_balance,
        daily_profit=data.daily_profit,
        daily_loss=data.daily_loss,
        net_profit=data.net_profit,
        total_trades=data.total_trades,
        winning_trades=data.winning_trades,
        losing_trades=data.losing_trades,
        win_rate=data.win_rate,
        cumulative_profit=data.cumulative_profit,
        currency=data.currency,
    )
    db.add(record)
    db.commit()

    return {"message": "取引データを保存しました", "id": record.id}


@app.get("/api/trade-data")
async def get_trade_data(
    limit: int = 30,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """取引データ履歴を取得"""
    records = db.query(TradeDataRecord).filter(
        TradeDataRecord.user_id == user.id
    ).order_by(TradeDataRecord.date.desc()).limit(limit).all()

    return [
        {
            "id": r.id,
            "date": r.date,
            "platform": r.platform,
            "net_profit": r.net_profit,
            "total_trades": r.total_trades,
            "win_rate": r.win_rate,
            "cumulative_profit": r.cumulative_profit,
        }
        for r in records
    ]


# ============================================================
# 投稿API
# ============================================================

def _build_trade_data_dict(trade_record: TradeDataRecord) -> dict:
    """TradeDataRecordから辞書を作成"""
    return {
        "date": trade_record.date or "",
        "net_profit": trade_record.net_profit or 0,
        "total_trades": trade_record.total_trades or 0,
        "winning_trades": trade_record.winning_trades or 0,
        "losing_trades": trade_record.losing_trades or 0,
        "win_rate": trade_record.win_rate or 0,
        "cumulative_profit": trade_record.cumulative_profit or 0,
    }


def _build_trade_data_obj(trade_record: TradeDataRecord):
    """TradeDataRecordからTradeDataオブジェクトを作成"""
    from modules.utils import TradeData
    return TradeData(
        date=trade_record.date or "",
        platform=trade_record.platform or "MT5",
        account_balance=trade_record.account_balance or 0,
        daily_profit=trade_record.daily_profit or 0,
        daily_loss=trade_record.daily_loss or 0,
        net_profit=trade_record.net_profit or 0,
        total_trades=trade_record.total_trades or 0,
        winning_trades=trade_record.winning_trades or 0,
        losing_trades=trade_record.losing_trades or 0,
        win_rate=trade_record.win_rate or 0,
        cumulative_profit=trade_record.cumulative_profit or 0,
        currency=trade_record.currency or "JPY",
    )


def _apply_text_template(template_text: str, trade_data: dict) -> str:
    """テキストテンプレートの変数を実データで置換"""
    net = trade_data.get("net_profit", 0)
    cum = trade_data.get("cumulative_profit", 0)
    replacements = {
        "{date}": trade_data.get("date", ""),
        "{net_profit}": f"{'+'if net>=0 else ''}{net:,.0f}円",
        "{win_rate}": f"{trade_data.get('win_rate', 0):.1f}%",
        "{total_trades}": f"{trade_data.get('total_trades', 0)}回",
        "{winning_trades}": f"{trade_data.get('winning_trades', 0)}勝",
        "{losing_trades}": f"{trade_data.get('losing_trades', 0)}敗",
        "{cumulative_profit}": f"{'+'if cum>=0 else ''}{cum:,.0f}円",
    }
    result = template_text
    for k, v in replacements.items():
        result = result.replace(k, v)
    return result


@app.post("/api/post/execute")
async def execute_post(
    data: PostRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """SNS投稿を実行します"""
    validation = PlanGuard.validate_post_request(
        user=user, db=db, platforms=data.platforms,
        template_id=data.template_id, generate_video=data.generate_video
    )

    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="\n".join(validation["errors"])
        )

    trade_record = db.query(TradeDataRecord).filter(
        TradeDataRecord.user_id == user.id
    ).order_by(TradeDataRecord.date.desc()).first()

    if not trade_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="取引データがありません。先にデータを送信してください。"
        )

    allowed = validation["allowed_platforms"]
    sns_accounts = db.query(SNSAccount).filter(
        SNSAccount.user_id == user.id,
        SNSAccount.is_enabled == True,
        SNSAccount.platform.in_(allowed)
    ).all()

    if not sns_accounts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="有効なSNSアカウントがありません"
        )

    trade_dict = _build_trade_data_dict(trade_record)

    # --- 画像生成 ---
    image_path = None
    custom_text = None

    if data.custom_template_id:
        tmpl = db.query(PostTemplate).filter(
            PostTemplate.id == data.custom_template_id,
            PostTemplate.user_id == user.id,
        ).first()
        if tmpl and tmpl.config_json:
            import json as _json
            try:
                config = _json.loads(tmpl.config_json)
                bg_dir = os.path.join(BASE_DIR, "data", "bg_images")
                from modules.custom_template_renderer import render_from_config
                image_path = render_from_config(
                    config_json=config,
                    trade_data=trade_dict,
                    bg_image_dir=bg_dir,
                )
                logger.info(f"カスタムテンプレート画像生成: {image_path}")
            except Exception as e:
                logger.error(f"カスタム画像生成失敗: {e}")

        if tmpl and tmpl.text_template:
            custom_text = _apply_text_template(tmpl.text_template, trade_dict)
    elif data.template_id:
        # プリセットテンプレートの場合（既存のimage_templates使用）
        try:
            from modules.image_templates import render_template
            td_obj = _build_trade_data_obj(trade_record)
            tmpl = db.query(PostTemplate).filter(PostTemplate.id == data.template_id).first()
            tmpl_name = tmpl.image_template_path if tmpl else "dark_modern"
            image_path = render_template(
                template_id=tmpl_name or "dark_modern",
                trade_data=td_obj,
            )
        except Exception as e:
            logger.warning(f"プリセットテンプレート画像生成失敗: {e}")

    # --- 動画エフェクト生成 ---
    video_path = None
    if data.video_effect and image_path:
        try:
            from modules.effect_video_generator import generate_effect_video, EFFECTS
            if data.video_effect in EFFECTS:
                video_path = generate_effect_video(
                    image_path=image_path,
                    effect_type=data.video_effect,
                    duration=5.0,
                    fps=24,
                )
                logger.info(f"動画エフェクト生成完了: {video_path}")
            else:
                logger.warning(f"不明なエフェクト: {data.video_effect}")
        except Exception as e:
            logger.error(f"動画エフェクト生成失敗: {e}")

    # --- SNS投稿実行 ---
    results = []
    for acc in sns_accounts:
        history = PostHistory(
            user_id=user.id,
            date=trade_record.date,
            platform=acc.platform,
            status=PostStatus.PENDING,
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        td = _build_trade_data_obj(trade_record)
        post_result = None
        try:
            if acc.platform == PlatformType.X:
                from modules.post_x import XPoster
                poster = XPoster(
                    api_key=acc.api_key or "",
                    api_secret=acc.api_secret or "",
                    access_token=acc.access_token or "",
                    access_token_secret=acc.access_token_secret or "",
                )
                post_result = poster.post(
                    trade_data=td,
                    custom_text=custom_text,
                    image_path=image_path,
                )

            elif acc.platform == PlatformType.LINE:
                from modules.post_line import LinePoster
                poster = LinePoster(
                    channel_access_token=acc.access_token or "",
                    group_id=acc.group_id or "",
                )
                post_result = poster.post(
                    trade_data=td,
                    custom_text=custom_text,
                )

            elif acc.platform == PlatformType.INSTAGRAM:
                from modules.post_instagram import InstagramPoster
                poster = InstagramPoster(
                    access_token=acc.access_token or "",
                    user_id=acc.user_id_external or "",
                )
                # Instagram requires public image URL — skip if no URL available
                post_result = {"success": False, "error": "Instagram投稿にはHTTPS画像URLが必要です", "platform": "instagram"}

            elif acc.platform == PlatformType.THREADS:
                from modules.post_threads import ThreadsPoster
                poster = ThreadsPoster(
                    access_token=acc.access_token or "",
                    user_id=acc.user_id_external or "",
                )
                post_result = poster.post(trade_data=td, custom_text=custom_text)

            else:
                post_result = {"success": False, "error": f"未対応プラットフォーム: {acc.platform.value}", "platform": acc.platform.value}

        except Exception as e:
            logger.error(f"SNS投稿エラー ({acc.platform.value}): {e}")
            post_result = {"success": False, "error": str(e), "platform": acc.platform.value}

        # 履歴更新
        if post_result and post_result.get("success"):
            history.status = PostStatus.SUCCESS
            history.post_text = post_result.get("text", custom_text or "")
            history.image_url = image_path
            history.external_post_id = post_result.get("tweet_id") or post_result.get("post_id") or ""
        else:
            history.status = PostStatus.FAILED
            history.error_message = post_result.get("error", "不明なエラー") if post_result else "投稿処理が実行されませんでした"
        db.commit()

        results.append({
            "history_id": history.id,
            "platform": acc.platform.value,
            "status": history.status.value,
            "error": history.error_message,
        })

    success_count = sum(1 for r in results if r["status"] == "success")
    fail_count = sum(1 for r in results if r["status"] == "failed")

    return {
        "message": f"{success_count}件成功、{fail_count}件失敗（合計{len(results)}件）",
        "jobs": results,
        "warnings": validation["warnings"],
    }


# ============================================================
# 投稿履歴API
# ============================================================

@app.get("/api/post-history", response_model=List[PostHistoryResponse])
async def get_post_history(
    limit: int = 50,
    platform: Optional[str] = None,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """投稿履歴を取得"""
    query = db.query(PostHistory).filter(PostHistory.user_id == user.id)

    if platform:
        query = query.filter(PostHistory.platform == platform)

    records = query.order_by(PostHistory.created_at.desc()).limit(limit).all()
    return records


# ============================================================
# テンプレートAPI
# ============================================================

@app.get("/api/templates")
async def get_templates(
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """利用可能なテンプレート一覧を取得"""
    templates = db.query(PostTemplate).filter(
        PostTemplate.is_active == True
    ).all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "template_type": t.template_type,
            "available": PlanService.can_use_template(user.plan, t.template_type),
            "min_plan": t.min_plan.value,
        }
        for t in templates
    ]


# ============================================================
# 統計API
# ============================================================

@app.get("/api/stats/dashboard")
async def get_dashboard_stats(
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db)
):
    """ダッシュボード用の統計情報を取得"""
    success_count = db.query(PostHistory).filter(
        PostHistory.user_id == user.id, PostHistory.status == PostStatus.SUCCESS
    ).count()
    failed_count = db.query(PostHistory).filter(
        PostHistory.user_id == user.id, PostHistory.status == PostStatus.FAILED
    ).count()
    active_sns = db.query(SNSAccount).filter(
        SNSAccount.user_id == user.id, SNSAccount.is_enabled == True
    ).count()
    latest_trade = db.query(TradeDataRecord).filter(
        TradeDataRecord.user_id == user.id
    ).order_by(TradeDataRecord.date.desc()).first()
    plan_config = PlanService.get_plan_config(user.plan)

    return {
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "plan": user.plan.value,
            "plan_name": plan_config.name,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "two_factor_enabled": user.two_factor_enabled,
        },
        "stats": {
            "total_posts": success_count + failed_count,
            "success_posts": success_count,
            "failed_posts": failed_count,
            "active_sns_count": active_sns,
            "max_sns_count": plan_config.max_sns_count,
        },
        "latest_trade": {
            "date": latest_trade.date if latest_trade else None,
            "net_profit": latest_trade.net_profit if latest_trade else 0,
            "win_rate": latest_trade.win_rate if latest_trade else 0,
            "cumulative_profit": latest_trade.cumulative_profit if latest_trade else 0,
        } if latest_trade else None,
    }


# ============================================================
# 管理者チェック用ヘルパー
# ============================================================

def require_admin(user: User = Depends(get_current_user_by_jwt)):
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    return user


# ============================================================
# 管理者API
# ============================================================

class AdminPlanChange(BaseModel):
    plan: str

class AdminUserToggle(BaseModel):
    is_active: bool


@app.get("/api/admin/stats")
async def admin_stats(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理者用: システム統計"""
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    free_users = db.query(User).filter(User.plan == PlanType.FREE).count()
    light_users = db.query(User).filter(User.plan == PlanType.LIGHT).count()
    standard_users = db.query(User).filter(User.plan == PlanType.STANDARD).count()
    premium_users = db.query(User).filter(User.plan == PlanType.PREMIUM).count()
    total_posts = db.query(PostHistory).count()
    success_posts = db.query(PostHistory).filter(PostHistory.status == PostStatus.SUCCESS).count()
    failed_posts = db.query(PostHistory).filter(PostHistory.status == PostStatus.FAILED).count()
    total_sns = db.query(SNSAccount).filter(SNSAccount.is_enabled == True).count()

    mrr = (light_users * 1980) + (standard_users * 2980) + (premium_users * 4980)

    return {
        "users": {
            "total": total_users, "active": active_users,
            "inactive": total_users - active_users,
            "by_plan": {"free": free_users, "light": light_users, "standard": standard_users, "premium": premium_users}
        },
        "posts": {"total": total_posts, "success": success_posts, "failed": failed_posts},
        "sns": {"total_active": total_sns},
        "revenue": {"mrr": mrr, "arr": mrr * 12}
    }


@app.get("/api/admin/users")
async def admin_list_users(
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理者用: 全ユーザー一覧"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    result = []
    for u in users:
        sns_count = db.query(SNSAccount).filter(SNSAccount.user_id == u.id, SNSAccount.is_enabled == True).count()
        post_count = db.query(PostHistory).filter(PostHistory.user_id == u.id).count()
        success_count = db.query(PostHistory).filter(PostHistory.user_id == u.id, PostHistory.status == PostStatus.SUCCESS).count()
        result.append({
            "id": u.id, "email": u.email, "name": u.name,
            "plan": u.plan.value if u.plan else "light",
            "is_active": u.is_active, "is_admin": u.is_admin,
            "stripe_customer_id": u.stripe_customer_id,
            "stripe_subscription_id": u.stripe_subscription_id,
            "sns_count": sns_count, "post_count": post_count, "success_count": success_count,
            "api_key": u.api_key,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "updated_at": u.updated_at.isoformat() if u.updated_at else None,
        })
    return result


@app.get("/api/admin/users/{user_id}")
async def admin_get_user(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理者用: ユーザー詳細"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    sns_accounts = db.query(SNSAccount).filter(SNSAccount.user_id == user_id).all()
    posts = db.query(PostHistory).filter(PostHistory.user_id == user_id).order_by(PostHistory.created_at.desc()).limit(20).all()
    trades = db.query(TradeDataRecord).filter(TradeDataRecord.user_id == user_id).order_by(TradeDataRecord.date.desc()).limit(10).all()

    return {
        "user": {
            "id": target.id, "email": target.email, "name": target.name,
            "plan": target.plan.value if target.plan else "light",
            "is_active": target.is_active, "is_admin": target.is_admin,
            "stripe_customer_id": target.stripe_customer_id,
            "stripe_subscription_id": target.stripe_subscription_id,
            "api_key": target.api_key,
            "created_at": target.created_at.isoformat() if target.created_at else None,
        },
        "sns_accounts": [
            {"id": a.id, "platform": a.platform.value, "is_enabled": a.is_enabled, "has_token": bool(a.access_token)}
            for a in sns_accounts
        ],
        "recent_posts": [
            {"id": p.id, "date": p.date, "platform": p.platform.value, "status": p.status.value, "created_at": p.created_at.isoformat() if p.created_at else None}
            for p in posts
        ],
        "recent_trades": [
            {"date": t.date, "net_profit": t.net_profit, "win_rate": t.win_rate, "total_trades": t.total_trades}
            for t in trades
        ],
    }


@app.post("/api/admin/users/{user_id}/plan")
async def admin_change_plan(
    user_id: int, data: AdminPlanChange,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理者用: ユーザーのプランを変更"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    plan_map = {"free": PlanType.FREE, "light": PlanType.LIGHT, "standard": PlanType.STANDARD, "premium": PlanType.PREMIUM}
    new_plan = plan_map.get(data.plan.lower())
    if not new_plan:
        raise HTTPException(status_code=400, detail="無効なプランです")

    target.plan = new_plan
    db.commit()
    return {"message": f"ユーザー {target.name} のプランを {data.plan} に変更しました"}


@app.post("/api/admin/users/{user_id}/toggle")
async def admin_toggle_user(
    user_id: int, data: AdminUserToggle,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理者用: ユーザーの有効/無効を切り替え"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    target.is_active = data.is_active
    db.commit()
    return {"message": f"ユーザー {target.name} を {'有効' if data.is_active else '無効'}にしました"}


@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """管理者用: ユーザーを削除"""
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    if target.is_admin:
        raise HTTPException(status_code=400, detail="管理者は削除できません")

    db.delete(target)
    db.commit()
    return {"message": f"ユーザー {target.name} を削除しました"}


# ============================================================
# カスタムテンプレートAPI
# ============================================================

BG_IMAGE_DIR = os.path.join(BASE_DIR, "data", "bg_images")
os.makedirs(BG_IMAGE_DIR, exist_ok=True)


@app.post("/api/templates/upload-bg")
async def upload_background_image(
    data: BgUploadRequest,
    user: User = Depends(get_current_user_by_jwt),
):
    """背景画像をBase64でアップロード"""
    import base64
    from PIL import Image as PILImage
    from io import BytesIO

    try:
        # Base64デコード（data:image/...;base64, プレフィックス対応）
        img_data = data.image_data
        if "," in img_data:
            img_data = img_data.split(",", 1)[1]
        raw = base64.b64decode(img_data)

        if len(raw) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="画像は5MB以下にしてください")

        img = PILImage.open(BytesIO(raw)).convert("RGB")
        img = img.resize((1080, 1080), PILImage.LANCZOS)

        import uuid as _uuid
        filename = f"{user.id}_{_uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(BG_IMAGE_DIR, filename)
        img.save(filepath, "JPEG", quality=95)

        return {"filename": filename}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"画像の処理に失敗しました: {str(e)}")


@app.get("/api/templates/bg-image/{filename}")
async def get_background_image(filename: str):
    """背景画像を配信"""
    filepath = os.path.join(BG_IMAGE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="画像が見つかりません")
    return FileResponse(filepath, media_type="image/jpeg")


@app.post("/api/templates/custom/save")
async def save_custom_template(
    data: CustomTemplateSaveRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db),
):
    """カスタムテンプレートを保存（新規/更新）"""
    import json

    config = {
        "background": data.background,
        "elements": [e.dict() for e in data.elements],
    }

    if data.template_id:
        tmpl = db.query(PostTemplate).filter(
            PostTemplate.id == data.template_id,
            PostTemplate.user_id == user.id,
        ).first()
        if not tmpl:
            raise HTTPException(status_code=404, detail="テンプレートが見つかりません")
        tmpl.name = data.name
        tmpl.config_json = json.dumps(config)
        tmpl.text_template = data.text_template
        tmpl.background_image_path = data.background
    else:
        # ユーザーあたり最大10テンプレート
        count = db.query(PostTemplate).filter(
            PostTemplate.user_id == user.id
        ).count()
        if count >= 10:
            raise HTTPException(status_code=400, detail="テンプレートは最大10個まで作成できます")

        tmpl = PostTemplate(
            user_id=user.id,
            name=data.name,
            template_type="custom",
            config_json=json.dumps(config),
            text_template=data.text_template,
            background_image_path=data.background,
            min_plan=PlanType.LIGHT,
        )
        db.add(tmpl)

    db.commit()
    db.refresh(tmpl)
    return {"id": tmpl.id, "name": tmpl.name, "message": "テンプレートを保存しました"}


@app.get("/api/templates/custom/list")
async def list_custom_templates(
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db),
):
    """ユーザーのカスタムテンプレート一覧"""
    import json

    templates = db.query(PostTemplate).filter(
        PostTemplate.user_id == user.id,
        PostTemplate.is_active == True,
    ).order_by(PostTemplate.created_at.desc()).all()

    return [
        {
            "id": t.id,
            "name": t.name,
            "config": json.loads(t.config_json) if t.config_json else {},
            "text_template": t.text_template or "",
            "background": t.background_image_path or "",
            "created_at": t.created_at.isoformat() if t.created_at else "",
        }
        for t in templates
    ]


@app.delete("/api/templates/custom/{template_id}")
async def delete_custom_template(
    template_id: int,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db),
):
    """カスタムテンプレートを削除"""
    tmpl = db.query(PostTemplate).filter(
        PostTemplate.id == template_id,
        PostTemplate.user_id == user.id,
    ).first()
    if not tmpl:
        raise HTTPException(status_code=404, detail="テンプレートが見つかりません")
    db.delete(tmpl)
    db.commit()
    return {"message": "テンプレートを削除しました"}


@app.post("/api/templates/custom/preview")
async def preview_custom_template(
    data: CustomTemplatePreviewRequest,
    user: User = Depends(get_current_user_by_jwt),
):
    """カスタムテンプレートのプレビュー画像を生成（Base64返却）"""
    sys.path.insert(0, str(BASE_DIR))
    from modules.custom_template_renderer import render_from_config

    config = {
        "background": data.background,
        "elements": [e.dict() for e in data.elements],
    }
    sample_data = {
        "date": datetime.now().strftime("%Y/%m/%d"),
        "net_profit": 17000,
        "total_trades": 12,
        "winning_trades": 8,
        "losing_trades": 4,
        "win_rate": 66.7,
        "cumulative_profit": 230000,
    }

    try:
        base64_img = render_from_config(
            config_json=config,
            trade_data=sample_data,
            bg_image_dir=BG_IMAGE_DIR,
            return_base64=True,
        )
        return {"image": f"data:image/jpeg;base64,{base64_img}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プレビュー生成に失敗: {str(e)}")


# ============================================================
# 動画エフェクトAPI
# ============================================================

class VideoGenerateRequest(BaseModel):
    custom_template_id: int
    effect_type: str

@app.get("/api/video/effects")
async def get_video_effects(
    user: User = Depends(get_current_user_by_jwt),
):
    """利用可能な動画エフェクト一覧を返す"""
    from modules.effect_video_generator import get_available_effects
    return get_available_effects()


@app.post("/api/video/generate")
async def generate_video_preview(
    data: VideoGenerateRequest,
    user: User = Depends(get_current_user_by_jwt),
    db: Session = Depends(get_db),
):
    """動画エフェクトプレビューを生成（プレミアムプラン以上）"""
    import base64 as b64

    # プレミアムプラン制限
    if user.plan not in (PlanType.PREMIUM, PlanType.ENTERPRISE):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="動画エフェクトはプレミアムプラン以上でご利用いただけます"
        )

    from modules.effect_video_generator import generate_effect_video, EFFECTS
    if data.effect_type not in EFFECTS:
        raise HTTPException(status_code=400, detail=f"不明なエフェクト: {data.effect_type}")

    # テンプレート画像を生成
    tmpl = db.query(PostTemplate).filter(
        PostTemplate.id == data.custom_template_id,
        PostTemplate.user_id == user.id,
    ).first()
    if not tmpl or not tmpl.config_json:
        raise HTTPException(status_code=404, detail="テンプレートが見つかりません")

    import json as _json
    config = _json.loads(tmpl.config_json)
    sample_data = {
        "date": datetime.now().strftime("%Y/%m/%d"),
        "net_profit": 17000,
        "total_trades": 12,
        "winning_trades": 8,
        "losing_trades": 4,
        "win_rate": 66.7,
        "cumulative_profit": 230000,
    }

    try:
        from modules.custom_template_renderer import render_from_config
        image_path = render_from_config(
            config_json=config,
            trade_data=sample_data,
            bg_image_dir=BG_IMAGE_DIR,
        )

        video_path = generate_effect_video(
            image_path=image_path,
            effect_type=data.effect_type,
            duration=5.0,
            fps=24,
        )

        with open(video_path, "rb") as f:
            video_b64 = b64.b64encode(f.read()).decode()

        # 一時ファイル削除
        try:
            os.remove(video_path)
            os.remove(image_path)
        except Exception:
            pass

        return {"video": f"data:video/mp4;base64,{video_b64}"}

    except Exception as e:
        logger.error(f"動画プレビュー生成失敗: {e}")
        raise HTTPException(status_code=500, detail=f"動画生成に失敗しました: {str(e)}")
