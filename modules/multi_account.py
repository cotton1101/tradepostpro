"""
TradePost Pro - 複数口座対応モジュール
MT4/MT5の複数口座データを統合・集計する
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Dict, List, Optional

from modules.utils import TradeData

logger = logging.getLogger(__name__)


@dataclass
class AccountConfig:
    """口座設定"""
    account_id: str
    account_name: str
    platform: str  # "mt4" or "mt5"
    server: str = ""
    login: int = 0
    password: str = ""
    enabled: bool = True
    # MT4の場合のCSVパス
    csv_path: str = ""
    # MT5の場合の接続情報
    mt5_path: str = ""


@dataclass
class AccountTradeData:
    """口座別取引データ"""
    account_id: str
    account_name: str
    platform: str
    trade_data: TradeData
    raw_trades: List[Dict] = field(default_factory=list)


class MultiAccountManager:
    """複数口座マネージャー"""

    def __init__(self, accounts: Optional[List[AccountConfig]] = None):
        self.accounts: List[AccountConfig] = accounts or []
        self._account_data: Dict[str, AccountTradeData] = {}

    def add_account(self, account: AccountConfig):
        """口座を追加"""
        self.accounts.append(account)
        logger.info(f"口座追加: {account.account_name} ({account.platform})")

    def remove_account(self, account_id: str):
        """口座を削除"""
        self.accounts = [a for a in self.accounts if a.account_id != account_id]
        self._account_data.pop(account_id, None)
        logger.info(f"口座削除: {account_id}")

    def get_enabled_accounts(self) -> List[AccountConfig]:
        """有効な口座一覧を取得"""
        return [a for a in self.accounts if a.enabled]

    def fetch_all_accounts(self, target_date: Optional[date] = None) -> List[AccountTradeData]:
        """全口座のデータを取得"""
        target_date = target_date or date.today()
        results = []

        for account in self.get_enabled_accounts():
            try:
                if account.platform == "mt5":
                    data = self._fetch_mt5_data(account, target_date)
                elif account.platform == "mt4":
                    data = self._fetch_mt4_data(account, target_date)
                else:
                    logger.warning(f"不明なプラットフォーム: {account.platform}")
                    continue

                if data:
                    self._account_data[account.account_id] = data
                    results.append(data)
                    logger.info(
                        f"口座 {account.account_name}: "
                        f"損益={data.trade_data.daily_profit:+,.0f}円, "
                        f"取引={data.trade_data.total_trades}回"
                    )
            except Exception as e:
                logger.error(f"口座 {account.account_name} のデータ取得に失敗: {e}")

        return results

    def _fetch_mt5_data(self, account: AccountConfig, target_date: date) -> Optional[AccountTradeData]:
        """MT5口座のデータを取得"""
        try:
            from modules.mt5_data import MT5DataFetcher
            fetcher = MT5DataFetcher(
                mt5_path=account.mt5_path or None,
                login=account.login,
                password=account.password,
                server=account.server,
            )
            trade_data = fetcher.fetch_daily_data(target_date)
            if trade_data:
                return AccountTradeData(
                    account_id=account.account_id,
                    account_name=account.account_name,
                    platform="mt5",
                    trade_data=trade_data,
                )
        except ImportError:
            logger.warning("MT5モジュールが利用できません")
        except Exception as e:
            logger.error(f"MT5データ取得エラー: {e}")
        return None

    def _fetch_mt4_data(self, account: AccountConfig, target_date: date) -> Optional[AccountTradeData]:
        """MT4口座のデータを取得"""
        try:
            from modules.mt4_data import MT4DataReader
            reader = MT4DataReader(csv_path=account.csv_path)
            trade_data = reader.read_daily_data(target_date)
            if trade_data:
                return AccountTradeData(
                    account_id=account.account_id,
                    account_name=account.account_name,
                    platform="mt4",
                    trade_data=trade_data,
                )
        except ImportError:
            logger.warning("MT4モジュールが利用できません")
        except Exception as e:
            logger.error(f"MT4データ取得エラー: {e}")
        return None

    def aggregate_data(self, account_data_list: Optional[List[AccountTradeData]] = None) -> TradeData:
        """複数口座のデータを合算"""
        if account_data_list is None:
            account_data_list = list(self._account_data.values())

        if not account_data_list:
            return TradeData(
                date=date.today().isoformat(),
                platform="multi",
                account_balance=0,
                daily_profit=0,
                daily_loss=0,
                net_profit=0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                cumulative_profit=0,
            )

        total_daily_profit = sum(d.trade_data.daily_profit for d in account_data_list)
        total_daily_loss = sum(d.trade_data.daily_loss for d in account_data_list)
        total_net = sum(d.trade_data.net_profit for d in account_data_list)
        total_trades = sum(d.trade_data.total_trades for d in account_data_list)
        total_wins = sum(d.trade_data.winning_trades for d in account_data_list)
        total_losses = sum(d.trade_data.losing_trades for d in account_data_list)
        total_cumulative = sum(d.trade_data.cumulative_profit for d in account_data_list)
        total_balance = sum(d.trade_data.account_balance for d in account_data_list)

        win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0

        return TradeData(
            date=account_data_list[0].trade_data.date,
            platform="multi",
            account_balance=total_balance,
            daily_profit=total_daily_profit,
            daily_loss=total_daily_loss,
            net_profit=total_net,
            total_trades=total_trades,
            winning_trades=total_wins,
            losing_trades=total_losses,
            win_rate=round(win_rate, 1),
            cumulative_profit=total_cumulative,
        )

    def get_account_summary(self) -> List[Dict]:
        """口座別サマリーを取得"""
        summary = []
        for account_id, data in self._account_data.items():
            summary.append({
                "account_id": account_id,
                "account_name": data.account_name,
                "platform": data.platform,
                "net_profit": data.trade_data.net_profit,
                "total_trades": data.trade_data.total_trades,
                "win_rate": data.trade_data.win_rate,
            })
        return summary

    def to_json(self) -> str:
        """口座設定をJSON形式で出力"""
        accounts = []
        for a in self.accounts:
            accounts.append({
                "account_id": a.account_id,
                "account_name": a.account_name,
                "platform": a.platform,
                "server": a.server,
                "login": a.login,
                "enabled": a.enabled,
            })
        return json.dumps(accounts, ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "MultiAccountManager":
        """JSONから口座設定を読み込み"""
        data = json.loads(json_str)
        accounts = []
        for item in data:
            accounts.append(AccountConfig(
                account_id=item["account_id"],
                account_name=item["account_name"],
                platform=item["platform"],
                server=item.get("server", ""),
                login=item.get("login", 0),
                enabled=item.get("enabled", True),
            ))
        return cls(accounts=accounts)


if __name__ == "__main__":
    # テスト
    manager = MultiAccountManager()

    # サンプル口座追加
    manager.add_account(AccountConfig(
        account_id="acc_001",
        account_name="XM口座1（MT5）",
        platform="mt5",
        server="XMTrading-MT5",
        login=12345678,
    ))
    manager.add_account(AccountConfig(
        account_id="acc_002",
        account_name="XM口座2（MT4）",
        platform="mt4",
        server="XMTrading-Real",
        login=87654321,
        csv_path="/path/to/mt4/trades.csv",
    ))

    print(f"有効口座数: {len(manager.get_enabled_accounts())}")
    print(f"口座設定JSON:\n{manager.to_json()}")

    # サンプルデータで合算テスト
    sample_data = [
        AccountTradeData(
            account_id="acc_001",
            account_name="XM口座1",
            platform="mt5",
            trade_data=TradeData(
                date="2026-03-11",
                platform="mt5",
                account_balance=500000,
                daily_profit=15000,
                daily_loss=3000,
                net_profit=12000,
                total_trades=8,
                winning_trades=6,
                losing_trades=2,
                win_rate=75.0,
                cumulative_profit=150000,
            ),
        ),
        AccountTradeData(
            account_id="acc_002",
            account_name="XM口座2",
            platform="mt4",
            trade_data=TradeData(
                date="2026-03-11",
                platform="mt4",
                account_balance=300000,
                daily_profit=8000,
                daily_loss=3000,
                net_profit=5000,
                total_trades=4,
                winning_trades=2,
                losing_trades=2,
                win_rate=50.0,
                cumulative_profit=80000,
            ),
        ),
    ]

    aggregated = manager.aggregate_data(sample_data)
    print(f"\n=== 合算結果 ===")
    print(f"純損益: {aggregated.net_profit:+,}円")
    print(f"取引: {aggregated.total_trades}回 ({aggregated.winning_trades}勝{aggregated.losing_trades}敗)")
    print(f"勝率: {aggregated.win_rate}%")
    print(f"累計: {aggregated.cumulative_profit:+,}円")
    print(f"合算残高: {aggregated.account_balance:,.0f}円")
