"""
TradePost Pro - 投稿プレビューサービス
各SNSでの投稿見え方をプレビュー生成
"""

import json
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class PreviewConfig:
    """SNSプレビュー設定"""
    platform: str = ""
    max_text_length: int = 0
    image_aspect_ratio: str = ""
    supports_image: bool = True
    supports_video: bool = False
    supports_hashtags: bool = True
    supports_links: bool = True
    preview_width: int = 400
    preview_height: int = 500


# 各SNSのプレビュー設定
SNS_PREVIEW_CONFIGS = {
    "x": PreviewConfig(
        platform="X (Twitter)",
        max_text_length=280,
        image_aspect_ratio="16:9",
        supports_image=False,  # テキストのみ設定
        supports_video=False,
        preview_width=500,
        preview_height=300,
    ),
    "instagram": PreviewConfig(
        platform="Instagram",
        max_text_length=2200,
        image_aspect_ratio="1:1",
        supports_image=True,
        supports_video=True,
        preview_width=400,
        preview_height=550,
    ),
    "threads": PreviewConfig(
        platform="Threads",
        max_text_length=500,
        image_aspect_ratio="1:1",
        supports_image=True,
        supports_video=False,
        preview_width=400,
        preview_height=500,
    ),
    "tiktok": PreviewConfig(
        platform="TikTok",
        max_text_length=2200,
        image_aspect_ratio="9:16",
        supports_image=True,
        supports_video=True,
        preview_width=350,
        preview_height=620,
    ),
    "line": PreviewConfig(
        platform="LINE",
        max_text_length=5000,
        image_aspect_ratio="1:1",
        supports_image=True,
        supports_video=False,
        preview_width=400,
        preview_height=450,
    ),
}


@dataclass
class PostPreview:
    """投稿プレビューデータ"""
    platform: str
    display_name: str
    text: str
    text_truncated: bool
    text_length: int
    max_length: int
    image_url: Optional[str]
    hashtags: List[str]
    warnings: List[str]
    preview_html: str


