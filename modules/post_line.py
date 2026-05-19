"""
LINE オープンチャット自動投稿モジュール
========================================
LINE Messaging APIを使用して、オープンチャットに
取引結果のテキストと画像を自動投稿します。

【前提条件】
- LINE Developersでチャネル（Messaging API）を作成済みであること
- チャネルアクセストークンを取得済みであること
- LINE公式アカウント（Bot）をオープンチャットに招待済みであること
- pip install line-bot-sdk でパッケージをインストール済みであること

【使い方】
    from modules.post_line import LINEPoster
    from modules.utils import create_sample_trade_data
    
    poster = LINEPoster(
        channel_access_token="...",
        group_id="..."
    )
    trade_data = create_sample_trade_data()
    result = poster.post(trade_data, image_path="/path/to/image.jpg")
"""

import logging
import sys
import json
import requests
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.utils import TradeData, format_date_jp

logger = logging.getLogger(__name__)


class LINEPoster:
    """
    LINE Messaging APIを使用してオープンチャットに投稿するクラス。
    """

    # LINE Messaging API エンドポイント
    PUSH_API_URL = "https://api.line.me/v2/bot/message/push"

    def __init__(
        self,
        channel_access_token: str,
        group_id: str
    ):
        """
        Args:
            channel_access_token: LINE チャネルアクセストークン
            group_id: 投稿先のグループID（オープンチャットのグループID）
        """
        self.channel_access_token = channel_access_token
        self.group_id = group_id

    def _get_headers(self) -> dict:
        """APIリクエスト用のヘッダーを返します。"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.channel_access_token}"
        }

    def build_message_text(
        self,
        trade_data: TradeData,
        line_openchat_url: str = ""
    ) -> str:
        """
        LINE投稿用のメッセージテキストを生成します。
        
        Args:
            trade_data: 取引データ
            line_openchat_url: LINEオープンチャットURL（共有用）
        
        Returns:
            str: メッセージテキスト
        """
        date_str = format_date_jp(trade_data.date)
        trend = "📈" if trade_data.is_profitable else "📉"

        lines = [
            f"{trend} 本日のトレード結果 {trend}",
            f"",
            f"📅 日付: {date_str}",
            f"💰 損益: {trade_data.net_profit_str}",
            f"📊 勝率: {trade_data.win_rate_str}",
            f"🔄 取引回数: {trade_data.total_trades}回",
            f"📈 累計損益: {trade_data.cumulative_profit_str}",
        ]

        if line_openchat_url:
            lines.extend([
                f"",
                f"▼ 友達にもシェアしよう！",
                f"{line_openchat_url}",
            ])

        return "\n".join(lines)

    def post(
        self,
        trade_data: TradeData,
        image_url: Optional[str] = None,
        line_openchat_url: str = "",
        dry_run: bool = False,
        custom_text: Optional[str] = None,
    ) -> dict:
        """
        LINEオープンチャットにメッセージと画像を投稿します。

        Args:
            trade_data: 取引データ
            image_url: 画像の公開URL（HTTPS必須）
            line_openchat_url: LINEオープンチャットURL
            dry_run: Trueの場合、実際には投稿せずテキストのみ返す
            custom_text: カスタム投稿テキスト（指定時はbuild_message_textを使わない）

        Returns:
            dict: 投稿結果
        """
        message_text = custom_text if custom_text else self.build_message_text(trade_data, line_openchat_url)

        logger.info(f"LINEメッセージ生成完了（{len(message_text)}文字）")

        # メッセージの構築
        messages = []

        # テキストメッセージ
        messages.append({
            "type": "text",
            "text": message_text
        })

        # 画像メッセージ（URLが指定されている場合）
        if image_url:
            messages.append({
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url
            })

        if dry_run:
            logger.info("ドライラン: 実際の投稿はスキップします")
            return {
                "success": True,
                "text": message_text,
                "image_url": image_url,
                "platform": "line"
            }

        # API リクエスト
        payload = {
            "to": self.group_id,
            "messages": messages
        }

        try:
            response = requests.post(
                self.PUSH_API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                logger.info("LINE投稿成功")
                return {
                    "success": True,
                    "text": message_text,
                    "image_url": image_url,
                    "platform": "line"
                }
            else:
                error_body = response.text
                logger.error(
                    f"LINE投稿失敗: status={response.status_code}, "
                    f"body={error_body}"
                )
                return {
                    "success": False,
                    "text": message_text,
                    "error": f"HTTP {response.status_code}: {error_body}",
                    "platform": "line"
                }

        except requests.exceptions.RequestException as e:
            logger.error(f"LINE投稿失敗（通信エラー）: {e}")
            return {
                "success": False,
                "text": message_text,
                "error": str(e),
                "platform": "line"
            }

    def post_text_only(
        self,
        text: str,
        dry_run: bool = False
    ) -> dict:
        """
        テキストのみを投稿します（汎用メソッド）。
        
        Args:
            text: 投稿テキスト
            dry_run: ドライランフラグ
        
        Returns:
            dict: 投稿結果
        """
        if dry_run:
            return {"success": True, "text": text, "platform": "line"}

        payload = {
            "to": self.group_id,
            "messages": [{"type": "text", "text": text}]
        }

        try:
            response = requests.post(
                self.PUSH_API_URL,
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                logger.info("LINEテキスト投稿成功")
                return {"success": True, "text": text, "platform": "line"}
            else:
                logger.error(f"LINEテキスト投稿失敗: {response.status_code}")
                return {
                    "success": False,
                    "text": text,
                    "error": response.text,
                    "platform": "line"
                }
        except Exception as e:
            logger.error(f"LINEテキスト投稿失敗: {e}")
            return {"success": False, "text": text, "error": str(e), "platform": "line"}


def main():
    """LINE投稿のテスト実行（ドライラン）。"""
    from modules.utils import create_sample_trade_data, setup_logger
    from config.settings import (
        LINE_CHANNEL_ACCESS_TOKEN, LINE_GROUP_ID,
        LINE_OPENCHAT_URL, LOG_DIR
    )

    setup_logger("modules.post_line", LOG_DIR)

    poster = LINEPoster(
        channel_access_token=LINE_CHANNEL_ACCESS_TOKEN,
        group_id=LINE_GROUP_ID
    )

    trade_data = create_sample_trade_data()

    # ドライランでメッセージを確認
    result = poster.post(
        trade_data,
        image_url="https://example.com/trade_report.jpg",
        line_openchat_url=LINE_OPENCHAT_URL,
        dry_run=True
    )

    print("\n===== LINEメッセージプレビュー =====")
    print(result["text"])
    print("====================================")


if __name__ == "__main__":
    main()
