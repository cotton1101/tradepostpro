"""
マルチテンプレート画像生成モジュール
====================================
5種類のテンプレートを提供し、プランに応じた画像を生成します。

基本テンプレート（ライトプラン以上）:
  1. dark_classic   — ダーククラシック（既存デザインの改良版）
  2. neon_glow      — ネオングロー（サイバーパンク風）
  3. minimal_white  — ミニマルホワイト（シンプル白背景）

プレミアムテンプレート（スタンダードプラン以上）:
  4. gold_luxury    — ゴールドラグジュアリー（高級感）
  5. gradient_wave  — グラデーションウェーブ（モダン）
"""

import logging
import math
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List

from PIL import Image, ImageDraw, ImageFont, ImageFilter

from modules.utils import TradeData, format_date_jp

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "assets" / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

FONT_BOLD = str(FONTS_DIR / "NotoSansJP-Bold.otf")
FONT_REGULAR = str(FONTS_DIR / "NotoSansJP-Regular.otf")


# ============================================================
# テンプレート定義
# ============================================================

TEMPLATE_REGISTRY: Dict[str, dict] = {
    "dark_classic": {
        "name": "ダーククラシック",
        "description": "落ち着いたダークテーマ。信頼感のあるプロフェッショナルなデザイン。",
        "min_plan": "light",
        "template_type": "basic",
    },
    "neon_glow": {
        "name": "ネオングロー",
        "description": "サイバーパンク風のネオンカラー。目を引く派手なデザイン。",
        "min_plan": "light",
        "template_type": "basic",
    },
    "minimal_white": {
        "name": "ミニマルホワイト",
        "description": "白背景のシンプルデザイン。清潔感と読みやすさ重視。",
        "min_plan": "light",
        "template_type": "basic",
    },
    "gold_luxury": {
        "name": "ゴールドラグジュアリー",
        "description": "黒×金の高級感あるデザイン。プレミアム感を演出。",
        "min_plan": "standard",
        "template_type": "premium",
    },
    "gradient_wave": {
        "name": "グラデーションウェーブ",
        "description": "モダンなグラデーション。トレンド感のあるデザイン。",
        "min_plan": "standard",
        "template_type": "premium",
    },
}


def get_available_templates(plan: str = "light") -> List[dict]:
    """プランに応じた利用可能テンプレート一覧を返す"""
    plan_hierarchy = {"light": 0, "standard": 1, "premium": 2}
    user_level = plan_hierarchy.get(plan, 0)

    result = []
    for tid, info in TEMPLATE_REGISTRY.items():
        tmpl_level = plan_hierarchy.get(info["min_plan"], 0)
        result.append({
            "id": tid,
            **info,
            "available": user_level >= tmpl_level,
        })
    return result


# ============================================================
# 共通ヘルパー
# ============================================================