class PreviewService:
    """投稿プレビュー生成サービス"""

    def __init__(self):
        self.configs = SNS_PREVIEW_CONFIGS

    def generate_preview(
        self,
        platform: str,
        text: str,
        image_url: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        username: str = "user",
        profile_image: str = "",
    ) -> PostPreview:
        """指定SNS用のプレビューを生成"""
        config = self.configs.get(platform)
        if not config:
            return PostPreview(
                platform=platform,
                display_name=platform,
                text=text,
                text_truncated=False,
                text_length=len(text),
                max_length=0,
                image_url=image_url,
                hashtags=hashtags or [],
                warnings=["未対応のプラットフォームです"],
                preview_html="",
            )

        warnings = []
        hashtags = hashtags or []

        # テキスト長チェック
        full_text = text
        if hashtags and config.supports_hashtags:
            hashtag_text = " " + " ".join(f"#{tag}" for tag in hashtags)
            full_text += hashtag_text

        text_truncated = len(full_text) > config.max_text_length
        if text_truncated:
            warnings.append(f"テキストが{config.max_text_length}文字を超えています（{len(full_text)}文字）")

        # 画像チェック
        if image_url and not config.supports_image:
            warnings.append(f"{config.platform}ではテキストのみの投稿です")

        # プレビューHTML生成
        preview_html = self._render_preview_html(
            platform, config, full_text, image_url, username, profile_image
        )

        return PostPreview(
            platform=platform,
            display_name=config.platform,
            text=full_text,
            text_truncated=text_truncated,
            text_length=len(full_text),
            max_length=config.max_text_length,
            image_url=image_url,
            hashtags=hashtags,
            warnings=warnings,
            preview_html=preview_html,
        )

    def generate_all_previews(
        self,
        platforms: List[str],
        text: str,
        image_url: Optional[str] = None,
        hashtags: Optional[List[str]] = None,
        username: str = "user",
    ) -> List[PostPreview]:
        """全SNS分のプレビューを一括生成"""
        return [
            self.generate_preview(p, text, image_url, hashtags, username)
            for p in platforms
        ]

    def _render_preview_html(
        self,
        platform: str,
        config: PreviewConfig,
        text: str,
        image_url: Optional[str],
        username: str,
        profile_image: str,
    ) -> str:
        """プレビュー用HTMLを生成"""
        if platform == "x":
            return self._render_x_preview(config, text, username, profile_image)
        elif platform == "instagram":
            return self._render_instagram_preview(config, text, image_url, username, profile_image)
        elif platform == "threads":
            return self._render_threads_preview(config, text, image_url, username, profile_image)
        elif platform == "tiktok":
            return self._render_tiktok_preview(config, text, image_url, username)
        elif platform == "line":
            return self._render_line_preview(config, text, image_url)
        return ""

    def _render_x_preview(self, config, text, username, profile_image) -> str:
        return f'''
<div style="background:#15202b;border-radius:16px;padding:16px;max-width:{config.preview_width}px;font-family:sans-serif;color:#fff;">
  <div style="display:flex;align-items:center;margin-bottom:12px;">
    <div style="width:48px;height:48px;border-radius:50%;background:#334155;margin-right:12px;display:flex;align-items:center;justify-content:center;color:#94a3b8;font-size:20px;">
      {username[0].upper()}
    </div>
    <div>
      <div style="font-weight:bold;font-size:15px;">{username}</div>
      <div style="color:#8899a6;font-size:13px;">@{username}</div>
    </div>
  </div>
  <div style="font-size:15px;line-height:1.5;white-space:pre-wrap;">{text[:config.max_text_length]}</div>
  <div style="color:#8899a6;font-size:13px;margin-top:12px;padding-top:12px;border-top:1px solid #38444d;">
    {datetime.now().strftime("%H:%M · %Y年%m月%d日")}
  </div>
</div>'''

    def _render_instagram_preview(self, config, text, image_url, username, profile_image) -> str:
        img_html = f'<img src="{image_url}" style="width:100%;aspect-ratio:1/1;object-fit:cover;" />' if image_url else '<div style="width:100%;aspect-ratio:1/1;background:#262626;display:flex;align-items:center;justify-content:center;color:#666;">画像プレビュー</div>'
        return f'''
<div style="background:#000;border-radius:8px;max-width:{config.preview_width}px;font-family:sans-serif;color:#fff;overflow:hidden;">
  <div style="display:flex;align-items:center;padding:12px;">
    <div style="width:32px;height:32px;border-radius:50%;background:#333;margin-right:10px;display:flex;align-items:center;justify-content:center;font-size:14px;">{username[0].upper()}</div>
    <span style="font-weight:600;font-size:14px;">{username}</span>
  </div>
  {img_html}
  <div style="padding:12px;">
    <div style="display:flex;gap:16px;margin-bottom:8px;">
      <span>♡</span><span>💬</span><span>↗</span>
    </div>
    <div style="font-size:14px;line-height:1.4;">
      <span style="font-weight:600;">{username}</span> {text[:150]}{'...' if len(text) > 150 else ''}
    </div>
  </div>
</div>'''

    def _render_threads_preview(self, config, text, image_url, username, profile_image) -> str:
        img_html = f'<img src="{image_url}" style="width:100%;border-radius:8px;margin-top:8px;" />' if image_url else ''
        return f'''
<div style="background:#101010;border-radius:12px;padding:16px;max-width:{config.preview_width}px;font-family:sans-serif;color:#fff;">
  <div style="display:flex;align-items:center;margin-bottom:12px;">
    <div style="width:36px;height:36px;border-radius:50%;background:#333;margin-right:10px;display:flex;align-items:center;justify-content:center;">{username[0].upper()}</div>
    <div>
      <span style="font-weight:600;font-size:14px;">{username}</span>
      <span style="color:#777;font-size:12px;margin-left:8px;">1分前</span>
    </div>
  </div>
  <div style="font-size:15px;line-height:1.5;">{text[:config.max_text_length]}</div>
  {img_html}
</div>'''

    def _render_tiktok_preview(self, config, text, image_url, username) -> str:
        img_html = f'background-image:url({image_url});background-size:cover;background-position:center;' if image_url else 'background:#111;'
        return f'''
<div style="border-radius:12px;max-width:{config.preview_width}px;height:{config.preview_height}px;font-family:sans-serif;color:#fff;position:relative;overflow:hidden;{img_html}">
  <div style="position:absolute;bottom:0;left:0;right:0;padding:16px;background:linear-gradient(transparent,rgba(0,0,0,0.8));">
    <div style="font-weight:bold;font-size:16px;margin-bottom:4px;">@{username}</div>
    <div style="font-size:14px;line-height:1.4;">{text[:100]}{'...' if len(text) > 100 else ''}</div>
  </div>
</div>'''

    def _render_line_preview(self, config, text, image_url) -> str:
        img_html = f'<img src="{image_url}" style="width:100%;border-radius:8px;margin-bottom:8px;" />' if image_url else ''
        return f'''
<div style="background:#7494c0;border-radius:12px;padding:20px;max-width:{config.preview_width}px;font-family:sans-serif;">
  <div style="background:#fff;border-radius:12px;padding:12px;max-width:80%;">
    {img_html}
    <div style="font-size:14px;line-height:1.5;color:#333;">{text[:200]}{'...' if len(text) > 200 else ''}</div>
  </div>
  <div style="color:rgba(255,255,255,0.7);font-size:11px;margin-top:4px;">既読 {datetime.now().strftime("%H:%M")}</div>
</div>'''


# テスト用
if __name__ == "__main__":
    service = PreviewService()

    text = "本日のFXトレード結果\n\n日次損益: +¥17,000\n取引回数: 12回\n勝率: 66.7%\n\n#FX #トレード #XM"

    # 全SNSプレビュー
    previews = service.generate_all_previews(
        platforms=["x", "instagram", "threads", "tiktok", "line"],
        text=text,
        image_url="https://example.com/trade_report.jpg",
        hashtags=["FX", "トレード"],
        username="fx_trader",
    )

    for p in previews:
        status = "⚠️" if p.warnings else "✓"
        print(f"{status} {p.display_name}: {p.text_length}/{p.max_length}文字 "
              f"{'(切り詰め)' if p.text_truncated else ''}")
        for w in p.warnings:
            print(f"  警告: {w}")
        print(f"  HTML: {len(p.preview_html)}文字")

    print("\n✓ プレビューサービス テスト完了")
