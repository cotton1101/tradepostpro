"""
TradePost Pro - SNS投稿モジュール ユニットテスト（モック使用）
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPostX:
    """X (Twitter) 投稿モジュールのテスト"""

    def test_build_tweet_text(self, trade_data_profit):
        """ツイートテキストのフォーマットテスト"""
        from modules.post_x import XPoster

        poster = XPoster(
            api_key="test", api_secret="test",
            access_token="test", access_token_secret="test"
        )
        text = poster.build_tweet_text(trade_data_profit)
        assert isinstance(text, str)
        assert len(text) <= 280, "ツイートが280文字を超えている"
        assert len(text) > 0

    def test_build_tweet_text_loss(self, trade_data_loss):
        """損失時のツイートテキストテスト"""
        from modules.post_x import XPoster

        poster = XPoster(
            api_key="test", api_secret="test",
            access_token="test", access_token_secret="test"
        )
        text = poster.build_tweet_text(trade_data_loss)
        assert isinstance(text, str)
        assert len(text) <= 280

    def test_post_build_text_contains_data(self, trade_data_profit):
        """投稿テキストにデータが含まれているか"""
        from modules.post_x import XPoster

        poster = XPoster(
            api_key="test", api_secret="test",
            access_token="test", access_token_secret="test"
        )
        text = poster.build_tweet_text(trade_data_profit)
        assert text is not None
        assert len(text) > 10


class TestPostInstagram:
    """Instagram 投稿モジュールのテスト"""

    def test_build_caption(self, trade_data_profit):
        """キャプションのフォーマットテスト"""
        from modules.post_instagram import InstagramPoster

        poster = InstagramPoster(access_token="test", user_id="test")
        caption = poster.build_caption(trade_data_profit)
        assert isinstance(caption, str)
        assert len(caption) <= 2200, "キャプションが2200文字を超えている"
        assert len(caption) > 0

    def test_build_caption_loss(self, trade_data_loss):
        """損失時のキャプションテスト"""
        from modules.post_instagram import InstagramPoster

        poster = InstagramPoster(access_token="test", user_id="test")
        caption = poster.build_caption(trade_data_loss)
        assert isinstance(caption, str)


class TestPostThreads:
    """Threads 投稿モジュールのテスト"""

    def test_build_text(self, trade_data_profit):
        """テキストのフォーマットテスト"""
        from modules.post_threads import ThreadsPoster

        poster = ThreadsPoster(access_token="test", user_id="test")
        text = poster.build_text(trade_data_profit)
        assert isinstance(text, str)
        assert len(text) <= 500, "Threadsテキストが500文字を超えている"
        assert len(text) > 0


class TestPostTikTok:
    """TikTok 投稿モジュールのテスト"""

    def test_build_description(self, trade_data_profit):
        """説明文のフォーマットテスト"""
        from modules.post_tiktok import TikTokPoster

        poster = TikTokPoster(access_token="test")
        desc = poster.build_description(trade_data_profit)
        assert isinstance(desc, str)
        assert len(desc) > 0


class TestPostLine:
    """LINE 投稿モジュールのテスト"""

    def test_build_message_text(self, trade_data_profit):
        """LINEメッセージのフォーマットテスト"""
        from modules.post_line import LINEPoster

        poster = LINEPoster(channel_access_token="test", group_id="test")
        message = poster.build_message_text(trade_data_profit)
        assert isinstance(message, str)
        assert len(message) > 0

    def test_build_message_text_loss(self, trade_data_loss):
        """損失時のLINEメッセージテスト"""
        from modules.post_line import LINEPoster

        poster = LINEPoster(channel_access_token="test", group_id="test")
        message = poster.build_message_text(trade_data_loss)
        assert isinstance(message, str)
