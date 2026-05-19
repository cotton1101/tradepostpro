"""
XM Affiliate SNS Auto Poster - 設定ファイル
============================================
各種APIキーやサーバー設定を管理します。
実運用時は環境変数または .env ファイルから読み込みます。
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルの読み込み
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ============================================================
# 基本設定
# ============================================================
APP_NAME = "XM Affiliate SNS Auto Poster"
VERSION = "1.0.0"
TIMEZONE = "Asia/Tokyo"
LOG_DIR = BASE_DIR / "logs"
ASSETS_DIR = BASE_DIR / "assets"
TEMPLATES_DIR = BASE_DIR / "templates"

# ============================================================
# MT5 設定
# ============================================================
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "XMTrading-MT5")
MT5_PATH = os.getenv("MT5_PATH", r"C:\Program Files\MetaTrader 5\terminal64.exe")

# ============================================================
# MT4 設定（CSV出力パス）
# ============================================================
MT4_CSV_DIR = os.getenv("MT4_CSV_DIR", r"C:\Users\User\AppData\Roaming\MetaQuotes\Terminal\{TERMINAL_ID}\MQL4\Files")

# ============================================================
# X (Twitter) API 設定
# ============================================================
X_API_KEY = os.getenv("X_API_KEY", "")
X_API_SECRET = os.getenv("X_API_SECRET", "")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN", "")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET", "")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")

# ============================================================
# Instagram API 設定
# ============================================================
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
INSTAGRAM_USER_ID = os.getenv("INSTAGRAM_USER_ID", "")

# ============================================================
# Threads API 設定
# ============================================================
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN", "")
THREADS_USER_ID = os.getenv("THREADS_USER_ID", "")

# ============================================================
# TikTok API 設定
# ============================================================
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "")

# ============================================================
# LINE Messaging API 設定
# ============================================================
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
LINE_GROUP_ID = os.getenv("LINE_GROUP_ID", "")

# ============================================================
# LINE オープンチャット誘導URL
# ============================================================
LINE_OPENCHAT_URL = os.getenv("LINE_OPENCHAT_URL", "https://line.me/ti/g2/xxxxx")

# ============================================================
# 投稿設定
# ============================================================
POST_SCHEDULE_HOUR = int(os.getenv("POST_SCHEDULE_HOUR", "7"))
POST_SCHEDULE_MINUTE = int(os.getenv("POST_SCHEDULE_MINUTE", "0"))

# ============================================================
# 画像生成設定
# ============================================================
IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1080
FONT_PATH = str(ASSETS_DIR / "fonts" / "NotoSansJP-Bold.ttf")
TEMPLATE_IMAGE = os.getenv("TEMPLATE_IMAGE", "default_template.png")

# ============================================================
# ハッシュタグ設定
# ============================================================
HASHTAGS = os.getenv(
    "HASHTAGS",
    "#FX #XM #トレード結果 #自動売買 #海外FX #XMアフィリエイト"
)

# ============================================================
# ConoHa オブジェクトストレージ設定
# ============================================================
CONOHA_ACCESS_KEY = os.getenv("CONOHA_ACCESS_KEY", "")
CONOHA_SECRET_KEY = os.getenv("CONOHA_SECRET_KEY", "")
CONOHA_BUCKET_NAME = os.getenv("CONOHA_BUCKET_NAME", "sns-images")
CONOHA_ENDPOINT_URL = os.getenv("CONOHA_ENDPOINT_URL", "https://s3.c3j1.conoha.io")
CONOHA_PUBLIC_BASE_URL = os.getenv("CONOHA_PUBLIC_BASE_URL", "")

# ============================================================
# Stripe 決済設定
# ============================================================
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

# ============================================================
# SaaS バックエンドAPI設定
# ============================================================
BACKEND_API_URL = os.getenv("BACKEND_API_URL", "")
USER_API_KEY = os.getenv("USER_API_KEY", "")
