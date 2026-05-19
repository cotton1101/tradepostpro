"""
TikTok 自動投稿モジュール
============================
TikTok Content Posting API (Direct Post) を使用して、
画像または動画を自動投稿します。

【前提条件】
- TikTok for Developersでアプリを作成・審査通過済みであること
- Content Posting APIのスコープが承認済みであること
- OAuth 2.0でユーザーのアクセストークンを取得済みであること

【使い方】
    from modules.post_tiktok import TikTokPoster
    from modules.utils import create_sample_trade_data
    
    poster = TikTokPoster(access_token="...")
    trade_data = create_sample_trade_data()
    result = poster.post_photo(trade_data, image_paths=["/path/to/image.jpg"])
"""

import logging
import sys
import time
import requests
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.utils import TradeData, format_date_jp

logger = logging.getLogger(__name__)


class TikTokPoster:
    """
    TikTok Content Posting APIを使用して投稿を行うクラス。
    """

    API_BASE = "https://open.tiktokapis.com/v2"

    def __init__(self, access_token: str):
        self.access_token = access_token

    def _get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8"
        }

    def build_description(
        self,
        trade_data: TradeData,
        line_openchat_url: str = "",
        hashtags: str = ""
    ) -> str:
        """TikTok投稿の説明文を生成します。"""
        date_str = format_date_jp(trade_data.date)

        lines = [
            f"本日のトレード結果",
            f"📅 {date_str}",
            f"💰 損益: {trade_data.net_profit_str}",
            f"📊 勝率: {trade_data.win_rate_str}",
        ]

        if line_openchat_url:
            lines.extend([
                f"",
                f"詳しくはプロフィールのリンクから！",
            ])

        if hashtags:
            # TikTokのハッシュタグ形式に変換
            lines.extend([f"", hashtags])

        return "\n".join(lines)

    def post_photo(
        self,
        trade_data: TradeData,
        image_urls: List[str],
        line_openchat_url: str = "",
        hashtags: str = "",
        dry_run: bool = False
    ) -> dict:
        """
        TikTokに写真投稿を行います（Photo Post）。
        
        Args:
            trade_data: 取引データ
            image_urls: 画像の公開URL（1〜10枚）
            line_openchat_url: LINEオープンチャットURL
            hashtags: ハッシュタグ
            dry_run: ドライランフラグ
        
        Returns:
            dict: 投稿結果
        """
        description = self.build_description(
            trade_data, line_openchat_url, hashtags
        )

        logger.info(f"TikTok説明文生成完了（{len(description)}文字）")

        if dry_run:
            logger.info("ドライラン: 実際の投稿はスキップします")
            return {
                "success": True,
                "text": description,
                "image_urls": image_urls,
                "platform": "tiktok"
            }

        try:
            # Photo Post API
            url = f"{self.API_BASE}/post/publish/content/init/"

            payload = {
                "post_info": {
                    "title": description,
                    "privacy_level": "SELF_ONLY",  # 初回はSELF_ONLYで安全にテスト
                    "disable_comment": False,
                    "auto_add_music": True
                },
                "source_info": {
                    "source": "PULL_FROM_URL",
                    "photo_cover_index": 0,
                    "photo_images": image_urls
                },
                "post_mode": "DIRECT_POST",
                "media_type": "PHOTO"
            }

            resp = requests.post(
                url,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )

            resp_data = resp.json()

            if resp_data.get("error", {}).get("code") == "ok":
                publish_id = resp_data.get("data", {}).get("publish_id", "")
                logger.info(f"TikTok投稿成功: publish_id={publish_id}")
                return {
                    "success": True,
                    "publish_id": publish_id,
                    "text": description,
                    "platform": "tiktok"
                }
            else:
                error_msg = resp_data.get("error", {}).get("message", "不明なエラー")
                logger.error(f"TikTok投稿失敗: {error_msg}")
                return {
                    "success": False,
                    "text": description,
                    "error": error_msg,
                    "platform": "tiktok"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok投稿失敗: {e}")
            return {
                "success": False,
                "text": description,
                "error": str(e),
                "platform": "tiktok"
            }


def main():
    """TikTok投稿のテスト実行（ドライラン）。"""
    from modules.utils import create_sample_trade_data, setup_logger
    from config.settings import TIKTOK_ACCESS_TOKEN, LINE_OPENCHAT_URL, HASHTAGS, LOG_DIR

    setup_logger("modules.post_tiktok", LOG_DIR)

    poster = TikTokPoster(access_token=TIKTOK_ACCESS_TOKEN)
    trade_data = create_sample_trade_data()

    result = poster.post_photo(
        trade_data,
        image_urls=["https://example.com/trade_report.jpg"],
        line_openchat_url=LINE_OPENCHAT_URL,
        hashtags=HASHTAGS,
        dry_run=True
    )

    print("\n===== TikTokプレビュー =====")
    print(result["text"])
    print("=============================")


if __name__ == "__main__":
    main()
