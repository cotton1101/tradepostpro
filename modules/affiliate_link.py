"""
TradePost Pro - アフィリエイトリンク自動挿入モジュール
XMアフィリエイトリンクをSNS投稿に自動挿入する
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

logger = logging.getLogger(__name__)


@dataclass
class AffiliateConfig:
    """アフィリエイト設定"""
    # XMアフィリエイトID
    xm_partner_id: str = ""
    # XMアフィリエイトリンクのベースURL
    xm_base_url: str = "https://clicks.pipaffiliates.com/c"
    # トラッキングパラメータ
    xm_campaign: str = ""
    xm_sub_id: str = ""
    # カスタムリンク（短縮URL等）
    custom_link: str = ""
    # LINEオープンチャットURL
    line_openchat_url: str = ""
    # 各SNS別のリンク設定
    platform_links: Dict[str, str] = field(default_factory=dict)
    # リンク短縮を使うか
    use_short_link: bool = False
    short_link: str = ""


class AffiliateLinkManager:
    """アフィリエイトリンク管理"""

    def __init__(self, config: Optional[AffiliateConfig] = None):
        self.config = config or AffiliateConfig()

    def generate_xm_link(
        self,
        platform: str = "",
        campaign: str = "",
    ) -> str:
        """XMアフィリエイトリンクを生成"""
        if self.config.custom_link:
            return self.config.custom_link

        if self.config.use_short_link and self.config.short_link:
            return self.config.short_link

        if not self.config.xm_partner_id:
            return ""

        params = {
            "c": self.config.xm_partner_id,
        }

        # キャンペーンパラメータ
        camp = campaign or self.config.xm_campaign
        if camp:
            params["l"] = camp

        # サブID（プラットフォーム別トラッキング）
        sub_id = self.config.xm_sub_id or platform
        if sub_id:
            params["s1"] = sub_id

        # プラットフォーム別トラッキング
        if platform:
            params["s2"] = platform

        url = f"{self.config.xm_base_url}?{urlencode(params)}"
        return url

    def get_platform_link(self, platform: str) -> str:
        """プラットフォーム別のリンクを取得"""
        # プラットフォーム固有のリンクがあればそれを使用
        if platform in self.config.platform_links:
            return self.config.platform_links[platform]
        # なければ共通リンクを生成
        return self.generate_xm_link(platform=platform)

    def insert_affiliate_link(
        self,
        text: str,
        platform: str,
        include_line_url: bool = True,
    ) -> str:
        """投稿テキストにアフィリエイトリンクを挿入"""
        parts = [text]

        # XMアフィリエイトリンク
        xm_link = self.get_platform_link(platform)
        if xm_link:
            parts.append("")
            parts.append(f"🔗 XMで口座開設👇")
            parts.append(xm_link)

        # LINEオープンチャットURL
        if include_line_url and self.config.line_openchat_url:
            parts.append("")
            parts.append(f"👥 LINEオープンチャット参加👇")
            parts.append(self.config.line_openchat_url)

        return "\n".join(parts)

    def build_post_text(
        self,
        platform: str,
        trade_text: str,
        hashtags: str = "",
    ) -> str:
        """完全な投稿テキストを構築"""
        # プラットフォーム別の文字数制限
        char_limits = {
            "x": 280,
            "instagram": 2200,
            "threads": 500,
            "tiktok": 2200,
            "line": 5000,
        }

        # テキスト構築
        full_text = self.insert_affiliate_link(
            text=trade_text,
            platform=platform,
            include_line_url=(platform != "line"),  # LINE自体にはLINEリンク不要
        )

        # ハッシュタグ追加
        if hashtags:
            full_text += f"\n\n{hashtags}"

        # 文字数制限チェック
        limit = char_limits.get(platform, 5000)
        if len(full_text) > limit:
            # ハッシュタグを削除して再試行
            full_text = self.insert_affiliate_link(
                text=trade_text,
                platform=platform,
                include_line_url=(platform != "line"),
            )
            if len(full_text) > limit:
                # リンクを短縮
                full_text = full_text[:limit - 3] + "..."

        return full_text

    def get_tracking_stats_url(self) -> str:
        """アフィリエイト管理画面のURLを返す"""
        return "https://partners.xm.com/"

    def validate_config(self) -> Dict[str, bool]:
        """設定の検証"""
        return {
            "xm_partner_id": bool(self.config.xm_partner_id),
            "line_openchat_url": bool(self.config.line_openchat_url),
            "has_any_link": bool(
                self.config.xm_partner_id
                or self.config.custom_link
                or self.config.short_link
            ),
        }


# テンプレート付き投稿テキスト生成
class PostTextBuilder:
    """SNS投稿テキストビルダー"""

    # プラットフォーム別テンプレート
    TEMPLATES = {
        "x": {
            "profit": (
                "📊 本日のFX取引結果\n"
                "💰 損益: {net_profit}\n"
                "📈 {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率: {win_rate}%"
            ),
            "loss": (
                "📊 本日のFX取引結果\n"
                "💰 損益: {net_profit}\n"
                "📈 {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率: {win_rate}%"
            ),
        },
        "instagram": {
            "profit": (
                "📊 本日のFX取引結果\n"
                "━━━━━━━━━━━━━━━\n"
                "💰 損益: {net_profit}\n"
                "📈 取引回数: {total_trades}回\n"
                "🏆 勝敗: {wins}勝{losses}敗\n"
                "🎯 勝率: {win_rate}%\n"
                "📊 累計: {cumulative}\n"
                "━━━━━━━━━━━━━━━"
            ),
            "loss": (
                "📊 本日のFX取引結果\n"
                "━━━━━━━━━━━━━━━\n"
                "💰 損益: {net_profit}\n"
                "📈 取引回数: {total_trades}回\n"
                "🏆 勝敗: {wins}勝{losses}敗\n"
                "🎯 勝率: {win_rate}%\n"
                "📊 累計: {cumulative}\n"
                "━━━━━━━━━━━━━━━"
            ),
        },
        "threads": {
            "profit": (
                "📊 本日のFX取引結果\n\n"
                "💰 {net_profit}\n"
                "📈 {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率 {win_rate}%"
            ),
            "loss": (
                "📊 本日のFX取引結果\n\n"
                "💰 {net_profit}\n"
                "📈 {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率 {win_rate}%"
            ),
        },
        "tiktok": {
            "profit": (
                "📊 本日のFX取引結果\n\n"
                "💰 損益: {net_profit}\n"
                "📈 取引: {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率: {win_rate}%\n"
                "📊 累計: {cumulative}"
            ),
            "loss": (
                "📊 本日のFX取引結果\n\n"
                "💰 損益: {net_profit}\n"
                "📈 取引: {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率: {win_rate}%\n"
                "📊 累計: {cumulative}"
            ),
        },
        "line": {
            "profit": (
                "📊 本日のFX取引結果\n"
                "━━━━━━━━━━━━\n"
                "💰 損益: {net_profit}\n"
                "📈 取引: {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率: {win_rate}%\n"
                "📊 累計: {cumulative}\n"
                "━━━━━━━━━━━━"
            ),
            "loss": (
                "📊 本日のFX取引結果\n"
                "━━━━━━━━━━━━\n"
                "💰 損益: {net_profit}\n"
                "📈 取引: {total_trades}回（{wins}勝{losses}敗）\n"
                "🎯 勝率: {win_rate}%\n"
                "📊 累計: {cumulative}\n"
                "━━━━━━━━━━━━"
            ),
        },
    }

    def __init__(self, affiliate_manager: AffiliateLinkManager):
        self.affiliate = affiliate_manager

    def build(
        self,
        platform: str,
        net_profit: float,
        total_trades: int,
        wins: int,
        losses: int,
        win_rate: float,
        cumulative: float,
        hashtags: str = "",
    ) -> str:
        """投稿テキストを構築"""
        template_type = "profit" if net_profit >= 0 else "loss"
        templates = self.TEMPLATES.get(platform, self.TEMPLATES["x"])
        template = templates.get(template_type, templates["profit"])

        sign = "+" if net_profit >= 0 else ""
        cum_sign = "+" if cumulative >= 0 else ""

        text = template.format(
            net_profit=f"{sign}{net_profit:,.0f}円",
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
            cumulative=f"{cum_sign}{cumulative:,.0f}円",
        )

        return self.affiliate.build_post_text(
            platform=platform,
            trade_text=text,
            hashtags=hashtags,
        )


if __name__ == "__main__":
    # テスト
    config = AffiliateConfig(
        xm_partner_id="12345",
        xm_campaign="auto_post",
        line_openchat_url="https://line.me/ti/g2/xxxxx",
        custom_link="https://clicks.pipaffiliates.com/c?c=12345&l=ja&s1=tradepost",
    )

    manager = AffiliateLinkManager(config)
    builder = PostTextBuilder(manager)

    # 各プラットフォームのテスト
    for platform in ["x", "instagram", "threads", "tiktok", "line"]:
        print(f"\n{'='*50}")
        print(f"  {platform.upper()}")
        print(f"{'='*50}")
        text = builder.build(
            platform=platform,
            net_profit=17000,
            total_trades=12,
            wins=8,
            losses=4,
            win_rate=66.7,
            cumulative=230000,
            hashtags="#FX #トレード #XM",
        )
        print(text)

    # 設定検証
    print(f"\n設定検証: {manager.validate_config()}")
