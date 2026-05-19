"""
TradePost Pro - MT4/MT5 接続テストツール
==========================================
ユーザーがMT4/MT5との接続を確認するためのテストスクリプトです。

【使い方】
  # MT5接続テスト
  python tools/connection_test.py --platform mt5

  # MT4接続テスト（CSVファイル確認）
  python tools/connection_test.py --platform mt4 --csv-path /path/to/trades.csv

  # API接続テスト（バックエンドAPI）
  python tools/connection_test.py --api --api-url https://api.example.com

  # 全テスト実行
  python tools/connection_test.py --all
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# カラー出力
class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    END = "\033[0m"


def print_header(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{Colors.END}\n")


def print_pass(msg: str):
    print(f"  {Colors.GREEN}[PASS]{Colors.END} {msg}")


def print_fail(msg: str):
    print(f"  {Colors.RED}[FAIL]{Colors.END} {msg}")


def print_warn(msg: str):
    print(f"  {Colors.YELLOW}[WARN]{Colors.END} {msg}")


def print_info(msg: str):
    print(f"  {Colors.BLUE}[INFO]{Colors.END} {msg}")


# ============================================================
# MT5 接続テスト
# ============================================================

def test_mt5_connection():
    """MT5 Python APIの接続テスト"""
    print_header("MT5 接続テスト")

    results = {"passed": 0, "failed": 0, "warnings": 0}

    # 1. MetaTrader5パッケージの確認
    print_info("MetaTrader5パッケージの確認...")
    try:
        import MetaTrader5 as mt5
        print_pass(f"MetaTrader5 パッケージ: バージョン {mt5.__version__}")
        results["passed"] += 1
    except ImportError:
        print_fail("MetaTrader5 パッケージがインストールされていません")
        print_info("インストール: pip install MetaTrader5")
        print_info("※ Windows環境でのみ動作します")
        results["failed"] += 1
        return results

    # 2. MT5ターミナルへの接続
    print_info("MT5ターミナルへの接続...")
    try:
        if mt5.initialize():
            print_pass("MT5ターミナルに接続成功")
            results["passed"] += 1
        else:
            error = mt5.last_error()
            print_fail(f"MT5ターミナルに接続失敗: {error}")
            print_info("MT5ターミナルが起動しているか確認してください")
            results["failed"] += 1
            return results
    except Exception as e:
        print_fail(f"MT5接続エラー: {e}")
        results["failed"] += 1
        return results

    # 3. アカウント情報の取得
    print_info("アカウント情報の取得...")
    try:
        account = mt5.account_info()
        if account:
            print_pass(f"アカウントID: {account.login}")
            print_pass(f"サーバー: {account.server}")
            print_pass(f"残高: {account.balance:,.0f} {account.currency}")
            print_pass(f"有効証拠金: {account.equity:,.0f} {account.currency}")
            results["passed"] += 4
        else:
            print_fail("アカウント情報の取得に失敗")
            results["failed"] += 1
    except Exception as e:
        print_fail(f"アカウント情報取得エラー: {e}")
        results["failed"] += 1

    # 4. 取引履歴の取得
    print_info("取引履歴の取得テスト（過去7日間）...")
    try:
        from_date = datetime.now() - timedelta(days=7)
        to_date = datetime.now()
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is not None:
            print_pass(f"取引履歴: {len(deals)}件取得")
            results["passed"] += 1
        else:
            print_warn("取引履歴が0件です（過去7日間に取引がない可能性）")
            results["warnings"] += 1
    except Exception as e:
        print_fail(f"取引履歴取得エラー: {e}")
        results["failed"] += 1

    # 5. ポジション情報の取得
    print_info("現在のポジション情報...")
    try:
        positions = mt5.positions_get()
        if positions is not None:
            print_pass(f"オープンポジション: {len(positions)}件")
            results["passed"] += 1
        else:
            print_pass("オープンポジション: 0件")
            results["passed"] += 1
    except Exception as e:
        print_fail(f"ポジション取得エラー: {e}")
        results["failed"] += 1

    # クリーンアップ
    mt5.shutdown()
    return results


# ============================================================
# MT4 接続テスト（CSVファイル確認）
# ============================================================

def test_mt4_csv(csv_path: str = None):
    """MT4 CSVファイルの読み込みテスト"""
    print_header("MT4 CSV接続テスト")

    results = {"passed": 0, "failed": 0, "warnings": 0}

    # 1. CSVファイルの存在確認
    if not csv_path:
        # デフォルトパスを探す
        default_paths = [
            "C:/Users/*/AppData/Roaming/MetaQuotes/Terminal/*/MQL4/Files/daily_trades.csv",
            "/tmp/mt4_trades.csv",
            os.path.expanduser("~/mt4_trades.csv"),
        ]
        print_info("CSVファイルのパスが指定されていません。デフォルトパスを検索...")
        import glob
        for pattern in default_paths:
            matches = glob.glob(pattern)
            if matches:
                csv_path = matches[0]
                break

    if not csv_path or not os.path.exists(csv_path):
        print_fail(f"CSVファイルが見つかりません: {csv_path or '(未指定)'}")
        print_info("MT4のEA (DailyTradeExporter) がCSVを出力しているか確認してください")
        print_info("使い方: python connection_test.py --platform mt4 --csv-path /path/to/trades.csv")
        results["failed"] += 1
        return results

    print_pass(f"CSVファイル発見: {csv_path}")
    results["passed"] += 1

    # 2. CSVファイルの読み込み
    print_info("CSVファイルの読み込み...")
    try:
        import csv
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if len(rows) > 0:
            print_pass(f"データ行数: {len(rows)}行")
            results["passed"] += 1
        else:
            print_warn("CSVファイルにデータがありません")
            results["warnings"] += 1
            return results
    except Exception as e:
        print_fail(f"CSV読み込みエラー: {e}")
        results["failed"] += 1
        return results

    # 3. 必須カラムの確認
    print_info("必須カラムの確認...")
    required_columns = ["Date", "Ticket", "Type", "Profit"]
    if rows:
        headers = list(rows[0].keys())
        for col in required_columns:
            if col in headers:
                print_pass(f"カラム '{col}' が存在")
                results["passed"] += 1
            else:
                print_fail(f"カラム '{col}' が見つかりません")
                results["failed"] += 1

    # 4. 最新データの確認
    print_info("最新データの確認...")
    if rows:
        last_row = rows[-1]
        print_info(f"最新レコード: {json.dumps(last_row, ensure_ascii=False, indent=2)}")
        
        # 日付の新しさを確認
        try:
            last_date = datetime.strptime(last_row.get("Date", ""), "%Y.%m.%d")
            days_old = (datetime.now() - last_date).days
            if days_old <= 1:
                print_pass(f"データは最新です（{days_old}日前）")
                results["passed"] += 1
            elif days_old <= 7:
                print_warn(f"データが{days_old}日前です")
                results["warnings"] += 1
            else:
                print_warn(f"データが{days_old}日前です。EAが正常に動作しているか確認してください")
                results["warnings"] += 1
        except ValueError:
            print_warn("日付フォーマットを解析できません")
            results["warnings"] += 1

    return results


# ============================================================
# バックエンドAPI接続テスト
# ============================================================

def test_api_connection(api_url: str = "http://localhost:8000"):
    """バックエンドAPIの接続テスト"""
    print_header("バックエンドAPI接続テスト")

    results = {"passed": 0, "failed": 0, "warnings": 0}

    try:
        import requests
    except ImportError:
        print_fail("requestsパッケージがインストールされていません")
        results["failed"] += 1
        return results

    # 1. ヘルスチェック
    print_info(f"API URL: {api_url}")
    print_info("ヘルスチェック...")
    try:
        resp = requests.get(f"{api_url}/health", timeout=10)
        if resp.status_code == 200:
            print_pass(f"APIサーバー稼働中 (ステータス: {resp.status_code})")
            data = resp.json()
            print_info(f"レスポンス: {json.dumps(data, ensure_ascii=False)}")
            results["passed"] += 1
        else:
            print_fail(f"APIサーバーエラー (ステータス: {resp.status_code})")
            results["failed"] += 1
    except requests.ConnectionError:
        print_fail(f"APIサーバーに接続できません: {api_url}")
        print_info("サーバーが起動しているか確認してください")
        results["failed"] += 1
        return results
    except Exception as e:
        print_fail(f"接続エラー: {e}")
        results["failed"] += 1
        return results

    # 2. プラン情報の取得
    print_info("プラン情報の取得...")
    try:
        resp = requests.get(f"{api_url}/api/v1/plans", timeout=10)
        if resp.status_code == 200:
            plans = resp.json()
            print_pass(f"プラン情報: {len(plans)}件取得")
            results["passed"] += 1
        else:
            print_warn(f"プラン情報取得: ステータス {resp.status_code}")
            results["warnings"] += 1
    except Exception as e:
        print_warn(f"プラン情報取得エラー: {e}")
        results["warnings"] += 1

    # 3. レスポンスタイムの確認
    print_info("レスポンスタイムの確認...")
    try:
        start = time.time()
        resp = requests.get(f"{api_url}/health", timeout=10)
        elapsed = (time.time() - start) * 1000
        if elapsed < 500:
            print_pass(f"レスポンスタイム: {elapsed:.0f}ms (良好)")
            results["passed"] += 1
        elif elapsed < 2000:
            print_warn(f"レスポンスタイム: {elapsed:.0f}ms (やや遅い)")
            results["warnings"] += 1
        else:
            print_fail(f"レスポンスタイム: {elapsed:.0f}ms (遅い)")
            results["failed"] += 1
    except Exception as e:
        print_fail(f"レスポンスタイム計測エラー: {e}")
        results["failed"] += 1

    return results


# ============================================================
# SNS API接続テスト
# ============================================================

def test_sns_connections():
    """SNS APIの接続テスト"""
    print_header("SNS API接続テスト")

    results = {"passed": 0, "failed": 0, "warnings": 0}

    # 環境変数の確認
    sns_configs = {
        "X (Twitter)": ["X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"],
        "Instagram": ["INSTAGRAM_ACCESS_TOKEN", "INSTAGRAM_ACCOUNT_ID"],
        "Threads": ["THREADS_ACCESS_TOKEN", "THREADS_ACCOUNT_ID"],
        "TikTok": ["TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET"],
        "LINE": ["LINE_NOTIFY_TOKEN"],
    }

    for platform, env_vars in sns_configs.items():
        print_info(f"{platform} の設定確認...")
        all_set = True
        for var in env_vars:
            value = os.environ.get(var, "")
            if value and value != "your_" + var.lower():
                print_pass(f"  {var}: 設定済み")
                results["passed"] += 1
            else:
                print_warn(f"  {var}: 未設定")
                results["warnings"] += 1
                all_set = False

        if all_set:
            print_pass(f"{platform}: 全ての設定が完了しています")
        else:
            print_warn(f"{platform}: 一部の設定が未完了です")

    return results


# ============================================================
# メイン
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="TradePost Pro - 接続テストツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python connection_test.py --platform mt5
  python connection_test.py --platform mt4 --csv-path /path/to/trades.csv
  python connection_test.py --api --api-url https://api.example.com
  python connection_test.py --sns
  python connection_test.py --all
        """
    )
    parser.add_argument("--platform", choices=["mt4", "mt5"], help="テスト対象のプラットフォーム")
    parser.add_argument("--csv-path", help="MT4 CSVファイルのパス")
    parser.add_argument("--api", action="store_true", help="バックエンドAPI接続テスト")
    parser.add_argument("--api-url", default="http://localhost:8000", help="APIのURL")
    parser.add_argument("--sns", action="store_true", help="SNS API設定テスト")
    parser.add_argument("--all", action="store_true", help="全テスト実行")

    args = parser.parse_args()

    print(f"\n{Colors.BOLD}TradePost Pro - 接続テストツール{Colors.END}")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    total = {"passed": 0, "failed": 0, "warnings": 0}

    if args.all or args.platform == "mt5":
        r = test_mt5_connection()
        for k in total:
            total[k] += r[k]

    if args.all or args.platform == "mt4":
        r = test_mt4_csv(args.csv_path)
        for k in total:
            total[k] += r[k]

    if args.all or args.api:
        r = test_api_connection(args.api_url)
        for k in total:
            total[k] += r[k]

    if args.all or args.sns:
        r = test_sns_connections()
        for k in total:
            total[k] += r[k]

    if not any([args.platform, args.api, args.sns, args.all]):
        parser.print_help()
        return

    # サマリー
    print_header("テスト結果サマリー")
    print(f"  {Colors.GREEN}合格: {total['passed']}{Colors.END}")
    print(f"  {Colors.RED}不合格: {total['failed']}{Colors.END}")
    print(f"  {Colors.YELLOW}警告: {total['warnings']}{Colors.END}")
    print()

    if total["failed"] == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}全てのテストに合格しました！{Colors.END}")
    else:
        print(f"  {Colors.RED}{Colors.BOLD}{total['failed']}件のテストが不合格です。上記のエラーを確認してください。{Colors.END}")

    sys.exit(1 if total["failed"] > 0 else 0)


if __name__ == "__main__":
    main()
