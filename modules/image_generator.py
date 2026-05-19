"""
画像自動生成モジュール
======================
Pillowを使用して、取引データをテンプレート画像に合成し、
SNS投稿用の画像を自動生成します。

【使い方】
    from modules.image_generator import ImageGenerator
    from modules.utils import create_sample_trade_data
    
    generator = ImageGenerator()
    trade_data = create_sample_trade_data()
    output_path = generator.generate(trade_data)
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.utils import TradeData, format_date_jp

logger = logging.getLogger(__name__)

# プロジェクトルート
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output"


class ImageGenerator:
    """
    取引データからSNS投稿用画像を生成するクラス。
    """

    # デフォルトの画像サイズ（Instagram推奨: 1080x1080）
    DEFAULT_WIDTH = 1080
    DEFAULT_HEIGHT = 1080

    # カラーパレット
    COLORS = {
        "background_dark": (15, 15, 25),        # ダークネイビー
        "background_gradient": (25, 35, 65),     # グラデーション用
        "profit_green": (0, 230, 118),           # プラス損益（緑）
        "loss_red": (255, 82, 82),               # マイナス損益（赤）
        "text_white": (255, 255, 255),           # 白テキスト
        "text_light": (200, 200, 220),           # 薄い白テキスト
        "text_gold": (255, 215, 0),              # ゴールドテキスト
        "accent_blue": (66, 133, 244),           # アクセントブルー
        "card_bg": (30, 40, 70),                 # カード背景
        "card_border": (60, 80, 130),            # カードボーダー
        "divider": (50, 60, 100),                # 区切り線
    }

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        template_path: Optional[str] = None,
        font_bold_path: Optional[str] = None,
        font_regular_path: Optional[str] = None,
    ):
        self.width = width
        self.height = height
        self.template_path = template_path

        # フォントパスの設定
        self.font_bold_path = font_bold_path or str(FONTS_DIR / "NotoSansJP-Bold.otf")
        self.font_regular_path = font_regular_path or str(FONTS_DIR / "NotoSansJP-Regular.otf")

        # 出力ディレクトリの作成
        OUTPUT_DIR.mkdir(exist_ok=True)

    def _load_font(self, path: str, size: int) -> ImageFont.FreeTypeFont:
        """フォントを読み込みます。"""
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            logger.warning(f"フォント読み込み失敗: {path}、デフォルトフォントを使用します")
            return ImageFont.load_default()

    def _create_gradient_background(self) -> Image.Image:
        """グラデーション背景を生成します。"""
        img = Image.new("RGB", (self.width, self.height), self.COLORS["background_dark"])
        draw = ImageDraw.Draw(img)

        # 上から下へのグラデーション
        c1 = self.COLORS["background_dark"]
        c2 = self.COLORS["background_gradient"]

        for y in range(self.height):
            ratio = y / self.height
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        return img

    def _draw_rounded_rect(
        self,
        draw: ImageDraw.Draw,
        xy: Tuple[int, int, int, int],
        fill: Tuple[int, int, int],
        outline: Optional[Tuple[int, int, int]] = None,
        radius: int = 20,
        outline_width: int = 2
    ):
        """角丸の四角形を描画します。"""
        x1, y1, x2, y2 = xy
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=radius,
            fill=fill,
            outline=outline,
            width=outline_width
        )

    def _draw_text_centered(
        self,
        draw: ImageDraw.Draw,
        text: str,
        y: int,
        font: ImageFont.FreeTypeFont,
        fill: Tuple[int, int, int],
        x_offset: int = 0
    ):
        """テキストを水平方向中央に描画します。"""
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        x = (self.width - text_width) // 2 + x_offset
        draw.text((x, y), text, font=font, fill=fill)

    def generate(
        self,
        trade_data: TradeData,
        output_path: Optional[Path] = None,
        line_openchat_url: str = ""
    ) -> Path:
        """
        取引データから投稿用画像を生成します。
        
        Args:
            trade_data: 取引データ
            output_path: 出力先パス（デフォルト: output/ディレクトリ）
            line_openchat_url: LINEオープンチャットURL
        
        Returns:
            Path: 生成された画像のパス
        """
        logger.info(f"画像生成開始: {trade_data.date}")

        # テンプレート画像の読み込み、またはグラデーション背景の生成
        if self.template_path and Path(self.template_path).exists():
            img = Image.open(self.template_path).resize(
                (self.width, self.height), Image.LANCZOS
            )
            # テンプレート画像にダーク半透明オーバーレイを追加
            overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 140))
            img = img.convert("RGBA")
            img = Image.alpha_composite(img, overlay)
            img = img.convert("RGB")
        else:
            img = self._create_gradient_background()

        draw = ImageDraw.Draw(img)

        # フォントの読み込み
        font_title = self._load_font(self.font_bold_path, 42)
        font_date = self._load_font(self.font_regular_path, 28)
        font_profit_large = self._load_font(self.font_bold_path, 80)
        font_profit_label = self._load_font(self.font_regular_path, 24)
        font_stats_value = self._load_font(self.font_bold_path, 36)
        font_stats_label = self._load_font(self.font_regular_path, 20)
        font_footer = self._load_font(self.font_regular_path, 22)
        font_cta = self._load_font(self.font_bold_path, 26)

        # 損益に応じた色の決定
        profit_color = (
            self.COLORS["profit_green"] if trade_data.is_profitable
            else self.COLORS["loss_red"]
        )

        # ===== 描画開始 =====

        y_cursor = 40

        # --- ヘッダー: タイトル ---
        self._draw_text_centered(
            draw, "DAILY TRADE REPORT",
            y_cursor, font_title, self.COLORS["text_gold"]
        )
        y_cursor += 60

        # --- 日付 ---
        date_text = format_date_jp(trade_data.date)
        self._draw_text_centered(
            draw, date_text,
            y_cursor, font_date, self.COLORS["text_light"]
        )
        y_cursor += 50

        # --- 区切り線 ---
        line_margin = 100
        draw.line(
            [(line_margin, y_cursor), (self.width - line_margin, y_cursor)],
            fill=self.COLORS["divider"], width=2
        )
        y_cursor += 30

        # --- メインカード: 日次損益 ---
        card_margin = 60
        card_height = 200
        self._draw_rounded_rect(
            draw,
            (card_margin, y_cursor, self.width - card_margin, y_cursor + card_height),
            fill=self.COLORS["card_bg"],
            outline=profit_color,
            radius=20,
            outline_width=3
        )

        # 「本日の損益」ラベル
        self._draw_text_centered(
            draw, "本日の損益",
            y_cursor + 25, font_profit_label, self.COLORS["text_light"]
        )

        # 損益金額（大きく表示）
        self._draw_text_centered(
            draw, trade_data.net_profit_str,
            y_cursor + 65, font_profit_large, profit_color
        )

        y_cursor += card_height + 30

        # --- 統計カード群（3列） ---
        stats = [
            ("取引回数", f"{trade_data.total_trades}回"),
            ("勝率", f"{trade_data.win_rate:.1f}%"),
            ("勝敗", f"{trade_data.winning_trades}勝{trade_data.losing_trades}敗"),
        ]

        card_w = (self.width - card_margin * 2 - 20 * 2) // 3
        card_h = 110

        for i, (label, value) in enumerate(stats):
            x1 = card_margin + i * (card_w + 20)
            x2 = x1 + card_w

            self._draw_rounded_rect(
                draw,
                (x1, y_cursor, x2, y_cursor + card_h),
                fill=self.COLORS["card_bg"],
                outline=self.COLORS["card_border"],
                radius=15,
                outline_width=1
            )

            # ラベル
            bbox = draw.textbbox((0, 0), label, font=font_stats_label)
            lw = bbox[2] - bbox[0]
            draw.text(
                ((x1 + x2 - lw) // 2, y_cursor + 15),
                label, font=font_stats_label, fill=self.COLORS["text_light"]
            )

            # 値
            bbox = draw.textbbox((0, 0), value, font=font_stats_value)
            vw = bbox[2] - bbox[0]
            draw.text(
                ((x1 + x2 - vw) // 2, y_cursor + 50),
                value, font=font_stats_value, fill=self.COLORS["text_white"]
            )

        y_cursor += card_h + 25

        # --- 累計損益カード ---
        cum_card_h = 100
        cum_color = (
            self.COLORS["profit_green"] if trade_data.cumulative_profit >= 0
            else self.COLORS["loss_red"]
        )

        self._draw_rounded_rect(
            draw,
            (card_margin, y_cursor, self.width - card_margin, y_cursor + cum_card_h),
            fill=self.COLORS["card_bg"],
            outline=self.COLORS["card_border"],
            radius=15,
            outline_width=1
        )

        self._draw_text_centered(
            draw, "累計損益",
            y_cursor + 12, font_profit_label, self.COLORS["text_light"]
        )

        font_cum_value = self._load_font(self.font_bold_path, 44)
        self._draw_text_centered(
            draw, trade_data.cumulative_profit_str,
            y_cursor + 45, font_cum_value, cum_color
        )

        y_cursor += cum_card_h + 30

        # --- 区切り線 ---
        draw.line(
            [(line_margin, y_cursor), (self.width - line_margin, y_cursor)],
            fill=self.COLORS["divider"], width=2
        )
        y_cursor += 25

        # --- CTA（LINEオープンチャット誘導） ---
        cta_text = "詳しい手法はLINEオープンチャットで公開中！"
        self._draw_text_centered(
            draw, cta_text,
            y_cursor, font_cta, self.COLORS["text_gold"]
        )
        y_cursor += 40

        if line_openchat_url:
            self._draw_text_centered(
                draw, f"▼ 参加はこちら ▼",
                y_cursor, font_footer, self.COLORS["accent_blue"]
            )
            y_cursor += 30
            self._draw_text_centered(
                draw, line_openchat_url,
                y_cursor, font_footer, self.COLORS["text_light"]
            )

        # --- フッター: プラットフォーム情報 ---
        footer_text = f"Powered by {trade_data.platform} | XM Trading"
        bbox = draw.textbbox((0, 0), footer_text, font=font_stats_label)
        fw = bbox[2] - bbox[0]
        draw.text(
            ((self.width - fw) // 2, self.height - 45),
            footer_text, font=font_stats_label,
            fill=(100, 110, 140)
        )

        # ===== 画像の保存 =====
        if output_path is None:
            output_path = OUTPUT_DIR / f"trade_report_{trade_data.date}.jpg"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        img.save(str(output_path), "JPEG", quality=95)
        logger.info(f"画像生成完了: {output_path}")

        return output_path


def main():
    """画像生成のテスト実行。"""
    from modules.utils import create_sample_trade_data, setup_logger

    log_dir = BASE_DIR / "logs"
    setup_logger("modules.image_generator", log_dir)

    generator = ImageGenerator()
    trade_data = create_sample_trade_data()

    output_path = generator.generate(
        trade_data,
        line_openchat_url="https://line.me/ti/g2/xxxxx"
    )

    print(f"\n画像を生成しました: {output_path}")


if __name__ == "__main__":
    main()
