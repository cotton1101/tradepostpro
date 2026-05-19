"""
TradePost Pro - カスタムテンプレートレンダラー
ユーザーが定義したカスタム設定に基づいて画像を生成する
"""

import logging
import os
import uuid
from typing import Dict, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
FONT_BOLD = os.path.join(ASSETS_DIR, "fonts", "NotoSansJP-Bold.otf")
FONT_REGULAR = os.path.join(ASSETS_DIR, "fonts", "NotoSansJP-Regular.otf")


def hex_to_rgb(hex_color: str) -> tuple:
    """HEXカラーをRGBタプルに変換"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def render_custom_template(
    config: Dict,
    trade_data: Dict,
    output_dir: Optional[str] = None,
) -> str:
    """カスタムテンプレート設定に基づいて画像を生成"""
    colors = config.get("colors", {})
    layout = config.get("layout", {})
    fonts_config = config.get("fonts", {})

    # デフォルト値
    width = layout.get("width", 1080)
    height = layout.get("height", 1080)
    padding = layout.get("padding", 40)
    card_radius = layout.get("card_radius", 15)

    bg_color = colors.get("background", "#0d1117")
    card_bg = colors.get("card_bg", "#161b22")
    card_border = colors.get("card_border", "#30363d")
    text_primary = colors.get("text_primary", "#ffffff")
    text_secondary = colors.get("text_secondary", "#8b949e")
    profit_color = colors.get("profit_color", "#00d4aa")
    loss_color = colors.get("loss_color", "#ff4757")
    accent_color = colors.get("accent_color", "#00d4aa")
    footer_bg = colors.get("footer_bg", "#00d4aa")
    footer_text_color = colors.get("footer_text", "#0d1117")

    # フォントサイズ
    title_size = fonts_config.get("title_size", 36)
    profit_size = fonts_config.get("profit_size", 72)
    label_size = fonts_config.get("label_size", 22)
    value_size = fonts_config.get("value_size", 32)
    footer_size = fonts_config.get("footer_size", 24)

    # 画像作成
    img = Image.new("RGB", (width, height), bg_color)
    draw = ImageDraw.Draw(img)

    # フォント読み込み
    try:
        font_title = ImageFont.truetype(FONT_BOLD, title_size)
        font_profit = ImageFont.truetype(FONT_BOLD, profit_size)
        font_label = ImageFont.truetype(FONT_REGULAR, label_size)
        font_value = ImageFont.truetype(FONT_BOLD, value_size)
        font_footer = ImageFont.truetype(FONT_BOLD, footer_size)
    except Exception:
        font_title = ImageFont.load_default()
        font_profit = font_title
        font_label = font_title
        font_value = font_title
        font_footer = font_title

    # 背景画像の合成（設定されている場合）
    bg_image_url = config.get("background_image")
    if bg_image_url and os.path.exists(bg_image_url):
        try:
            bg_img = Image.open(bg_image_url).resize((width, height))
            opacity = config.get("background_opacity", 0.3)
            bg_img = Image.blend(
                Image.new("RGB", (width, height), bg_color),
                bg_img,
                alpha=opacity,
            )
            img.paste(bg_img)
            draw = ImageDraw.Draw(img)
        except Exception as e:
            logger.warning(f"背景画像の読み込みに失敗: {e}")

    y = padding

    # ヘッダー
    if layout.get("show_header", True):
        draw.rectangle([(0, 0), (width, y + title_size + 40)], fill=card_bg)
        draw.text((padding, y + 10), "FX Daily Report", fill=text_primary, font=font_title)
        y += title_size + 60

    # 日付
    if layout.get("show_date", True):
        date_str = trade_data.get("date", "2026-03-11")
        draw.text((padding, y), date_str, fill=text_secondary, font=font_label)
        y += label_size + 20

    # メイン損益
    net_profit = trade_data.get("net_profit", 0)
    color = profit_color if net_profit >= 0 else loss_color
    sign = "+" if net_profit >= 0 else ""
    profit_text = f"{sign}{net_profit:,.0f}円"

    draw.text((padding, y), "本日の損益", fill=text_secondary, font=font_label)
    y += label_size + 10
    draw.text((padding, y), profit_text, fill=color, font=font_profit)
    y += profit_size + 30

    # 統計カード
    if layout.get("show_stats_cards", True):
        cards = [
            ("取引回数", f"{trade_data.get('total_trades', 0)}回"),
            ("勝率", f"{trade_data.get('win_rate', 0)}%"),
            ("勝ち", f"{trade_data.get('winning_trades', 0)}回"),
            ("負け", f"{trade_data.get('losing_trades', 0)}回"),
        ]

        card_w = (width - padding * 2 - 20) // 2
        card_h = 90

        for i, (label, value) in enumerate(cards):
            col = i % 2
            row = i // 2
            cx = padding + col * (card_w + 20)
            cy = y + row * (card_h + 15)

            draw.rounded_rectangle(
                [(cx, cy), (cx + card_w, cy + card_h)],
                radius=card_radius,
                fill=card_bg,
                outline=card_border,
            )
            draw.text((cx + 15, cy + 12), label, fill=text_secondary, font=font_label)
            draw.text((cx + 15, cy + 45), value, fill=text_primary, font=font_value)

        y += (card_h + 15) * 2 + 20

    # 勝敗バー
    if layout.get("show_win_loss_bar", True):
        wins = trade_data.get("winning_trades", 0)
        losses = trade_data.get("losing_trades", 0)
        total = wins + losses

        if total > 0:
            bar_width = width - padding * 2
            bar_height = 30
            win_width = int(bar_width * wins / total)

            draw.rounded_rectangle(
                [(padding, y), (padding + bar_width, y + bar_height)],
                radius=bar_height // 2,
                fill=loss_color,
            )
            if win_width > 0:
                draw.rounded_rectangle(
                    [(padding, y), (padding + win_width, y + bar_height)],
                    radius=bar_height // 2,
                    fill=profit_color,
                )

            # ラベル
            y += bar_height + 10
            draw.text(
                (padding, y),
                f"Win {wins}",
                fill=profit_color,
                font=font_label,
            )
            draw.text(
                (width - padding - 80, y),
                f"Loss {losses}",
                fill=loss_color,
                font=font_label,
            )
            y += label_size + 20

    # 累計損益
    if layout.get("show_cumulative", True):
        cumulative = trade_data.get("cumulative_profit", 0)
        cum_color = profit_color if cumulative >= 0 else loss_color
        cum_sign = "+" if cumulative >= 0 else ""

        draw.rounded_rectangle(
            [(padding, y), (width - padding, y + 80)],
            radius=card_radius,
            fill=card_bg,
            outline=card_border,
        )
        draw.text((padding + 15, y + 10), "累計損益", fill=text_secondary, font=font_label)
        draw.text(
            (padding + 15, y + 40),
            f"{cum_sign}{cumulative:,.0f}円",
            fill=cum_color,
            font=font_value,
        )
        y += 100

    # フッター
    if layout.get("show_footer", True):
        footer_h = 50
        draw.rectangle([(0, height - footer_h), (width, height)], fill=footer_bg)
        ft = layout.get("footer_text", "TradePost Pro")
        draw.text((padding, height - footer_h + 12), ft, fill=footer_text_color, font=font_footer)

    # 保存
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    filename = f"custom_{uuid.uuid4().hex[:8]}.jpg"
    output_path = os.path.join(output_dir, filename)
    img.save(output_path, "JPEG", quality=95)
    logger.info(f"カスタムテンプレート画像を生成: {output_path}")
    return output_path


def render_from_config(
    config_json: Dict,
    trade_data: Dict,
    bg_image_dir: str = "",
    return_base64: bool = False,
) -> str:
    """
    ユーザー定義のconfig_jsonに基づいて画像を生成する。
    背景画像の上に各要素を指定座標に描画する。

    Args:
        config_json: {"background": "filename.jpg", "elements": [...]}
        trade_data: {"date": "...", "net_profit": 17000, ...}
        bg_image_dir: 背景画像が保存されているディレクトリパス
        return_base64: Trueの場合、Base64文字列を返す

    Returns:
        ファイルパス or Base64文字列
    """
    import base64
    from io import BytesIO

    width, height = 1080, 1080

    # 背景画像の読み込み
    bg_filename = config_json.get("background", "")
    bg_path = os.path.join(bg_image_dir, bg_filename) if bg_filename and bg_image_dir else ""

    if bg_path and os.path.exists(bg_path):
        try:
            img = Image.open(bg_path).convert("RGB").resize((width, height), Image.LANCZOS)
        except Exception as e:
            logger.warning(f"背景画像読み込み失敗: {e}")
            img = Image.new("RGB", (width, height), "#1a1a2e")
    else:
        img = Image.new("RGB", (width, height), "#1a1a2e")

    draw = ImageDraw.Draw(img)

    # フォント読み込みヘルパー
    def get_font(size: int, bold: bool = False):
        font_path = FONT_BOLD if bold else FONT_REGULAR
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            return ImageFont.load_default()

    # 要素データマッピング
    net_profit = trade_data.get("net_profit", 0)
    cumulative = trade_data.get("cumulative_profit", 0)

    def format_profit(val):
        sign = "+" if val >= 0 else ""
        return f"{sign}{val:,.0f}"

    value_map = {
        "net_profit": format_profit(net_profit) + "円",
        "win_rate": f"{trade_data.get('win_rate', 0):.1f}%",
        "total_trades": f"{trade_data.get('total_trades', 0)}回",
        "date": trade_data.get("date", ""),
        "cumulative_profit": format_profit(cumulative) + "円",
        "winning_trades": f"{trade_data.get('winning_trades', 0)}勝",
        "losing_trades": f"{trade_data.get('losing_trades', 0)}敗",
    }

    # 要素描画
    elements = config_json.get("elements", [])
    for elem in elements:
        etype = elem.get("type", "")
        x = int(elem.get("x", 0))
        y = int(elem.get("y", 0))
        font_size = int(elem.get("fontSize", 32))
        color = elem.get("color", "#ffffff")
        bold = elem.get("bold", False)
        font = get_font(font_size, bold)

        if etype in value_map:
            text = value_map[etype]
            # 損益系は色分け
            if etype == "net_profit":
                color = elem.get("profitColor", "#00ff00") if net_profit >= 0 else elem.get("lossColor", "#ff0000")
            elif etype == "cumulative_profit":
                color = elem.get("profitColor", "#00ff00") if cumulative >= 0 else elem.get("lossColor", "#ff0000")
        elif etype in ("custom_text", "label"):
            text = elem.get("text", "")
        else:
            continue

        if text:
            draw.text((x, y), text, fill=color, font=font)

    # 出力
    if return_base64:
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=95)
        buffer.seek(0)
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)
    filename = f"custom_{uuid.uuid4().hex[:8]}.jpg"
    output_path = os.path.join(output_dir, filename)
    img.save(output_path, "JPEG", quality=95)
    logger.info(f"カスタムテンプレート画像を生成: {output_path}")
    return output_path


if __name__ == "__main__":
    # テスト: 各プリセットの設定でレンダリング
    test_configs = [
        {
            "name": "ダークカスタム",
            "colors": {
                "background": "#0d1117",
                "card_bg": "#161b22",
                "card_border": "#30363d",
                "text_primary": "#ffffff",
                "text_secondary": "#8b949e",
                "profit_color": "#00d4aa",
                "loss_color": "#ff4757",
                "accent_color": "#00d4aa",
                "footer_bg": "#00d4aa",
                "footer_text": "#0d1117",
            },
            "layout": {
                "width": 1080,
                "height": 1080,
                "padding": 40,
                "card_radius": 15,
                "show_header": True,
                "show_stats_cards": True,
                "show_win_loss_bar": True,
                "show_footer": True,
                "show_cumulative": True,
                "show_date": True,
                "footer_text": "TradePost Pro",
            },
            "fonts": {
                "title_size": 36,
                "profit_size": 72,
                "label_size": 22,
                "value_size": 32,
                "footer_size": 24,
            },
        },
        {
            "name": "ネオンカスタム",
            "colors": {
                "background": "#0a0a1a",
                "card_bg": "#1a1a3e",
                "card_border": "#4a00e0",
                "text_primary": "#ffffff",
                "text_secondary": "#b0b0ff",
                "profit_color": "#00ff88",
                "loss_color": "#ff0055",
                "accent_color": "#ff00ff",
                "footer_bg": "#4a00e0",
                "footer_text": "#ffffff",
            },
            "layout": {
                "width": 1080,
                "height": 1080,
                "footer_text": "Neon Trading",
            },
            "fonts": {},
        },
    ]

    sample_data = {
        "date": "2026-03-11",
        "net_profit": 17000,
        "total_trades": 12,
        "winning_trades": 8,
        "losing_trades": 4,
        "win_rate": 66.7,
        "cumulative_profit": 230000,
    }

    for config in test_configs:
        path = render_custom_template(config=config, trade_data=sample_data)
        print(f"{config['name']}: {path}")
