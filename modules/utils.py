"""
共通ユーティリティモジュール
============================
ロギング設定、データモデル、ヘルパー関数を提供します。
"""

import logging
import sys
from dataclasses import dataclass, asdict
from datetime import date, datetime
from pathlib import Path
from typing import Optional


def setup_logger(name: str, log_dir: Path, level: int = logging.INFO) -> logging.Logger:
    """
    ロガーを設定して返します。
    コンソールとファイルの両方にログを出力します。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # 既にハンドラが設定されている場合はスキップ
    if logger.handlers:
        return logger

    # ログディレクトリの作成
    log_dir.mkdir(parents=True, exist_ok=True)

    # フォーマッター
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # コンソールハンドラ
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # ファイルハンドラ（日付ごとのログファイル）
    today = date.today().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        log_dir / f"{today}.log",
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


@dataclass
class TradeData:
    """
    日次取引データを格納するデータクラス。
    MT4/MT5から取得したデータをこの形式に統一します。
    """
    date: str                          # 取引日 (YYYY-MM-DD)
    platform: str                      # "MT4" or "MT5"
    account_balance: float             # 口座残高
    daily_profit: float                # 日次利益（プラス分）
    daily_loss: float                  # 日次損失（マイナス分）
    net_profit: float                  # 日次純損益
    total_trades: int                  # 総取引回数
    winning_trades: int                # 勝ちトレード数
    losing_trades: int                 # 負けトレード数
    win_rate: float                    # 勝率 (%)
    cumulative_profit: float           # 累計損益
    currency: str = "JPY"             # 通貨

    def to_dict(self) -> dict:
        """辞書形式に変換します。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TradeData":
        """辞書からTradeDataを生成します。"""
        return cls(**data)

    @property
    def net_profit_str(self) -> str:
        """損益を符号付き文字列で返します（例: +17,000円）。"""
        sign = "+" if self.net_profit >= 0 else ""
        return f"{sign}{self.net_profit:,.0f}円"

    @property
    def cumulative_profit_str(self) -> str:
        """累計損益を符号付き文字列で返します。"""
        sign = "+" if self.cumulative_profit >= 0 else ""
        return f"{sign}{self.cumulative_profit:,.0f}円"

    @property
    def win_rate_str(self) -> str:
        """勝率を文字列で返します（例: 66.7% (8勝4敗)）。"""
        return f"{self.win_rate:.1f}% ({self.winning_trades}勝{self.losing_trades}敗)"

    @property
    def is_profitable(self) -> bool:
        """日次損益がプラスかどうかを返します。"""
        return self.net_profit >= 0


def format_date_jp(date_str: str) -> str:
    """
    日付文字列を日本語形式に変換します。
    例: "2026-03-10" → "2026/03/10"
    """
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%Y/%m/%d")


def create_sample_trade_data() -> TradeData:
    """
    テスト用のサンプル取引データを生成します。
    """
    return TradeData(
        date=date.today().strftime("%Y-%m-%d"),
        platform="MT5",
        account_balance=1500000,
        daily_profit=25000,
        daily_loss=-8000,
        net_profit=17000,
        total_trades=12,
        winning_trades=8,
        losing_trades=4,
        win_rate=66.7,
        cumulative_profit=350000,
        currency="JPY"
    )
