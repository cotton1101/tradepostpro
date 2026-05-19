"""
MT4 データ取得モジュール（CSV読み込み）
=======================================
MT4のEA（DailyTradeExporter.mq4）が出力したCSVファイルを読み込み、
TradeDataオブジェクトに変換します。

【前提条件】
- MT4上でDailyTradeExporter EAが稼働し、CSVが出力されていること
- CSVファイルのパスが正しく設定されていること

【使い方】
    from modules.mt4_data import MT4DataReader
    
    reader = MT4DataReader(csv_dir=r"C:\\path\\to\\MQL4\\Files")
    trade_data = reader.read_latest()
    print(trade_data.net_profit_str)
"""

import csv
import glob
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.utils import TradeData, setup_logger

logger = logging.getLogger(__name__)


class MT4DataReader:
    """
    MT4のEAが出力したCSVファイルを読み込むクラス。
    """

    def __init__(self, csv_dir: str):
        """
        Args:
            csv_dir: MT4のMQL4/Filesディレクトリのパス
        """
        self.csv_dir = Path(csv_dir)

    def read_by_date(self, target_date: Optional[date] = None) -> TradeData:
        """
        指定日のCSVファイルを読み込みます。
        
        Args:
            target_date: 取得対象日（デフォルト: 前日）
        
        Returns:
            TradeData: 日次取引データ
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        date_str = target_date.strftime("%Y.%m.%d")
        file_pattern = f"daily_trade_data_{date_str}*.csv"

        # 別の日付フォーマットも試す
        date_str_alt = target_date.strftime("%Y-%m-%d")
        file_pattern_alt = f"daily_trade_data_{date_str_alt}*.csv"

        csv_files = list(self.csv_dir.glob(file_pattern))
        if not csv_files:
            csv_files = list(self.csv_dir.glob(file_pattern_alt))

        if not csv_files:
            logger.warning(f"{target_date}のCSVファイルが見つかりません: {self.csv_dir}")
            raise FileNotFoundError(
                f"CSVファイルが見つかりません: {self.csv_dir / file_pattern}"
            )

        csv_path = csv_files[0]
        logger.info(f"CSVファイル読み込み: {csv_path}")

        return self._parse_csv(csv_path)

    def read_latest(self) -> TradeData:
        """
        最新のCSVファイルを読み込みます。
        
        Returns:
            TradeData: 日次取引データ
        """
        csv_files = sorted(
            self.csv_dir.glob("daily_trade_data_*.csv"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        if not csv_files:
            raise FileNotFoundError(
                f"CSVファイルが見つかりません: {self.csv_dir}"
            )

        csv_path = csv_files[0]
        logger.info(f"最新CSVファイル読み込み: {csv_path}")

        return self._parse_csv(csv_path)

    def _parse_csv(self, csv_path: Path) -> TradeData:
        """
        CSVファイルをパースしてTradeDataに変換します。
        
        Args:
            csv_path: CSVファイルのパス
        
        Returns:
            TradeData: 日次取引データ
        """
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            raise ValueError(f"CSVファイルにデータがありません: {csv_path}")

        row = rows[0]

        trade_data = TradeData(
            date=row["date"].replace(".", "-"),
            platform=row.get("platform", "MT4"),
            account_balance=float(row["account_balance"]),
            daily_profit=float(row["daily_profit"]),
            daily_loss=float(row["daily_loss"]),
            net_profit=float(row["net_profit"]),
            total_trades=int(row["total_trades"]),
            winning_trades=int(row["winning_trades"]),
            losing_trades=int(row["losing_trades"]),
            win_rate=float(row["win_rate"]),
            cumulative_profit=float(row["cumulative_profit"]),
            currency=row.get("currency", "JPY")
        )

        logger.info(
            f"CSV読み込み完了: 損益={trade_data.net_profit_str}, "
            f"勝率={trade_data.win_rate_str}"
        )

        return trade_data

    def read_and_save_json(
        self,
        output_path: Optional[Path] = None,
        target_date: Optional[date] = None
    ) -> TradeData:
        """
        CSVを読み込んでJSONファイルに保存します。
        
        Args:
            output_path: JSON出力先パス
            target_date: 取得対象日
        
        Returns:
            TradeData: 日次取引データ
        """
        trade_data = self.read_by_date(target_date)

        if output_path is None:
            data_dir = Path(__file__).resolve().parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            output_path = data_dir / f"trade_data_{trade_data.date}.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(trade_data.to_dict(), f, ensure_ascii=False, indent=2)

        logger.info(f"JSONファイルに保存しました: {output_path}")
        return trade_data


def main():
    """MT4データ読み込みのメインエントリーポイント。"""
    from config.settings import MT4_CSV_DIR, LOG_DIR

    setup_logger("modules.mt4_data", LOG_DIR)

    reader = MT4DataReader(csv_dir=MT4_CSV_DIR)

    try:
        trade_data = reader.read_latest()
        print(f"\n取得結果:")
        print(f"  日付: {trade_data.date}")
        print(f"  損益: {trade_data.net_profit_str}")
        print(f"  勝率: {trade_data.win_rate_str}")
        print(f"  取引回数: {trade_data.total_trades}回")
        print(f"  累計損益: {trade_data.cumulative_profit_str}")
    except FileNotFoundError as e:
        print(f"エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