def _load_font(path: str, size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        return ImageFont.load_default()


def _center_text(draw, text, y, font, fill, width):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (width - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, font=font, fill=fill)


def _draw_stats_row(draw, stats, y, card_margin, width, font_label, font_value, 
                     label_color, value_color, bg_color, border_color):
    """統計カード行を描画"""
    card_w = (width - card_margin * 2 - 20 * 2) // 3
    card_h = 110
    for i, (label, value) in enumerate(stats):
        x1 = card_margin + i * (card_w + 20)
        x2 = x1 + card_w
        draw.rounded_rectangle([x1, y, x2, y + card_h], radius=15,
                                fill=bg_color, outline=border_color, width=1)
        bbox = draw.textbbox((0, 0), label, font=font_label)
        lw = bbox[2] - bbox[0]
        draw.text(((x1 + x2 - lw) // 2, y + 15), label, font=font_label, fill=label_color)
        bbox = draw.textbbox((0, 0), value, font=font_value)
        vw = bbox[2] - bbox[0]
        draw.text(((x1 + x2 - vw) // 2, y + 50), value, font=font_value, fill=value_color)
    return card_h


# ============================================================
# テンプレート1: ダーククラシック
# ============================================================

def render_dark_classic(trade_data: TradeData, width: int, height: int,
                         line_url: str = "") -> Image.Image:
    """ダーククラシックテンプレート"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # グラデーション背景
    for y in range(height):
        r = y / height
        draw.line([(0, y), (width, y)], fill=(int(15 + r * 10), int(15 + r * 20), int(25 + r * 40)))

    # フォント
    f_title = _load_font(FONT_BOLD, 42)
    f_date = _load_font(FONT_REGULAR, 28)
    f_profit = _load_font(FONT_BOLD, 80)
    f_label = _load_font(FONT_REGULAR, 24)
    f_stat_v = _load_font(FONT_BOLD, 36)
    f_stat_l = _load_font(FONT_REGULAR, 20)
    f_cum = _load_font(FONT_BOLD, 44)
    f_cta = _load_font(FONT_BOLD, 26)
    f_footer = _load_font(FONT_REGULAR, 22)

    profit_color = (0, 230, 118) if trade_data.is_profitable else (255, 82, 82)
    cum_color = (0, 230, 118) if trade_data.cumulative_profit >= 0 else (255, 82, 82)

    y_pos = 40
    _center_text(draw, "DAILY TRADE REPORT", y_pos, f_title, (255, 215, 0), width)
    y_pos += 60
    _center_text(draw, format_date_jp(trade_data.date), y_pos, f_date, (200, 200, 220), width)
    y_pos += 50
    draw.line([(100, y_pos), (width - 100, y_pos)], fill=(50, 60, 100), width=2)
    y_pos += 30

    # メインカード
    m = 60
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 200], radius=20,
                            fill=(30, 40, 70), outline=profit_color, width=3)
    _center_text(draw, "本日の損益", y_pos + 25, f_label, (200, 200, 220), width)
    _center_text(draw, trade_data.net_profit_str, y_pos + 65, f_profit, profit_color, width)
    y_pos += 230

    # 統計
    stats = [("取引回数", f"{trade_data.total_trades}回"),
             ("勝率", f"{trade_data.win_rate:.1f}%"),
             ("勝敗", f"{trade_data.winning_trades}勝{trade_data.losing_trades}敗")]
    ch = _draw_stats_row(draw, stats, y_pos, m, width, f_stat_l, f_stat_v,
                          (200, 200, 220), (255, 255, 255), (30, 40, 70), (60, 80, 130))
    y_pos += ch + 25

    # 累計
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 100], radius=15,
                            fill=(30, 40, 70), outline=(60, 80, 130), width=1)
    _center_text(draw, "累計損益", y_pos + 12, f_label, (200, 200, 220), width)
    _center_text(draw, trade_data.cumulative_profit_str, y_pos + 45, f_cum, cum_color, width)
    y_pos += 130

    draw.line([(100, y_pos), (width - 100, y_pos)], fill=(50, 60, 100), width=2)
    y_pos += 25
    _center_text(draw, "詳しい手法はLINEオープンチャットで公開中！", y_pos, f_cta, (255, 215, 0), width)
    y_pos += 40
    if line_url:
        _center_text(draw, "▼ プロフィールリンクから参加 ▼", y_pos, f_footer, (66, 133, 244), width)

    bbox = draw.textbbox((0, 0), f"Powered by {trade_data.platform} | XM Trading", font=f_stat_l)
    fw = bbox[2] - bbox[0]
    draw.text(((width - fw) // 2, height - 45),
              f"Powered by {trade_data.platform} | XM Trading", font=f_stat_l, fill=(100, 110, 140))

    return img


# ============================================================
# テンプレート2: ネオングロー
# ============================================================

def render_neon_glow(trade_data: TradeData, width: int, height: int,
                      line_url: str = "") -> Image.Image:
    """ネオングロー（サイバーパンク風）テンプレート"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 黒背景 + 紫グラデーション
    for y in range(height):
        r = y / height
        draw.line([(0, y), (width, y)], fill=(int(5 + r * 15), int(0), int(15 + r * 30)))

    # グリッドライン（サイバーパンク風）
    for gy in range(0, height, 60):
        draw.line([(0, gy), (width, gy)], fill=(30, 0, 60), width=1)
    for gx in range(0, width, 60):
        draw.line([(gx, 0), (gx, height)], fill=(30, 0, 60), width=1)

    f_title = _load_font(FONT_BOLD, 44)
    f_date = _load_font(FONT_REGULAR, 26)
    f_profit = _load_font(FONT_BOLD, 85)
    f_label = _load_font(FONT_REGULAR, 24)
    f_stat_v = _load_font(FONT_BOLD, 38)
    f_stat_l = _load_font(FONT_REGULAR, 20)
    f_cum = _load_font(FONT_BOLD, 46)
    f_cta = _load_font(FONT_BOLD, 26)
    f_footer = _load_font(FONT_REGULAR, 20)

    neon_cyan = (0, 255, 255)
    neon_pink = (255, 0, 200)
    neon_green = (0, 255, 100)
    neon_red = (255, 50, 80)

    profit_color = neon_green if trade_data.is_profitable else neon_red
    cum_color = neon_green if trade_data.cumulative_profit >= 0 else neon_red

    y_pos = 35
    _center_text(draw, "DAILY TRADE REPORT", y_pos, f_title, neon_cyan, width)
    y_pos += 55
    _center_text(draw, format_date_jp(trade_data.date), y_pos, f_date, neon_pink, width)
    y_pos += 50

    # ネオンライン
    draw.line([(50, y_pos), (width - 50, y_pos)], fill=neon_cyan, width=2)
    y_pos += 25

    # メインカード（ネオンボーダー）
    m = 50
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 210], radius=5,
                            fill=(10, 5, 25), outline=profit_color, width=3)
    # グロー効果（外側にもう一つ薄い枠）
    draw.rounded_rectangle([m - 3, y_pos - 3, width - m + 3, y_pos + 213], radius=8,
                            outline=(*profit_color[:2], profit_color[2] // 3), width=1)

    _center_text(draw, "本日の損益", y_pos + 25, f_label, (150, 150, 200), width)
    _center_text(draw, trade_data.net_profit_str, y_pos + 65, f_profit, profit_color, width)
    y_pos += 240

    # 統計（ネオンスタイル）
    stats = [("TRADES", f"{trade_data.total_trades}"),
             ("WIN RATE", f"{trade_data.win_rate:.1f}%"),
             ("W / L", f"{trade_data.winning_trades} / {trade_data.losing_trades}")]
    card_w = (width - m * 2 - 20 * 2) // 3
    card_h = 110
    for i, (label, value) in enumerate(stats):
        x1 = m + i * (card_w + 20)
        x2 = x1 + card_w
        draw.rounded_rectangle([x1, y_pos, x2, y_pos + card_h], radius=5,
                                fill=(10, 5, 25), outline=neon_cyan, width=2)
        bbox = draw.textbbox((0, 0), label, font=f_stat_l)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 12),
                  label, font=f_stat_l, fill=neon_pink)
        bbox = draw.textbbox((0, 0), value, font=f_stat_v)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 48),
                  value, font=f_stat_v, fill=(255, 255, 255))
    y_pos += card_h + 25

    # 累計
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 100], radius=5,
                            fill=(10, 5, 25), outline=neon_pink, width=2)
    _center_text(draw, "CUMULATIVE P&L", y_pos + 10, f_label, neon_pink, width)
    _center_text(draw, trade_data.cumulative_profit_str, y_pos + 45, f_cum, cum_color, width)
    y_pos += 130

    _center_text(draw, "LINEオープンチャットで手法を公開中！", y_pos, f_cta, neon_cyan, width)
    y_pos += 40
    _center_text(draw, "▼ プロフィールリンクから参加 ▼", y_pos, f_footer, neon_pink, width)

    return img


