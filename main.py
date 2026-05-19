"""
XM Affiliate SNS Auto Poster - メインスクリプト
=================================================
MT4/MT5からデータを取得し、画像を生成し、各SNSに自動投稿する
統合スクリプトです。

【使い方】
    # 通常実行（全SNSに投稿）
    python main.py
    
    # ドライラン（実際には投稿しない）
    python main.py --dry-run
    
    # 特定のSNSのみに投稿
    python main.py --platforms x line
    
    # サンプルデータでテスト
    python main.py --sample --dry-run
    
    # MT4モードで実行
    python main.py --mt4
    
    # 特定の日付のデータを処理
    python main.py --date 2026-03-10
"""

import argparse
import json
import sys
import traceback
from datetime import date, datetime
from pathlib import Path

# プロジェクトルートをパスに追加
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import (
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET,
    X_BEARER_TOKEN,
    INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID,
    THREADS_ACCESS_TOKEN, THREADS_USER_ID,
    TIKTOK_ACCESS_TOKEN,
    LINE_CHANNEL_ACCESS_TOKEN, LINE_GROUP_ID,
    LINE_OPENCHAT_URL, HASHTAGS,
    MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_PATH,
    MT4_CSV_DIR,
    CONOHA_ACCESS_KEY, CONOHA_SECRET_KEY,
    CONOHA_BUCKET_NAME, CONOHA_ENDPOINT_URL, CONOHA_PUBLIC_BASE_URL,
    LOG_DIR
)
from modules.utils import (
    TradeData, create_sample_trade_data, setup_logger
)
from modules.image_generator import ImageGenerator
from modules.post_x import XPoster
from modules.post_line import LINEPoster
from modules.post_instagram import InstagramPoster
from modules.post_threads import ThreadsPoster
from modules.post_tiktok import TikTokPoster
from modules.image_uploader import ConoHaImageUploader

# ロガーの設定
logger = setup_logger("main", LOG_DIR)


