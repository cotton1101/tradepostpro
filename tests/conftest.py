"""
TradePost Pro - テスト共通フィクスチャ・モックデータ
"""

import os
import sys
import pytest
from datetime import datetime, date
from unittest.mock import MagicMock, patch

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.utils import TradeData


# ============================================================
# モックデータ
# ============================================================

SAMPLE_TRADE_DATA_PROFIT = TradeData(
    date=date.today().strftime("%Y-%m-%d"),
    platform="MT5",
    account_balance=1250000.0,
    daily_profit=45200.0,
    daily_loss=-10000.0,
    net_profit=35200.0,
    total_trades=12,
    winning_trades=9,
    losing_trades=3,
    win_rate=75.0,
    cumulative_profit=250000.0,
    currency="JPY",
)

SAMPLE_TRADE_DATA_LOSS = TradeData(
    date=date.today().strftime("%Y-%m-%d"),
    platform="MT5",
    account_balance=980000.0,
    daily_profit=5000.0,
    daily_loss=-20800.0,
    net_profit=-15800.0,
    total_trades=8,
    winning_trades=3,
    losing_trades=5,
    win_rate=37.5,
    cumulative_profit=-20000.0,
    currency="JPY",
)

SAMPLE_TRADE_DATA_ZERO = TradeData(
    date=date.today().strftime("%Y-%m-%d"),
    platform="MT4",
    account_balance=1000000.0,
    daily_profit=0.0,
    daily_loss=0.0,
    net_profit=0.0,
    total_trades=0,
    winning_trades=0,
    losing_trades=0,
    win_rate=0.0,
    cumulative_profit=0.0,
    currency="JPY",
)


# ============================================================
# フィクスチャ
# ============================================================

@pytest.fixture
def trade_data_profit():
    """利益が出ているサンプルデータ"""
    return SAMPLE_TRADE_DATA_PROFIT


@pytest.fixture
def trade_data_loss():
    """損失が出ているサンプルデータ"""
    return SAMPLE_TRADE_DATA_LOSS


@pytest.fixture
def trade_data_zero():
    """取引なしのサンプルデータ"""
    return SAMPLE_TRADE_DATA_ZERO


@pytest.fixture
def output_dir(tmp_path):
    """テスト用出力ディレクトリ"""
    out = tmp_path / "output"
    out.mkdir()
    return str(out)


@pytest.fixture
def mock_env_vars():
    """テスト用環境変数のモック"""
    env_vars = {
        "X_API_KEY": "test_api_key",
        "X_API_SECRET": "test_api_secret",
        "X_ACCESS_TOKEN": "test_access_token",
        "X_ACCESS_SECRET": "test_access_secret",
        "INSTAGRAM_ACCESS_TOKEN": "test_ig_token",
        "INSTAGRAM_ACCOUNT_ID": "test_ig_id",
        "THREADS_ACCESS_TOKEN": "test_threads_token",
        "THREADS_ACCOUNT_ID": "test_threads_id",
        "TIKTOK_CLIENT_KEY": "test_tiktok_key",
        "TIKTOK_CLIENT_SECRET": "test_tiktok_secret",
        "LINE_CHANNEL_ACCESS_TOKEN": "test_line_token",
        "LINE_GROUP_ID": "test_line_group",
        "LINE_NOTIFY_TOKEN": "test_line_notify",
        "CONOHA_TENANT_ID": "test_tenant",
        "CONOHA_API_USER": "test_user",
        "CONOHA_API_PASSWORD": "test_pass",
        "STRIPE_SECRET_KEY": "sk_test_xxxx",
        "STRIPE_WEBHOOK_SECRET": "whsec_test_xxxx",
    }
    with patch.dict(os.environ, env_vars):
        yield env_vars
