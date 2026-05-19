"""
Instagram 自動投稿モジュール
==============================
Instagram Graph APIを使用して、画像付きの投稿を自動で行います。

【前提条件】
- Meta for Developersでアプリを作成済みであること
- Instagramプロアカウント（ビジネス）であること
- Facebookページと連携済みであること
- instagram_content_publish パーミッションが承認済みであること

【使い方】
    from modules.post_instagram import InstagramPoster
    from modules.utils import create_sample_trade_data
    
    poster = InstagramPoster(
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


class InstagramPoster:
    """
    Instagram Graph APIを使用して画像投稿を行うクラス。
    """

    GRAPH_API_BASE = "https://graph.facebook.com/v19.0"

    def __init__(self, access_token: str, user_id: str):
        """
        Args:
            access_token: Instagram Graph API アクセストークン
            user_id: Instagram ビジネスアカウントのユーザーID
        """
        self.access_token = access_token
        self.user_id = user_id

    def build_caption(
        self,
        trade_data: TradeData,
        line_openchat_url: str = "",
        hashtags: str = ""
    ) -> str:
        """投稿キャプションを生成します。"""
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
                f"プロフィールのリンクから参加できます✨",
            ])

        if hashtags:
            lines.extend([f"", hashtags])

        return "\n".join(lines)

    def post(
        self,
        trade_data: TradeData,
        image_url: str,
        line_openchat_url: str = "",
        hashtags: str = "",
        dry_run: bool = False
    ) -> dict:
        """
        Instagramに画像を投稿します。
        
        Args:
            trade_data: 取引データ
            image_url: 画像の公開URL（HTTPS必須）
            line_openchat_url: LINEオープンチャットURL
            hashtags: ハッシュタグ
            dry_run: ドライランフラグ
        
        Returns:
            dict: 投稿結果
        
        Note:
            Instagram Graph APIでは、画像はHTTPSでアクセス可能な
            公開URLである必要があります。
        """
        caption = self.build_caption(trade_data, line_openchat_url, hashtags)

        logger.info(f"Instagramキャプション生成完了（{len(caption)}文字）")

        if dry_run:
            logger.info("ドライラン: 実際の投稿はスキップします")
            return {
                "success": True,
                "text": caption,
                "image_url": image_url,
                "platform": "instagram"
            }

        try:
            # ステップ1: メディアコンテナの作成
            container_url = f"{self.GRAPH_API_BASE}/{self.user_id}/media"
            container_params = {
                "image_url": image_url,
                "caption": caption,
                "access_token": self.access_token
            }

            resp = requests.post(container_url, params=container_params, timeout=30)
            resp_data = resp.json()

            if "id" not in resp_data:
                error_msg = resp_data.get("error", {}).get("message", "不明なエラー")
                logger.error(f"Instagramコンテナ作成失敗: {error_msg}")
                return {
                    "success": False,
                    "text": caption,
                    "error": error_msg,
                    "platform": "instagram"
                }

            container_id = resp_data["id"]
            logger.info(f"メディアコンテナ作成成功: {container_id}")

            # コンテナの処理完了を待機（最大60秒）
            time.sleep(5)

            # ステップ2: メディアのパブリッシュ
            publish_url = f"{self.GRAPH_API_BASE}/{self.user_id}/media_publish"
            publish_params = {
                "creation_id": container_id,
                "access_token": self.access_token
            }

            pub_resp = requests.post(publish_url, params=publish_params, timeout=30)
            pub_data = pub_resp.json()

            if "id" in pub_data:
                post_id = pub_data["id"]
                logger.info(f"Instagram投稿成功: post_id={post_id}")
                return {
                    "success": True,
                    "post_id": post_id,
                    "text": caption,
                    "platform": "instagram"
                }
            else:
                error_msg = pub_data.get("error", {}).get("message", "不明なエラー")
                logger.error(f"Instagramパブリッシュ失敗: {error_msg}")
                return {
                    "success": False,
                    "text": caption,
                    "error": error_msg,
                    "platform": "instagram"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"Instagram投稿失敗（通信エラー）: {e}")
            return {
                "success": False,
                "text": caption,
                "error": str(e),
                "platform": "instagram"
            }


def main():
    """Instagram投稿のテスト実行（ドライラン）。"""
    from modules.utils import create_sample_trade_data, setup_logger
    from config.settings import (
        INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID,
        LINE_OPENCHAT_URL, HASHTAGS, LOG_DIR
    )

    setup_logger("modules.post_instagram", LOG_DIR)

    poster = InstagramPoster(
        access_token=INSTAGRAM_ACCESS_TOKEN,
        user_id=INSTAGRAM_USER_ID
    )

    trade_data = create_sample_trade_data()

    result = poster.post(
        trade_data,
        image_url="https://example.com/trade_report.jpg",
        line_openchat_url=LINE_OPENCHAT_URL,
        hashtags=HASHTAGS,
        dry_run=True
    )

    print("\n===== Instagramキャプションプレビュー =====")
    print(result["text"])
    print("============================================")


if __name__ == "__main__":
    main()