class SNSAutoPostOrchestrator:
    """
    全体の処理を統括するオーケストレータークラス。
    データ取得 → 画像生成 → 各SNS投稿 の一連の流れを管理します。
    """

    # 対応プラットフォーム一覧
    SUPPORTED_PLATFORMS = ["x", "instagram", "threads", "tiktok", "line"]

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.image_generator = ImageGenerator()
        self.image_uploader = None
        self.results = []

        # 画像アップローダーの初期化
        self._init_uploader()

        # 各SNSポスターの初期化
        self.posters = {}
        self._init_posters()

    def _init_uploader(self):
        """ConoHaオブジェクトストレージのアップローダーを初期化します。"""
        if CONOHA_ACCESS_KEY:
            self.image_uploader = ConoHaImageUploader(
                access_key=CONOHA_ACCESS_KEY,
                secret_key=CONOHA_SECRET_KEY,
                bucket_name=CONOHA_BUCKET_NAME,
                endpoint_url=CONOHA_ENDPOINT_URL,
                public_base_url=CONOHA_PUBLIC_BASE_URL
            )
            logger.info("ConoHaイメージアップローダー初期化完了")
        else:
            logger.warning(
                "ConoHaアクセスキーが未設定です。"
                "画像アップロードはスキップされます。"
            )

    def _init_posters(self):
        """各SNSのポスターを初期化します。"""
        # X (Twitter)
        if X_API_KEY:
            self.posters["x"] = XPoster(
                api_key=X_API_KEY,
                api_secret=X_API_SECRET,
                access_token=X_ACCESS_TOKEN,
                access_token_secret=X_ACCESS_TOKEN_SECRET,
                bearer_token=X_BEARER_TOKEN
            )
            logger.info("X (Twitter) ポスター初期化完了")
        else:
            logger.warning("X APIキーが未設定です。X投稿はスキップされます。")

        # Instagram
        if INSTAGRAM_ACCESS_TOKEN:
            self.posters["instagram"] = InstagramPoster(
                access_token=INSTAGRAM_ACCESS_TOKEN,
                user_id=INSTAGRAM_USER_ID
            )
            logger.info("Instagram ポスター初期化完了")
        else:
            logger.warning("Instagram APIが未設定です。Instagram投稿はスキップされます。")

        # Threads
        if THREADS_ACCESS_TOKEN:
            self.posters["threads"] = ThreadsPoster(
                access_token=THREADS_ACCESS_TOKEN,
                user_id=THREADS_USER_ID
            )
            logger.info("Threads ポスター初期化完了")
        else:
            logger.warning("Threads APIが未設定です。Threads投稿はスキップされます。")

        # TikTok
        if TIKTOK_ACCESS_TOKEN:
            self.posters["tiktok"] = TikTokPoster(
                access_token=TIKTOK_ACCESS_TOKEN
            )
            logger.info("TikTok ポスター初期化完了")
        else:
            logger.warning("TikTok APIが未設定です。TikTok投稿はスキップされます。")

        # LINE
        if LINE_CHANNEL_ACCESS_TOKEN:
            self.posters["line"] = LINEPoster(
                channel_access_token=LINE_CHANNEL_ACCESS_TOKEN,
                group_id=LINE_GROUP_ID
            )
            logger.info("LINE ポスター初期化完了")
        else:
            logger.warning("LINE APIが未設定です。LINE投稿はスキップされます。")

    def fetch_trade_data(
        self,
        use_mt4: bool = False,
        use_sample: bool = False,
        target_date: date = None
    ) -> TradeData:
        """
        取引データを取得します。
        
        Args:
            use_mt4: MT4モードを使用するか
            use_sample: サンプルデータを使用するか
            target_date: 取得対象日
        
        Returns:
            TradeData: 取引データ
        """
        if use_sample:
            logger.info("サンプルデータを使用します")
            return create_sample_trade_data()

        if use_mt4:
            logger.info("MT4モード: CSVファイルからデータを読み込みます")
            from modules.mt4_data import MT4DataReader
            reader = MT4DataReader(csv_dir=MT4_CSV_DIR)
            if target_date:
                return reader.read_by_date(target_date)
            return reader.read_latest()
        else:
            logger.info("MT5モード: MT5 APIからデータを取得します")
            from modules.mt5_data import MT5DataFetcher
            fetcher = MT5DataFetcher(
                login=MT5_LOGIN,
                password=MT5_PASSWORD,
                server=MT5_SERVER,
                path=MT5_PATH
            )
            if not fetcher.connect():
                raise RuntimeError("MT5への接続に失敗しました")
            try:
                return fetcher.fetch_daily_data(target_date)
            finally:
                fetcher.disconnect()

    def generate_image(
        self,
        trade_data: TradeData,
        template_path: str = None
    ) -> Path:
        """
        投稿用画像を生成します。
        
        Args:
            trade_data: 取引データ
            template_path: テンプレート画像パス（オプション）
        
        Returns:
            Path: 生成された画像のパス
        """
        if template_path:
            self.image_generator.template_path = template_path

        image_path = self.image_generator.generate(
            trade_data,
            line_openchat_url=LINE_OPENCHAT_URL
        )

        logger.info(f"画像生成完了: {image_path}")
        return image_path

    def post_to_all(
        self,
        trade_data: TradeData,
        image_path: Path,
        image_url: str = "",
        platforms: list = None
    ) -> list:
        """
        全SNSに投稿します。
        
        Args:
            trade_data: 取引データ
            image_path: 生成された画像のローカルパス
            image_url: 画像の公開URL（Instagram/Threads/TikTok/LINE用）
            platforms: 投稿先プラットフォームのリスト（Noneの場合は全て）
        
        Returns:
            list: 各プラットフォームの投稿結果
        """
        if platforms is None:
            platforms = self.SUPPORTED_PLATFORMS

        results = []

        for platform in platforms:
            if platform not in self.posters:
                logger.warning(f"{platform}のポスターが未設定です。スキップします。")
                results.append({
                    "platform": platform,
                    "success": False,
                    "error": "APIキー未設定"
                })
                continue

            logger.info(f"--- {platform.upper()} への投稿開始 ---")

            try:
                poster = self.posters[platform]

                if platform == "x":
                    result = poster.post(
                        trade_data,
                        line_openchat_url=LINE_OPENCHAT_URL,
                        hashtags=HASHTAGS,
                        dry_run=self.dry_run
                    )

                elif platform == "instagram":
                    if not image_url:
                        logger.warning("Instagram: 画像URLが未指定のためスキップ")
                        result = {
                            "success": False,
                            "error": "画像の公開URLが必要です",
                            "platform": "instagram"
                        }
                    else:
                        result = poster.post(
                            trade_data,
                            image_url=image_url,
                            line_openchat_url=LINE_OPENCHAT_URL,
                            hashtags=HASHTAGS,
                            dry_run=self.dry_run
                        )

                elif platform == "threads":
                    result = poster.post(
                        trade_data,
                        image_url=image_url if image_url else None,
                        line_openchat_url=LINE_OPENCHAT_URL,
                        hashtags=HASHTAGS,
                        dry_run=self.dry_run
                    )

                elif platform == "tiktok":
                    if not image_url:
                        logger.warning("TikTok: 画像URLが未指定のためスキップ")
                        result = {
                            "success": False,
                            "error": "画像の公開URLが必要です",
                            "platform": "tiktok"
                        }
                    else:
                        result = poster.post_photo(
                            trade_data,
                            image_urls=[image_url],
                            line_openchat_url=LINE_OPENCHAT_URL,
                            hashtags=HASHTAGS,
                            dry_run=self.dry_run
                        )

                elif platform == "line":
                    result = poster.post(
                        trade_data,
                        image_url=image_url if image_url else None,
                        line_openchat_url=LINE_OPENCHAT_URL,
                        dry_run=self.dry_run
                    )

                results.append(result)

                status = "成功" if result.get("success") else "失敗"
                logger.info(f"{platform.upper()} 投稿{status}")

            except Exception as e:
                logger.error(f"{platform.upper()} 投稿エラー: {e}")
                traceback.print_exc()
                results.append({
                    "platform": platform,
                    "success": False,
                    "error": str(e)
                })

        return results

    def run(
        self,
        use_mt4: bool = False,
        use_sample: bool = False,
        target_date: date = None,
        platforms: list = None,
        template_path: str = None,
        image_url: str = ""
    ) -> dict:
        """
        メイン処理を実行します。
        
        Args:
            use_mt4: MT4モードを使用するか
            use_sample: サンプルデータを使用するか
            target_date: 取得対象日
            platforms: 投稿先プラットフォーム
            template_path: テンプレート画像パス
            image_url: 画像の公開URL
        
        Returns:
            dict: 実行結果のサマリー
        """
        logger.info("=" * 60)
        logger.info("XM Affiliate SNS Auto Poster - 実行開始")
        logger.info(f"ドライラン: {self.dry_run}")
        logger.info(f"対象プラットフォーム: {platforms or 'ALL'}")
        logger.info("=" * 60)

        try:
            # 1. データ取得
            logger.info("[STEP 1/3] 取引データの取得")
            trade_data = self.fetch_trade_data(use_mt4, use_sample, target_date)
            logger.info(
                f"取引データ: 日付={trade_data.date}, "
                f"損益={trade_data.net_profit_str}, "
                f"勝率={trade_data.win_rate_str}"
            )

            # 2. 画像生成
            logger.info("[STEP 2/4] 投稿画像の生成")
            image_path = self.generate_image(trade_data, template_path)

            # 3. 画像アップロード
            logger.info("[STEP 3/4] 画像のアップロード")
            if not image_url and self.image_uploader:
                try:
                    image_url = self.image_uploader.upload(str(image_path))
                    logger.info(f"画像アップロード完了: {image_url}")
                except Exception as e:
                    logger.error(f"画像アップロード失敗: {e}")
            elif not image_url:
                logger.warning(
                    "画像アップローダーが未設定のため、"
                    "Instagram/Threads/TikTok/LINEへの画像投稿はスキップされます"
                )

            # 4. SNS投稿
            logger.info("[STEP 4/4] 各SNSへの投稿")
            results = self.post_to_all(
                trade_data, image_path, image_url, platforms
            )

            # サマリーの作成
            success_count = sum(1 for r in results if r.get("success"))
            fail_count = len(results) - success_count

            summary = {
                "status": "completed",
                "trade_data": trade_data.to_dict(),
                "image_path": str(image_path),
                "results": results,
                "summary": {
                    "total": len(results),
                    "success": success_count,
                    "failed": fail_count
                }
            }

            logger.info("=" * 60)
            logger.info(f"実行完了: 成功={success_count}, 失敗={fail_count}")
            logger.info("=" * 60)

            # 結果をJSONファイルに保存
            result_path = BASE_DIR / "output" / f"result_{trade_data.date}.json"
            result_path.parent.mkdir(exist_ok=True)
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)

            return summary

        except Exception as e:
            logger.error(f"実行エラー: {e}")
            traceback.print_exc()
            return {
                "status": "error",
                "error": str(e)
            }


