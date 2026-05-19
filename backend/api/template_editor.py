"""
TradePost Pro - カスタム画像テンプレートエディタ API
ユーザーがブラウザ上で画像テンプレートをカスタマイズできるAPIエンドポイント
"""

import json
import logging
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["Template Editor"])


# === Pydantic モデル ===

class TemplateColors(BaseModel):
    """テンプレートカラー設定"""
    background: str = Field(default="#0d1117", description="背景色")
    card_bg: str = Field(default="#161b22", description="カード背景色")
    card_border: str = Field(default="#30363d", description="カード枠線色")
    text_primary: str = Field(default="#ffffff", description="メインテキスト色")
    text_secondary: str = Field(default="#8b949e", description="サブテキスト色")
    profit_color: str = Field(default="#00d4aa", description="利益時の色")
    loss_color: str = Field(default="#ff4757", description="損失時の色")
    accent_color: str = Field(default="#00d4aa", description="アクセントカラー")
    footer_bg: str = Field(default="#00d4aa", description="フッター背景色")
    footer_text: str = Field(default="#0d1117", description="フッターテキスト色")


class TemplateLayout(BaseModel):
    """テンプレートレイアウト設定"""
    width: int = Field(default=1080, ge=600, le=1920)
    height: int = Field(default=1080, ge=600, le=1920)
    padding: int = Field(default=40, ge=10, le=100)
    card_radius: int = Field(default=15, ge=0, le=50)
    show_header: bool = Field(default=True)
    show_stats_cards: bool = Field(default=True)
    show_win_loss_bar: bool = Field(default=True)
    show_footer: bool = Field(default=True)
    show_cumulative: bool = Field(default=True)
    show_date: bool = Field(default=True)
    footer_text: str = Field(default="TradePost Pro")


class TemplateFonts(BaseModel):
    """テンプレートフォント設定"""
    title_size: int = Field(default=36, ge=16, le=72)
    profit_size: int = Field(default=72, ge=24, le=120)
    label_size: int = Field(default=22, ge=12, le=48)
    value_size: int = Field(default=32, ge=16, le=64)
    footer_size: int = Field(default=24, ge=12, le=48)


class CustomTemplateConfig(BaseModel):
    """カスタムテンプレート設定"""
    name: str = Field(description="テンプレート名")
    description: str = Field(default="", description="テンプレートの説明")
    colors: TemplateColors = Field(default_factory=TemplateColors)
    layout: TemplateLayout = Field(default_factory=TemplateLayout)
    fonts: TemplateFonts = Field(default_factory=TemplateFonts)
    background_image: Optional[str] = Field(default=None, description="背景画像URL")
    background_opacity: float = Field(default=0.3, ge=0.0, le=1.0)
    logo_url: Optional[str] = Field(default=None, description="ロゴ画像URL")


class TemplatePreviewRequest(BaseModel):
    """プレビューリクエスト"""
    config: CustomTemplateConfig
    sample_data: Optional[Dict] = None


class TemplateListResponse(BaseModel):
    """テンプレート一覧レスポンス"""
    templates: List[Dict]
    total: int


# === プリセットテンプレート ===