# ============================================================
# テンプレート3: ミニマルホワイト
# ============================================================

def render_minimal_white(trade_data: TradeData, width: int, height: int,
                          line_url: str = "") -> Image.Image:
    """ミニマルホワイト（シンプル白背景）テンプレート"""
    img = Image.new("RGB", (width, height), (250, 250, 252))
    draw = ImageDraw.Draw(img)

    f_title = _load_font(FONT_BOLD, 38)
    f_date = _load_font(FONT_REGULAR, 24)
    f_profit = _load_font(FONT_BOLD, 76)
    f_label = _load_font(FONT_REGULAR, 22)
    f_stat_v = _load_font(FONT_BOLD, 34)
    f_stat_l = _load_font(FONT_REGULAR, 18)
    f_cum = _load_font(FONT_BOLD, 40)
    f_cta = _load_font(FONT_BOLD, 24)
    f_footer = _load_font(FONT_REGULAR, 20)

    dark = (30, 30, 40)
    gray = (120, 120, 130)
    light_gray = (220, 220, 225)
    green = (16, 185, 129)
    red = (239, 68, 68)
    accent = (59, 130, 246)

    profit_color = green if trade_data.is_profitable else red
    cum_color = green if trade_data.cumulative_profit >= 0 else red

    # 上部アクセントバー
    draw.rectangle([(0, 0), (width, 6)], fill=accent)

    y_pos = 50
    _center_text(draw, "Daily Trade Report", y_pos, f_title, dark, width)
    y_pos += 55
    _center_text(draw, format_date_jp(trade_data.date), y_pos, f_date, gray, width)
    y_pos += 50
    draw.line([(80, y_pos), (width - 80, y_pos)], fill=light_gray, width=1)
    y_pos += 35

    # メインカード（白背景に影風）
    m = 60
    # シャドウ
    draw.rounded_rectangle([m + 4, y_pos + 4, width - m + 4, y_pos + 200 + 4], radius=16,
                            fill=(230, 230, 235))
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 200], radius=16,
                            fill=(255, 255, 255), outline=light_gray, width=1)
    _center_text(draw, "本日の損益", y_pos + 28, f_label, gray, width)
    _center_text(draw, trade_data.net_profit_str, y_pos + 68, f_profit, profit_color, width)
    y_pos += 230

    # 統計（ミニマルスタイル）
    stats = [("取引回数", f"{trade_data.total_trades}回"),
             ("勝率", f"{trade_data.win_rate:.1f}%"),
             ("勝敗", f"{trade_data.winning_trades}勝{trade_data.losing_trades}敗")]
    card_w = (width - m * 2 - 20 * 2) // 3
    card_h = 100
    for i, (label, value) in enumerate(stats):
        x1 = m + i * (card_w + 20)
        x2 = x1 + card_w
        draw.rounded_rectangle([x1 + 3, y_pos + 3, x2 + 3, y_pos + card_h + 3], radius=12,
                                fill=(235, 235, 240))
        draw.rounded_rectangle([x1, y_pos, x2, y_pos + card_h], radius=12,
                                fill=(255, 255, 255), outline=light_gray, width=1)
        bbox = draw.textbbox((0, 0), label, font=f_stat_l)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 15),
                  label, font=f_stat_l, fill=gray)
        bbox = draw.textbbox((0, 0), value, font=f_stat_v)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 48),
                  value, font=f_stat_v, fill=dark)
    y_pos += card_h + 25

    # 累計
    draw.rounded_rectangle([m + 3, y_pos + 3, width - m + 3, y_pos + 93], radius=12,
                            fill=(235, 235, 240))
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 90], radius=12,
                            fill=(255, 255, 255), outline=light_gray, width=1)
    _center_text(draw, "累計損益", y_pos + 10, f_label, gray, width)
    _center_text(draw, trade_data.cumulative_profit_str, y_pos + 42, f_cum, cum_color, width)
    y_pos += 120

    draw.line([(80, y_pos), (width - 80, y_pos)], fill=light_gray, width=1)
    y_pos += 25
    _center_text(draw, "LINEオープンチャットで手法を公開中！", y_pos, f_cta, accent, width)
    y_pos += 40
    _center_text(draw, "▼ プロフィールリンクから参加 ▼", y_pos, f_footer, gray, width)

    # 下部アクセントバー
    draw.rectangle([(0, height - 6), (width, height)], fill=accent)

    return img


