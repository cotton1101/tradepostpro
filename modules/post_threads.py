"""
Threads 自動投稿モジュール
============================
Threads APIを使用して、画像付きの投稿を自動で行います。

【前提条件】
- Meta for Developersでアプリを作成し、Threads APIを有効化済みであること
- threads_content_publish パーミッションが承認済みであること

【使い方】
    from modules.post_threads import ThreadsPoster
    from modules.utils import create_sample_trade_data
    
    poster = ThreadsPoster(
        access_token="...",
        user_id="..."
    )
    trade_data = create_sample_trade_data()
    result = poster.post(trade_data, image_url="https://example.com/image.jpg")
"""

import logging
import sys
import time
import requests
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.utils import TradeData, format_date_jp

logger = logging.getLogger(__name__)


class ThreadsPoster:
    """
    Threads APIを使用して投稿を行うクラス。
    """

    GRAPH_API_BASE = "https://graph.threads.net/v1.0"

    def __init__(self, access_token: str, user_id: str):
        self.access_token = access_token
        self.user_id = user_id

    def build_text(
        self,
        trade_data: TradeData,
        line_openchat_url: str = "",
        hashtags: str = ""
    ) -> str:
        """投稿テキストを生成します（500文字制限）。"""
        date_str = format_date_jp(trade_data.date)
        trend = "📈" if trade_data.is_profitable else "📉"

        lines = [
            f"{trend} 本日のトレード結果",
            f"",
            f"📅 {date_str}",
            f"💰 損益: {trade_data.net_profit_str}",
            f"📊 勝率: {trade_data.win_rate_str}",
            f"🔄 取引回数: {trade_data.total_trades}回",
            f"📈 累計損益: {trade_data.cumulative_profit_str}",
        ]

        if line_openchat_url:
            lines.extend([
                f"",
                f"詳しい手法はLINEオープンチャットで公開中！",
                f"{line_openchat_url}",
            ])

        if hashtags:
            lines.extend([f"", hashtags])

        text = "\n".join(lines)

        # 500文字制限
        if len(text) > 500:
            logger.warning(f"Threadsテキストが500文字を超えています（{len(text)}文字）")
            lines = [l for l in lines if not l.startswith("#")]
            text = "\n".join(lines)

        return text

    def post(
        self,
        trade_data: TradeData,
        image_url: Optional[str] = None,
        line_openchat_url: str = "",
        hashtags: str = "",
        dry_run: bool = False,
        custom_text: Optional[str] = None,
    ) -> dict:
        """
        Threadsに投稿します。

        Args:
            trade_data: 取引データ
            image_url: 画像の公開URL（オプション）
            line_openchat_url: LINEオープンチャットURL
            hashtags: ハッシュタグ
            dry_run: ドライランフラグ
            custom_text: カスタム投稿テキスト

        Returns:
            dict: 投稿結果
        """
        text = custom_text if custom_text else self.build_text(trade_data, line_openchat_url, hashtags)

        logger.info(f"Threadsテキスト生成完了（{len(text)}文字）")

        if dry_run:
            logger.info("ドライラン: 実際の投稿はスキップします")
            return {
                "success": True,
                "text": text,
                "image_url": image_url,
                "platform": "threads"
            }

        try:
            # ステップ1: メディアコンテナの作成
            container_url = f"{self.GRAPH_API_BASE}/{self.user_id}/threads"
            container_params = {
                "text": text,
                "access_token": self.access_token
            }

            if image_url:
                container_params["media_type"] = "IMAGE"
                container_params["image_url"] = image_url
            else:
                container_params["media_type"] = "TEXT"

            resp = requests.post(container_url, params=container_params, timeout=30)
            resp_data = resp.json()

            if "id" not in resp_data:
                error_msg = resp_data.get("error", {}).get("message", "不明なエラー")
                logger.error(f"Threadsコンテナ作成失敗: {error_msg}")
                return {
                    "success": False,
                    "text": text,
                    "error": error_msg,
                    "platform": "threads"
                }

            container_id = resp_data["id"]
            logger.info(f"Threadsコンテナ作成成功: {container_id}")

            # 処理完了を待機
            time.sleep(5)

            # ステップ2: パブリッシュ
            publish_url = f"{self.GRAPH_API_BASE}/{self.user_id}/threads_publish"
            publish_params = {
                "creation_id": container_id,
                "access_token": self.access_token
            }

            pub_resp = requests.post(publish_url, params=publish_params, timeout=30)
            pub_data = pub_resp.json()

            if "id" in pub_data:
                post_id = pub_data["id"]
                logger.info(f"Threads投稿成功: post_id={post_id}")
                return {
                    "success": True,
                    "post_id": post_id,
                    "text": text,
                    "platform": "threads"
                }
            else:
                error_msg = pub_data.get("error", {}).get("message", "不明なエラー")
                logger.error(f"Threadsパブリッシュ失敗: {error_msg}")
                return {
                    "success": False,
                    "text": text,
                    "error": error_msg,
                    "platform": "threads"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Threads投稿失敗: {e}")
            return {
                "success": False,
                "text": text,
                "error": str(e),
                "platform": "threads"
            }


def main():
    """Threads投稿のテスト実行（ドライラン）。"""
    from modules.utils import create_sample_trade_data, setup_logger
    from config.settings import (
        THREADS_ACCESS_TOKEN, THREADS_USER_ID,
        LINE_OPENCHAT_URL, HASHTAGS, LOG_DIR
    )

    setup_logger("modules.post_threads", LOG_DIR)

    poster = ThreadsPoster(
        access_token=THREADS_ACCESS_TOKEN,
        user_id=THREADS_USER_ID
    )

    trade_data = create_sample_trade_data()

    result = poster.post(
        trade_data,
        image_url="https://example.com/trade_report.jpg",
        line_openchat_url=LINE_OPENCHAT_URL,
        hashtags=HASHTAGS,
        dry_run=True
    )

    print("\n===== Threadsプレビュー =====")
    print(result["text"])
    print("==============================")


if __name__ == "__main__":
    main()