def parse_args():
    """コマンドライン引数をパースします。"""
    parser = argparse.ArgumentParser(
        description="XM Affiliate SNS Auto Poster"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ドライラン（実際には投稿しない）"
    )

    parser.add_argument(
        "--sample",
        action="store_true",
        help="サンプルデータを使用する"
    )

    parser.add_argument(
        "--mt4",
        action="store_true",
        help="MT4モード（CSVからデータ読み込み）"
    )

    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="対象日（YYYY-MM-DD形式）"
    )

    parser.add_argument(
        "--platforms",
        nargs="+",
        choices=SNSAutoPostOrchestrator.SUPPORTED_PLATFORMS,
        default=None,
        help="投稿先プラットフォーム（スペース区切り）"
    )

    parser.add_argument(
        "--template",
        type=str,
        default=None,
        help="テンプレート画像のパス"
    )

    parser.add_argument(
        "--image-url",
        type=str,
        default="",
        help="画像の公開URL（Instagram/Threads/TikTok/LINE用）"
    )

    return parser.parse_args()


def main():
    """メインエントリーポイント。"""
    args = parse_args()

    # 対象日のパース
    target_date = None
    if args.date:
        target_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    # オーケストレーターの作成と実行
    orchestrator = SNSAutoPostOrchestrator(dry_run=args.dry_run)

    summary = orchestrator.run(
        use_mt4=args.mt4,
        use_sample=args.sample,
        target_date=target_date,
        platforms=args.platforms,
        template_path=args.template,
        image_url=args.image_url
    )

    # 結果の表示
    print("\n" + "=" * 50)
    print("  実行結果サマリー")
    print("=" * 50)

    if summary["status"] == "completed":
        td = summary["trade_data"]
        print(f"  日付: {td['date']}")
        print(f"  損益: {td['net_profit']:+,.0f}円")
        print(f"  勝率: {td['win_rate']:.1f}%")
        print(f"  画像: {summary['image_path']}")
        print()

        for result in summary["results"]:
            platform = result.get("platform", "?").upper()
            success = result.get("success", False)
            status = "✓ 成功" if success else "✗ 失敗"
            error = result.get("error", "")
            print(f"  [{platform}] {status}" + (f" - {error}" if error else ""))

        s = summary["summary"]
        print(f"\n  合計: {s['total']}件 (成功: {s['success']}, 失敗: {s['failed']})")
    else:
        print(f"  エラー: {summary.get('error', '不明')}")

    print("=" * 50)


if __name__ == "__main__":
    main()
