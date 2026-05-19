"""
データベースモデル定義
======================
SQLAlchemy + SQLiteを使用したデータベーススキーマ定義。
ConoHa VPS上ではMySQL/MariaDBに切り替え可能です。
"""

import enum
from datetime import datetime

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, Boolean,
    DateTime, Text, Enum, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# データベースURL（本番ではMySQLに変更）
import os
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/tradepost.db"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================
# Enum定義
# ============================================================

class PlanType(str, enum.Enum):
    """サブスクリプションプラン"""
    FREE = "free"             # 無料プラン（登録直後）
    LIGHT = "light"           # ライト: 1,980円/月
    STANDARD = "standard"     # スタンダード: 2,980円/月
    PREMIUM = "premium"       # プレミアム: 4,980円/月


class PlatformType(str, enum.Enum):
    """SNSプラットフォーム"""
    X = "x"
    INSTAGRAM = "instagram"
    THREADS = "threads"
    TIKTOK = "tiktok"
    LINE = "line"


class PostStatus(str, enum.Enum):
    """投稿ステータス"""
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ============================================================
# テーブル定義
# ============================================================

class User(Base):
    """ユーザーテーブル"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    plan = Column(Enum(PlanType), default=PlanType.FREE, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    api_key = Column(String(255), unique=True, nullable=True, index=True)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    sns_accounts = relationship("SNSAccount", back_populates="user", cascade="all, delete-orphan")
    trade_data = relationship("TradeDataRecord", back_populates="user", cascade="all, delete-orphan")
    post_history = relationship("PostHistory", back_populates="user", cascade="all, delete-orphan")
    mt_settings = relationship("MTSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")


class SNSAccount(Base):
    """SNSアカウント設定テーブル"""
    __tablename__ = "sns_accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    platform = Column(Enum(PlatformType), nullable=False)
    is_enabled = Column(Boolean, default=True, nullable=False)

    # 各プラットフォーム共通のトークン格納
    access_token = Column(Text, nullable=True)
    access_token_secret = Column(Text, nullable=True)
    api_key = Column(Text, nullable=True)
    api_secret = Column(Text, nullable=True)
    user_id_external = Column(String(255), nullable=True)  # 外部ユーザーID
    group_id = Column(String(255), nullable=True)  # LINE用グループID

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="sns_accounts")


class MTSettings(Base):
    """MT4/MT5接続設定テーブル"""
    __tablename__ = "mt_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    platform = Column(String(10), default="MT5", nullable=False)  # "MT4" or "MT5"
    login = Column(Integer, nullable=True)
    password_encrypted = Column(Text, nullable=True)
    server = Column(String(255), nullable=True)
    path = Column(String(500), nullable=True)
    csv_dir = Column(String(500), nullable=True)  # MT4用CSVディレクトリ

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="mt_settings")


class TradeDataRecord(Base):
    """取引データ記録テーブル"""
    __tablename__ = "trade_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    platform = Column(String(10), nullable=False)
    account_balance = Column(Float, default=0)
    daily_profit = Column(Float, default=0)
    daily_loss = Column(Float, default=0)
    net_profit = Column(Float, default=0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)
    cumulative_profit = Column(Float, default=0)
    currency = Column(String(10), default="JPY")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # リレーション
    user = relationship("User", back_populates="trade_data")


class PostHistory(Base):
    """投稿履歴テーブル"""
    __tablename__ = "post_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String(10), nullable=False)
    platform = Column(Enum(PlatformType), nullable=False)
    status = Column(Enum(PostStatus), default=PostStatus.PENDING, nullable=False)
    post_text = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    external_post_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # リレーション
    user = relationship("User", back_populates="post_history")


class PostTemplate(Base):
    """投稿テンプレートテーブル"""
    __tablename__ = "post_templates"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # NULL=プリセット
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    template_type = Column(String(50), default="basic", nullable=False)  # basic, premium, custom
    image_template_path = Column(String(500), nullable=True)
    background_image_path = Column(String(500), nullable=True)  # カスタム背景画像パス
    config_json = Column(Text, nullable=True)  # 要素配置JSON設定
    text_template = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    min_plan = Column(Enum(PlanType), default=PlanType.LIGHT, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    user = relationship("User", backref="templates")


# ============================================================
# データベース初期化
# ============================================================

def init_db():
    """データベースとテーブルを作成します。"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """データベースセッションを取得するジェネレータ。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