PRESET_TEMPLATES = {
    "dark_classic": CustomTemplateConfig(
        name="ダーククラシック",
        description="プロフェッショナルなダークテーマ",
        colors=TemplateColors(
            background="#0d1117",
            accent_color="#00d4aa",
        ),
    ),
    "neon_glow": CustomTemplateConfig(
        name="ネオングロー",
        description="サイバーパンク風ネオンカラー",
        colors=TemplateColors(
            background="#0a0a1a",
            card_bg="#1a1a3e",
            card_border="#4a00e0",
            accent_color="#ff00ff",
            profit_color="#00ff88",
            loss_color="#ff0055",
            footer_bg="#4a00e0",
            footer_text="#ffffff",
        ),
    ),
    "minimal_white": CustomTemplateConfig(
        name="ミニマルホワイト",
        description="シンプルで清潔感のあるホワイトテーマ",
        colors=TemplateColors(
            background="#ffffff",
            card_bg="#f5f5f5",
            card_border="#e0e0e0",
            text_primary="#1a1a1a",
            text_secondary="#666666",
            profit_color="#00b894",
            loss_color="#d63031",
            accent_color="#0984e3",
            footer_bg="#1a1a1a",
            footer_text="#ffffff",
        ),
    ),
    "gold_luxury": CustomTemplateConfig(
        name="ゴールドラグジュアリー",
        description="高級感のあるブラック×ゴールド",
        colors=TemplateColors(
            background="#0a0a0a",
            card_bg="#1a1a1a",
            card_border="#c9a84c",
            text_primary="#ffffff",
            text_secondary="#b0b0b0",
            profit_color="#c9a84c",
            loss_color="#ff4757",
            accent_color="#c9a84c",
            footer_bg="#c9a84c",
            footer_text="#0a0a0a",
        ),
    ),
    "gradient_wave": CustomTemplateConfig(
        name="グラデーションウェーブ",
        description="パープル→ブルーのモダンなグラデーション",
        colors=TemplateColors(
            background="#1a0533",
            card_bg="#2d1b4e",
            card_border="#6c3fa0",
            accent_color="#00b4d8",
            profit_color="#00d4aa",
            loss_color="#ff6b6b",
            footer_bg="#00b4d8",
            footer_text="#ffffff",
        ),
    ),
}


# === APIエンドポイント ===

@router.get("/presets")
async def get_preset_templates():
    """プリセットテンプレート一覧を取得"""
    presets = []
    for key, config in PRESET_TEMPLATES.items():
        presets.append({
            "id": key,
            "name": config.name,
            "description": config.description,
            "colors": config.colors.dict(),
            "layout": config.layout.dict(),
            "fonts": config.fonts.dict(),
        })
    return {"presets": presets, "total": len(presets)}


@router.get("/presets/{template_id}")
async def get_preset_template(template_id: str):
    """プリセットテンプレートの詳細を取得"""
    if template_id not in PRESET_TEMPLATES:
        raise HTTPException(status_code=404, detail="テンプレートが見つかりません")
    config = PRESET_TEMPLATES[template_id]
    return {
        "id": template_id,
        "name": config.name,
        "description": config.description,
        "config": config.dict(),
    }


@router.post("/preview")
async def preview_template(request: TemplatePreviewRequest):
    """テンプレートのプレビュー画像を生成"""
    from modules.custom_template_renderer import render_custom_template

    sample = request.sample_data or {
        "date": "2026-03-11",
        "net_profit": 17000,
        "total_trades": 12,
        "winning_trades": 8,
        "losing_trades": 4,
        "win_rate": 66.7,
        "cumulative_profit": 230000,
    }

    try:
        image_path = render_custom_template(
            config=request.config.dict(),
            trade_data=sample,
            output_dir="/tmp/template_previews",
        )
        return {"preview_url": f"/static/previews/{os.path.basename(image_path)}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"プレビュー生成に失敗: {str(e)}")


@router.post("/save")
async def save_custom_template(config: CustomTemplateConfig):
    """カスタムテンプレートを保存"""
    # ユーザーIDは認証ミドルウェアから取得する想定
    template_id = f"custom_{config.name.replace(' ', '_').lower()}"
    return {
        "id": template_id,
        "name": config.name,
        "message": "テンプレートを保存しました",
    }


@router.get("/colors/palettes")
async def get_color_palettes():
    """カラーパレット候補を取得"""
    palettes = [
        {
            "name": "ダーク",
            "colors": ["#0d1117", "#161b22", "#30363d", "#00d4aa", "#ff4757"],
        },
        {
            "name": "ネオン",
            "colors": ["#0a0a1a", "#1a1a3e", "#4a00e0", "#ff00ff", "#00ff88"],
        },
        {
            "name": "ライト",
            "colors": ["#ffffff", "#f5f5f5", "#e0e0e0", "#0984e3", "#d63031"],
        },
        {
            "name": "ゴールド",
            "colors": ["#0a0a0a", "#1a1a1a", "#c9a84c", "#ffffff", "#ff4757"],
        },
        {
            "name": "オーシャン",
            "colors": ["#0c2340", "#1a3a5c", "#2980b9", "#00d4aa", "#e74c3c"],
        },
        {
            "name": "サンセット",
            "colors": ["#1a0a2e", "#2d1b4e", "#e74c3c", "#f39c12", "#ff6b6b"],
        },
    ]
    return {"palettes": palettes}
