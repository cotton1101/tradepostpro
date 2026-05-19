"""
MT5 データ取得モジュール
========================
MetaTrader 5のPython APIを使用して、日次の取引データを取得します。

【前提条件】
- Windows VPS上で実行すること
- MetaTrader 5がインストール・起動済みであること
- pip install MetaTrader5 でパッケージをインストール済みであること

【使い方】
    from modules.mt5_data import MT5DataFetcher
    
    fetcher = MT5DataFetcher(
        login=12345678,
        password="your_password",
        server="XMTrading-MT5",
        path=r"C:\\Program Files\\MetaTrader 5\\terminal64.exe"
    )
    trade_data = fetcher.fetch_daily_data()
    print(trade_data.net_profit_str)
"""

import sys
import json
import logging
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.utils import TradeData, setup_logger

logger = logging.getLogger(__name__)


class MT5DataFetcher:
    """
    MetaTrader 5からデータを取得するクラス。
    Windows VPS上でのみ動作します。
    """

    def __init__(
        self,
        login: int,
        password: str,
        server: str,
        path: str = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    ):
        self.login = login
        self.password = password
        self.server = server
        self.path = path
        self._mt5 = None

    def _import_mt5(self):
        """MT5モジュールをインポートします（Windows環境でのみ利用可能）。"""
        try:
            import MetaTrader5 as mt5
            self._mt5 = mt5
            return mt5
        except ImportError:
            raise ImportError(
                "MetaTrader5パッケージがインストールされていません。\n"
                "Windows VPS上で以下のコマンドを実行してください:\n"
                "  pip install MetaTrader5"
            )

    def connect(self) -> bool:
        """MT5に接続します。"""
        mt5 = self._import_mt5()

        # MT5の初期化
        if not mt5.initialize(
            path=self.path,
            login=self.login,
            password=self.password,
            server=self.server
        ):
            error = mt5.last_error()
            logger.error(f"MT5初期化失敗: {error}")
            return False

        # アカウント情報の確認
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("アカウント情報の取得に失敗しました")
            return False

        logger.info(
            f"MT5接続成功: アカウント={account_info.login}, "
            f"サーバー={account_info.server}, "
            f"残高={account_info.balance:,.0f} {account_info.currency}"
        )
        return True

    def disconnect(self):
        """MT5から切断します。"""
        if self._mt5:
            self._mt5.shutdown()
            logger.info("MT5から切断しました")

    def fetch_daily_data(
        self,
        target_date: Optional[date] = None
    ) -> TradeData:
        """
        指定日の取引データを取得します。
        
        Args:
            target_date: 取得対象日（デフォルト: 前日）
        
        Returns:
            TradeData: 日次取引データ
        """
        mt5 = self._mt5
        if mt5 is None:
            raise RuntimeError("MT5に接続されていません。connect()を先に呼び出してください。")

        # 対象日の設定（デフォルトは前日）
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        # 対象日の開始・終了時刻（UTC）
        from_dt = datetime.combine(target_date, datetime.min.time())
        to_dt = datetime.combine(target_date + timedelta(days=1), datetime.min.time())

        logger.info(f"取引データ取得中: {target_date}")

        # アカウント情報
        account_info = mt5.account_info()
        if account_info is None:
            raise RuntimeError("アカウント情報の取得に失敗しました")

        # 取引履歴（ディール）の取得
        deals = mt5.history_deals_get(from_dt, to_dt)

        if deals is None or len(deals) == 0:
            logger.warning(f"{target_date}の取引データがありません")
            return TradeData(
                date=target_date.strftime("%Y-%m-%d"),
                platform="MT5",
                account_balance=account_info.balance,
                daily_profit=0,
                daily_loss=0,
                net_profit=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                cumulative_profit=account_info.profit,
                currency=account_info.currency
            )

        # 損益の集計（DEAL_TYPE_BUY=0, DEAL_TYPE_SELL=1 のみ対象）
        daily_profit = 0.0
        daily_loss = 0.0
        winning_trades = 0
        losing_trades = 0
        total_trades = 0

        for deal in deals:
            # エントリー（DEAL_ENTRY_OUT=1）のディールのみ集計
            if deal.entry == 1:  # DEAL_ENTRY_OUT
                total_trades += 1
                profit = deal.profit + deal.swap + deal.commission

                if profit >= 0:
                    daily_profit += profit
                    winning_trades += 1
                else:
                    daily_loss += profit
                    losing_trades += 1

        net_profit = daily_profit + daily_loss
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

        trade_data = TradeData(
            date=target_date.strftime("%Y-%m-%d"),
            platform="MT5",
            account_balance=account_info.balance,
            daily_profit=daily_profit,
            daily_loss=daily_loss,
            net_profit=net_profit,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 1),
            cumulative_profit=account_info.profit,
            currency=account_info.currency if account_info.currency else "JPY"
        )

        logger.info(
            f"取引データ取得完了: 損益={trade_data.net_profit_str}, "
            f"勝率={trade_data.win_rate_str}, "
            f"取引回数={trade_data.total_trades}回"
        )

        return trade_data

    def fetch_and_save(
        self,
        output_path: Optional[Path] = None,
        target_date: Optional[date] = None
    ) -> TradeData:
        """
        取引データを取得してJSONファイルに保存します。
        
        Args:
            output_path: 出力先パス（デフォルト: プロジェクトルート/data/）
            target_date: 取得対象日
        
        Returns:
            TradeData: 日次取引データ
        """
        trade_data = self.fetch_daily_data(target_date)

        # 出力先の設定
        if output_path is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            output_path = data_dir / f"trade_data_{trade_data.date}.json"

        # JSONファイルに保存
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(trade_data.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"取引データを保存しました: {output_path}")
        return trade_data


def main():
    """
    MT5データ取得のメインエントリーポイント。
    コマンドラインから直接実行する場合に使用します。
    
    使い方:
        python -m modules.mt5_data
    """
    from config.settings import (
        MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH, LOG_DIR
    )

    # ロガーの設定
    setup_logger("modules.mt5_data", LOG_DIR)

    fetcher = MT5DataFetcher(
        login=MT5_LOGIN,
        password=MT5_PASSWORD,
        server=MT5_SERVER,
        path=MT5_PATH
    )

    try:
        if fetcher.connect():
            trade_data = fetcher.fetch_and_save()
            print(f"\n取得結果:")
            print(f"  日付: {trade_data.date}")
            print(f"  損益: {trade_data.net_profit_str}")
            print(f"  勝率: {trade_data.win_rate_str}")
            print(f"  取引回数: {trade_data.total_trades}回")
            print(f"  累計損益: {trade_data.cumulative_profit_str}")
        else:
            print("MT5への接続に失敗しました。設定を確認してください。")
            sys.exit(1)
    finally:
        fetcher.disconnect()


if __name__ == "__main__":
    main()
