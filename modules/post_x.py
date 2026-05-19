"""
X (Twitter) 自動投稿モジュール
================================
X API v2 (Tweepy) を使用して、取引結果をテキストで自動投稿します。

【前提条件】
- X Developer Portalでアプリを作成済みであること
- OAuth 1.0a のキー・トークンを取得済みであること
- pip install tweepy でパッケージをインストール済みであること

【使い方】
    from modules.post_x import XPoster
    from modules.utils import create_sample_trade_data
    
    poster = XPoster(
        api_key="...",
        api_secret="...",
        access_token="...",
        access_token_secret="..."
    )
    trade_data = create_sample_trade_data()
    result = poster.post(trade_data)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.utils import TradeData, format_date_jp

logger = logging.getLogger(__name__)


class XPoster:
    """
    X (Twitter) にテキスト投稿を行うクラス。
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        bearer_token: str = ""
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token = access_token
        self.access_token_secret = access_token_secret
        self.bearer_token = bearer_token
        self._client = None

    def _get_client(self):
        """Tweepy クライアントを取得します。"""
        if self._client is None:
            try:
                import tweepy
            except ImportError:
                raise ImportError(
                    "tweepyパッケージがインストールされていません。\n"
                    "  pip install tweepy"
                )

            self._client = tweepy.Client(
                bearer_token=self.bearer_token if self.bearer_token else None,
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_token_secret
            )
        return self._client

    def build_tweet_text(
        self,
        trade_data: TradeData,
        line_openchat_url: str = "",
        hashtags: str = ""
    ) -> str:
        """
        投稿テキストを生成します。
        
        Args:
            trade_data: 取引データ
            line_openchat_url: LINEオープンチャットURL
            hashtags: ハッシュタグ文字列
        
        Returns:
            str: 投稿テキスト（280文字以内）
        """
        date_str = format_date_jp(trade_data.date)

        # 損益の絵文字的表現（テキストのみ）
        trend = "▲" if trade_data.is_profitable else "▼"

        lines = [
            f"【本日のトレード結果】",
            f"",
            f"日付: {date_str}",
            f"損益: {trend} {trade_data.net_profit_str}",
            f"勝率: {trade_data.win_rate_str}",
            f"取引回数: {trade_data.total_trades}回",
            f"累計損益: {trade_data.cumulative_profit_str}",
        ]

        if line_openchat_url:
            lines.extend([
                f"",
                f"詳しい手法はLINEオープンチャットで公開中！",
                f"▼参加はこちら",
                f"{line_openchat_url}",
            ])

        if hashtags:
            lines.extend([
                f"",
                hashtags
            ])

        tweet_text = "\n".join(lines)

        # 280文字制限のチェック（日本語は1文字=2としてカウント）
        if len(tweet_text) > 280:
            logger.warning(f"ツイートが280文字を超えています（{len(tweet_text)}文字）。短縮します。")
            # ハッシュタグを削除して短縮
            lines = [l for l in lines if not l.startswith("#")]
            tweet_text = "\n".join(lines)

        return tweet_text

    def _get_api_v1(self):
        """Tweepy API v1.1を取得（メディアアップロード用）"""
        try:
            import tweepy
        except ImportError:
            raise ImportError("tweepyパッケージがインストールされていません。")
        auth = tweepy.OAuth1UserHandler(
            self.api_key, self.api_secret,
            self.access_token, self.access_token_secret
        )
        return tweepy.API(auth)

    def post(
        self,
        trade_data: TradeData,
        line_openchat_url: str = "",
        hashtags: str = "",
        dry_run: bool = False,
        custom_text: Optional[str] = None,
        image_path: Optional[str] = None,
    ) -> dict:
        """
        Xにテキスト（+画像）を投稿します。

        Args:
            trade_data: 取引データ
            line_openchat_url: LINEオープンチャットURL
            hashtags: ハッシュタグ
            dry_run: Trueの場合、実際には投稿せずテキストのみ返す
            custom_text: カスタム投稿テキスト（指定時はbuild_tweet_textを使わない）
            image_path: 画像ファイルパス（指定時はメディアアップロード）

        Returns:
            dict: 投稿結果 {"success": bool, "tweet_id": str, "text": str}
        """
        tweet_text = custom_text if custom_text else self.build_tweet_text(
            trade_data, line_openchat_url, hashtags
        )

        logger.info(f"X投稿テキスト生成完了（{len(tweet_text)}文字）")

        if dry_run:
            logger.info("ドライラン: 実際の投稿はスキップします")
            return {
                "success": True,
                "tweet_id": "dry_run",
                "text": tweet_text,
                "platform": "x"
            }

        try:
            client = self._get_client()
            media_ids = None

            # 画像がある場合はv1.1 APIでアップロード
            if image_path and os.path.exists(image_path):
                try:
                    api_v1 = self._get_api_v1()
                    media = api_v1.media_upload(filename=image_path)
                    media_ids = [media.media_id]
                    logger.info(f"メディアアップロード成功: media_id={media.media_id}")
                except Exception as me:
                    logger.warning(f"メディアアップロード失敗（テキストのみで投稿）: {me}")

            response = client.create_tweet(
                text=tweet_text,
                media_ids=media_ids
            )

            tweet_id = response.data["id"]
            logger.info(f"X投稿成功: tweet_id={tweet_id}")

            return {
                "success": True,
                "tweet_id": tweet_id,
                "text": tweet_text,
                "platform": "x"
            }

        except Exception as e:
            logger.error(f"X投稿失敗: {e}")
            return {
                "success": False,
                "tweet_id": None,
                "text": tweet_text,
                "error": str(e),
                "platform": "x"
            }

    def verify_credentials(self) -> bool:
        """
        認証情報が正しいか確認します。
        
        Returns:
            bool: 認証成功ならTrue
        """
        try:
            client = self._get_client()
            me = client.get_me()
            if me.data:
                logger.info(f"X認証成功: @{me.data.username}")
                return True
            return False
        except Exception as e:
            logger.error(f"X認証失敗: {e}")
            return False


def main():
    """X投稿のテスト実行（ドライラン）。"""
    from modules.utils import create_sample_trade_data, setup_logger
    from config.settings import (
        X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN,
        X_ACCESS_TOKEN_SECRET, X_BEARER_TOKEN,
        LINE_OPENCHAT_URL, HASHTAGS, LOG_DIR
    )

    setup_logger("modules.post_x", LOG_DIR)

    poster = XPoster(
        api_key=X_API_KEY,
        api_secret=X_API_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
        bearer_token=X_BEARER_TOKEN
    )

    trade_data = create_sample_trade_data()

    # ドライランで投稿テキストを確認
    result = poster.post(
        trade_data,
        line_openchat_url=LINE_OPENCHAT_URL,
        hashtags=HASHTAGS,
        dry_run=True
    )

    print("\n===== X投稿プレビュー =====")
    print(result["text"])
    print("===========================")
    print(f"文字数: {len(result['text'])}文字")


if __name__ == "__main__":
    main()