# ============================================================
# テンプレート4: ゴールドラグジュアリー（プレミアム）
# ============================================================

def render_gold_luxury(trade_data: TradeData, width: int, height: int,
                        line_url: str = "") -> Image.Image:
    """ゴールドラグジュアリー（黒×金の高級デザイン）テンプレート"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # 黒背景
    for y in range(height):
        r = y / height
        draw.line([(0, y), (width, y)], fill=(int(8 + r * 5), int(8 + r * 5), int(10 + r * 5)))

    f_title = _load_font(FONT_BOLD, 40)
    f_date = _load_font(FONT_REGULAR, 26)
    f_profit = _load_font(FONT_BOLD, 82)
    f_label = _load_font(FONT_REGULAR, 24)
    f_stat_v = _load_font(FONT_BOLD, 36)
    f_stat_l = _load_font(FONT_REGULAR, 20)
    f_cum = _load_font(FONT_BOLD, 44)
    f_cta = _load_font(FONT_BOLD, 26)
    f_footer = _load_font(FONT_REGULAR, 20)

    gold = (212, 175, 55)
    gold_light = (255, 223, 100)
    gold_dark = (160, 130, 40)
    white = (240, 240, 240)
    green = (80, 220, 120)
    red = (220, 60, 60)

    profit_color = green if trade_data.is_profitable else red
    cum_color = green if trade_data.cumulative_profit >= 0 else red

    # 上部ゴールドライン
    draw.rectangle([(0, 0), (width, 4)], fill=gold)
    draw.rectangle([(0, 8), (width, 9)], fill=gold_dark)

    y_pos = 45
    _center_text(draw, "DAILY TRADE REPORT", y_pos, f_title, gold, width)
    y_pos += 55

    # 装飾ライン
    center = width // 2
    draw.line([(center - 200, y_pos), (center - 30, y_pos)], fill=gold_dark, width=1)
    draw.line([(center + 30, y_pos), (center + 200, y_pos)], fill=gold_dark, width=1)
    # ダイヤモンド装飾
    d = 8
    draw.polygon([(center, y_pos - d), (center + d, y_pos), (center, y_pos + d), (center - d, y_pos)],
                  fill=gold)
    y_pos += 20

    _center_text(draw, format_date_jp(trade_data.date), y_pos, f_date, (180, 180, 180), width)
    y_pos += 55

    # メインカード（ゴールドボーダー）
    m = 55
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 210], radius=3,
                            fill=(18, 18, 22), outline=gold, width=2)
    # 内側の装飾ライン
    draw.rounded_rectangle([m + 8, y_pos + 8, width - m - 8, y_pos + 202], radius=1,
                            outline=gold_dark, width=1)

    _center_text(draw, "本日の損益", y_pos + 28, f_label, gold_light, width)
    _center_text(draw, trade_data.net_profit_str, y_pos + 70, f_profit, profit_color, width)
    y_pos += 240

    # 統計
    stats = [("取引回数", f"{trade_data.total_trades}回"),
             ("勝率", f"{trade_data.win_rate:.1f}%"),
             ("勝敗", f"{trade_data.winning_trades}勝{trade_data.losing_trades}敗")]
    card_w = (width - m * 2 - 16 * 2) // 3
    card_h = 105
    for i, (label, value) in enumerate(stats):
        x1 = m + i * (card_w + 16)
        x2 = x1 + card_w
        draw.rounded_rectangle([x1, y_pos, x2, y_pos + card_h], radius=3,
                                fill=(18, 18, 22), outline=gold_dark, width=1)
        bbox = draw.textbbox((0, 0), label, font=f_stat_l)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 14),
                  label, font=f_stat_l, fill=gold)
        bbox = draw.textbbox((0, 0), value, font=f_stat_v)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 50),
                  value, font=f_stat_v, fill=white)
    y_pos += card_h + 22

    # 累計
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 100], radius=3,
                            fill=(18, 18, 22), outline=gold_dark, width=1)
    _center_text(draw, "累計損益", y_pos + 12, f_label, gold, width)
    _center_text(draw, trade_data.cumulative_profit_str, y_pos + 45, f_cum, cum_color, width)
    y_pos += 130

    # ゴールドライン
    draw.line([(m, y_pos), (width - m, y_pos)], fill=gold_dark, width=1)
    y_pos += 22
    _center_text(draw, "LINEオープンチャットで手法を公開中！", y_pos, f_cta, gold_light, width)
    y_pos += 38
    _center_text(draw, "▼ プロフィールリンクから参加 ▼", y_pos, f_footer, gold, width)

    # 下部ゴールドライン
    draw.rectangle([(0, height - 9), (width, height - 8)], fill=gold_dark)
    draw.rectangle([(0, height - 4), (width, height)], fill=gold)

    return img


# ============================================================
# テンプレート5: グラデーションウェーブ（プレミアム）
# ============================================================

def render_gradient_wave(trade_data: TradeData, width: int, height: int,
                          line_url: str = "") -> Image.Image:
    """グラデーションウェーブ（モダン）テンプレート"""
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)

    # パープル→ブルーのグラデーション
    for y in range(height):
        r = y / height
        rv = int(88 - r * 50)
        gv = int(28 + r * 50)
        bv = int(135 + r * 80)
        draw.line([(0, y), (width, y)], fill=(max(0, rv), max(0, gv), min(255, bv)))

    # ウェーブ装飾
    for wave_y in [250, 650]:
        for x in range(width):
            offset = int(15 * math.sin(x / 80 + wave_y / 100))
            wy = wave_y + offset
            draw.line([(x, wy), (x, wy + 2)], fill=(255, 255, 255, 30))

    f_title = _load_font(FONT_BOLD, 42)
    f_date = _load_font(FONT_REGULAR, 26)
    f_profit = _load_font(FONT_BOLD, 80)
    f_label = _load_font(FONT_REGULAR, 24)
    f_stat_v = _load_font(FONT_BOLD, 36)
    f_stat_l = _load_font(FONT_REGULAR, 20)
    f_cum = _load_font(FONT_BOLD, 44)
    f_cta = _load_font(FONT_BOLD, 26)
    f_footer = _load_font(FONT_REGULAR, 20)

    white = (255, 255, 255)
    light = (220, 220, 240)
    green = (134, 239, 172)
    red = (252, 165, 165)
    card_bg = (255, 255, 255, 25)

    profit_color = green if trade_data.is_profitable else red
    cum_color = green if trade_data.cumulative_profit >= 0 else red

    y_pos = 45
    _center_text(draw, "Daily Trade Report", y_pos, f_title, white, width)
    y_pos += 55
    _center_text(draw, format_date_jp(trade_data.date), y_pos, f_date, light, width)
    y_pos += 55

    # メインカード
    m = 55
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 200], radius=20,
                            fill=(30, 15, 60), outline=(120, 100, 200), width=2)
    _center_text(draw, "本日の損益", y_pos + 25, f_label, light, width)
    _center_text(draw, trade_data.net_profit_str, y_pos + 65, f_profit, profit_color, width)
    y_pos += 230

    # 統計
    stats = [("\u53d6\u5f15\u56de\u6570", f"{trade_data.total_trades}\u56de"),
             ("\u52dd\u7387", f"{trade_data.win_rate:.1f}%"),
             ("\u52dd\u6557", f"{trade_data.winning_trades}\u52dd{trade_data.losing_trades}\u6557")]
    card_w = (width - m * 2 - 20 * 2) // 3
    card_h = 105
    for i, (label, value) in enumerate(stats):
        x1 = m + i * (card_w + 20)
        x2 = x1 + card_w
        draw.rounded_rectangle([x1, y_pos, x2, y_pos + card_h], radius=15,
                                fill=(40, 20, 80), outline=(100, 80, 180), width=1)
        bbox = draw.textbbox((0, 0), label, font=f_stat_l)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 14),
                  label, font=f_stat_l, fill=light)
        bbox = draw.textbbox((0, 0), value, font=f_stat_v)
        draw.text(((x1 + x2 - (bbox[2] - bbox[0])) // 2, y_pos + 50),
                  value, font=f_stat_v, fill=white)
    y_pos += card_h + 25

    # 累計
    draw.rounded_rectangle([m, y_pos, width - m, y_pos + 95], radius=15,
                            fill=(40, 20, 80), outline=(100, 80, 180), width=1)
    _center_text(draw, "\u7d2f\u8a08\u640d\u76ca", y_pos + 10, f_label, light, width)
    _center_text(draw, trade_data.cumulative_profit_str, y_pos + 42, f_cum, cum_color, width)
    y_pos += 125

    _center_text(draw, "LINEオープンチャットで手法を公開中！", y_pos, f_cta, white, width)
    y_pos += 38
    _center_text(draw, "▼ プロフィールリンクから参加 ▼", y_pos, f_footer, light, width)

    return img


# ============================================================
# テンプレートレンダラー（統合）
# ============================================================

RENDERERS = {
    "dark_classic": render_dark_classic,
    "neon_glow": render_neon_glow,
    "minimal_white": render_minimal_white,
    "gold_luxury": render_gold_luxury,
    "gradient_wave": render_gradient_wave,
}


def render_template(
    template_id: str,
    trade_data: TradeData,
    width: int = 1080,
    height: int = 1080,
    output_path: Optional[str] = None,
    line_url: str = "",
) -> str:
    """
    指定テンプレートで画像を生成して保存します。
    
    Args:
        template_id: テンプレートID
        trade_data: 取引データ
        width: 画像幅
        height: 画像高さ
        output_path: 出力パス
        line_url: LINEオープンチャットURL
    
    Returns:
        str: 生成された画像のファイルパス
    """
    renderer = RENDERERS.get(template_id)
    if not renderer:
        raise ValueError(f"不明なテンプレートID: {template_id}。利用可能: {list(RENDERERS.keys())}")

    img = renderer(trade_data, width, height, line_url)

    if not output_path:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(OUTPUT_DIR / f"trade_{template_id}_{trade_data.date}.jpg")

    img.save(output_path, "JPEG", quality=95)
    logger.info(f"テンプレート '{template_id}' で画像生成完了: {output_path}")
    return output_path


# ============================================================
# テスト実行
# ============================================================

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(BASE_DIR))
    logging.basicConfig(level=logging.INFO)

    from modules.utils import create_sample_trade_data
    trade = create_sample_trade_data()

    print("全テンプレートの画像を生成中...")
    for tid in RENDERERS:
        path = render_template(tid, trade, line_url="https://line.me/ti/g2/xxxxx")
        print(f"  {tid}: {path}")
    print("完了！")
