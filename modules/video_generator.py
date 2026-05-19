"""
動画自動生成モジュール
======================
MoviePyを使用して取引結果のスライドショー動画を自動生成します。

生成される動画:
  - 1080x1920 (9:16 縦型 / TikTok・Instagram Reels向け)
  - 15秒間のスライドショー
  - ダークテーマ、アニメーション付き
  - BGM対応（オプション）

【前提条件】
  pip install moviepy pillow numpy
  
  MoviePy 1.x系を使用。ffmpegが必要です。
  sudo apt-get install ffmpeg
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont
import numpy as np

logger = logging.getLogger(__name__)

# パス設定
BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"
OUTPUT_DIR = BASE_DIR / "output"

# フォント
FONT_BOLD = str(FONTS_DIR / "NotoSansJP-Bold.otf")
FONT_REGULAR = str(FONTS_DIR / "NotoSansJP-Regular.otf")

# 動画設定
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30
DURATION = 15  # 秒


class VideoGenerator:
    """取引結果の動画を自動生成するクラス"""

    def __init__(
        self,
        width: int = VIDEO_WIDTH,
        height: int = VIDEO_HEIGHT,
        fps: int = FPS,
        duration: int = DURATION,
        bg_image_path: Optional[str] = None,
    ):
        """
        Args:
            width: 動画の幅
            height: 動画の高さ
            fps: フレームレート
            duration: 動画の長さ（秒）
            bg_image_path: 背景画像パス（オプション）
        """
        self.width = width
        self.height = height
        self.fps = fps
        self.duration = duration
        self.bg_image_path = bg_image_path

        # フォントの読み込み
        try:
            self.font_title = ImageFont.truetype(FONT_BOLD, 72)
            self.font_large = ImageFont.truetype(FONT_BOLD, 96)
            self.font_medium = ImageFont.truetype(FONT_BOLD, 48)
            self.font_small = ImageFont.truetype(FONT_REGULAR, 36)
            self.font_tiny = ImageFont.truetype(FONT_REGULAR, 28)
        except OSError:
            logger.warning("日本語フォントが見つかりません。デフォルトフォントを使用します。")
            self.font_title = ImageFont.load_default()
            self.font_large = ImageFont.load_default()
            self.font_medium = ImageFont.load_default()
            self.font_small = ImageFont.load_default()
            self.font_tiny = ImageFont.load_default()

    def _create_gradient_bg(self) -> Image.Image:
        """グラデーション背景を生成"""
        img = Image.new("RGB", (self.width, self.height))
        draw = ImageDraw.Draw(img)

        # ダークグラデーション（上: 濃い青 → 下: 濃い紫）
        for y in range(self.height):
            ratio = y / self.height
            r = int(10 + ratio * 20)
            g = int(15 + ratio * 5)
            b = int(40 + ratio * 30)
            draw.line([(0, y), (self.width, y)], fill=(r, g, b))

        return img

    def _create_frame_intro(self, trade_data: dict, progress: float) -> np.ndarray:
        """イントロフレーム（タイトル表示）"""
        img = self._create_gradient_bg()
        draw = ImageDraw.Draw(img)

        # フェードイン効果
        alpha = min(1.0, progress * 3)

        # 日付
        date_str = trade_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        date_color = tuple(int(200 * alpha) for _ in range(3))
        bbox = draw.textbbox((0, 0), date_str, font=self.font_medium)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 400), date_str, fill=date_color, font=self.font_medium)

        # タイトル
        title = "本日のトレード結果"
        title_color = tuple(int(255 * alpha) for _ in range(3))
        bbox = draw.textbbox((0, 0), title, font=self.font_title)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 500), title, fill=title_color, font=self.font_title)

        # 装飾ライン
        line_width = int(300 * alpha)
        center_x = self.width // 2
        line_color = (int(100 * alpha), int(150 * alpha), int(255 * alpha))
        draw.line(
            [(center_x - line_width, 620), (center_x + line_width, 620)],
            fill=line_color, width=3
        )

        return np.array(img)

    def _create_frame_profit(self, trade_data: dict, progress: float) -> np.ndarray:
        """損益表示フレーム"""
        img = self._create_gradient_bg()
        draw = ImageDraw.Draw(img)

        net_profit = trade_data.get("net_profit", 0)
        is_positive = net_profit >= 0

        # スライドイン効果
        offset_y = int(50 * max(0, 1 - progress * 3))

        # ラベル
        label = "本日の損益"
        bbox = draw.textbbox((0, 0), label, font=self.font_medium)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 350 + offset_y), label, fill=(180, 180, 180), font=self.font_medium)

        # 損益金額（大きく表示）
        sign = "+" if is_positive else ""
        profit_text = f"{sign}{net_profit:,.0f}円"
        profit_color = (0, 230, 118) if is_positive else (255, 82, 82)

        bbox = draw.textbbox((0, 0), profit_text, font=self.font_large)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 480 + offset_y), profit_text, fill=profit_color, font=self.font_large)

        # 累計損益
        cumulative = trade_data.get("cumulative_profit", 0)
        cum_sign = "+" if cumulative >= 0 else ""
        cum_text = f"累計: {cum_sign}{cumulative:,.0f}円"
        cum_color = (0, 200, 100) if cumulative >= 0 else (255, 100, 100)

        bbox = draw.textbbox((0, 0), cum_text, font=self.font_medium)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 650 + offset_y), cum_text, fill=cum_color, font=self.font_medium)

        return np.array(img)

    def _create_frame_stats(self, trade_data: dict, progress: float) -> np.ndarray:
        """統計情報フレーム"""
        img = self._create_gradient_bg()
        draw = ImageDraw.Draw(img)

        # 統計データ
        stats = [
            ("取引回数", f"{trade_data.get('total_trades', 0)}回"),
            ("勝率", f"{trade_data.get('win_rate', 0):.1f}%"),
            ("勝ち", f"{trade_data.get('winning_trades', 0)}回"),
            ("負け", f"{trade_data.get('losing_trades', 0)}回"),
        ]

        # カード表示
        card_width = 400
        card_height = 160
        gap = 30
        start_x = (self.width - card_width * 2 - gap) // 2
        start_y = 350

        for i, (label, value) in enumerate(stats):
            # フェードイン（順番にアニメーション）
            item_progress = max(0, min(1, (progress * 4) - i * 0.3))
            if item_progress <= 0:
                continue

            col = i % 2
            row = i // 2
            x = start_x + col * (card_width + gap)
            y = start_y + row * (card_height + gap)

            # カード背景
            alpha_val = int(40 * item_progress)
            draw.rounded_rectangle(
                [(x, y), (x + card_width, y + card_height)],
                radius=15,
                fill=(255, 255, 255, alpha_val)
            )
            # カード枠線
            draw.rounded_rectangle(
                [(x, y), (x + card_width, y + card_height)],
                radius=15,
                outline=(60, 80, 120, int(100 * item_progress)),
                width=2
            )

            # ラベル
            label_color = tuple([int(160 * item_progress)] * 3)
            bbox = draw.textbbox((0, 0), label, font=self.font_small)
            lx = x + (card_width - (bbox[2] - bbox[0])) // 2
            draw.text((lx, y + 25), label, fill=label_color, font=self.font_small)

            # 値
            value_color = tuple([int(255 * item_progress)] * 3)
            bbox = draw.textbbox((0, 0), value, font=self.font_medium)
            vx = x + (card_width - (bbox[2] - bbox[0])) // 2
            draw.text((vx, y + 80), value, fill=value_color, font=self.font_medium)

        return np.array(img)

    def _create_frame_cta(self, trade_data: dict, progress: float, line_url: str = "") -> np.ndarray:
        """CTA（LINEオープンチャット誘導）フレーム"""
        img = self._create_gradient_bg()
        draw = ImageDraw.Draw(img)

        alpha = min(1.0, progress * 2)

        # メインテキスト
        main_text = "毎日の結果を配信中!"
        main_color = tuple([int(255 * alpha)] * 3)
        bbox = draw.textbbox((0, 0), main_text, font=self.font_title)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 450), main_text, fill=main_color, font=self.font_title)

        # LINE誘導
        line_text = "LINEオープンチャットで"
        bbox = draw.textbbox((0, 0), line_text, font=self.font_medium)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        line_color = (int(0 * alpha), int(195 * alpha), int(0 * alpha))
        draw.text((x, 620), line_text, fill=line_color, font=self.font_medium)

        line_text2 = "リアルタイム情報をGET"
        bbox = draw.textbbox((0, 0), line_text2, font=self.font_medium)
        x = (self.width - (bbox[2] - bbox[0])) // 2
        draw.text((x, 690), line_text2, fill=line_color, font=self.font_medium)

        # ボタン風デザイン
        btn_text = "プロフィールリンクから参加"
        bbox = draw.textbbox((0, 0), btn_text, font=self.font_small)
        btn_w = bbox[2] - bbox[0] + 80
        btn_h = 70
        btn_x = (self.width - btn_w) // 2
        btn_y = 830

        # パルスアニメーション
        import math
        pulse = 1.0 + 0.03 * math.sin(progress * 10 * math.pi)
        pulse_w = int(btn_w * pulse)
        pulse_h = int(btn_h * pulse)
        pulse_x = (self.width - pulse_w) // 2
        pulse_y = btn_y - int((pulse_h - btn_h) / 2)

        draw.rounded_rectangle(
            [(pulse_x, pulse_y), (pulse_x + pulse_w, pulse_y + pulse_h)],
            radius=35,
            fill=(0, int(180 * alpha), 0)
        )
        text_x = pulse_x + (pulse_w - (bbox[2] - bbox[0])) // 2
        text_y = pulse_y + (pulse_h - (bbox[3] - bbox[1])) // 2
        draw.text((text_x, text_y), btn_text, fill=(255, 255, 255), font=self.font_small)

        return np.array(img)

    def generate(
        self,
        trade_data: dict,
        output_path: Optional[str] = None,
        line_url: str = "",
        bgm_path: Optional[str] = None,
    ) -> str:
        """
        取引結果の動画を生成します。
        
        Args:
            trade_data: 取引データ辞書
            output_path: 出力ファイルパス
            line_url: LINEオープンチャットURL
            bgm_path: BGM音声ファイルパス（オプション）
        
        Returns:
            str: 生成された動画のファイルパス
        """
        try:
            from moviepy import VideoClip, AudioFileClip
        except ImportError:
            try:
                from moviepy.editor import VideoClip, AudioFileClip
            except ImportError:
                raise ImportError("moviepyパッケージが必要です: pip install moviepy")

        if not output_path:
            date_str = trade_data.get("date", datetime.now().strftime("%Y-%m-%d"))
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(OUTPUT_DIR / f"trade_video_{date_str}.mp4")

        total_frames = self.fps * self.duration

        # シーン定義（開始秒, 終了秒, フレーム生成関数）
        scenes = [
            (0, 4, self._create_frame_intro),       # 0-4秒: イントロ
            (4, 9, self._create_frame_profit),       # 4-9秒: 損益表示
            (9, 12, self._create_frame_stats),       # 9-12秒: 統計情報
            (12, 15, self._create_frame_cta),        # 12-15秒: CTA
        ]

        def make_frame(t):
            """時間tに対応するフレームを生成"""
            for start, end, frame_func in scenes:
                if start <= t < end:
                    progress = (t - start) / (end - start)
                    if frame_func == self._create_frame_cta:
                        return frame_func(trade_data, progress, line_url)
                    return frame_func(trade_data, progress)
            # フォールバック
            return self._create_frame_cta(trade_data, 1.0, line_url)

        logger.info(f"動画生成開始: {self.width}x{self.height}, {self.duration}秒, {self.fps}fps")

        # VideoClip作成
        clip = VideoClip(make_frame, duration=self.duration)
        clip = clip.with_fps(self.fps)

        # BGM追加（オプション）
        if bgm_path and os.path.exists(bgm_path):
            try:
                audio = AudioFileClip(bgm_path).subclipped(0, self.duration)
                audio = audio.with_volume_scaled(0.3)  # 音量30%
                clip = clip.with_audio(audio)
                logger.info("BGMを追加しました")
            except Exception as e:
                logger.warning(f"BGM追加に失敗: {e}")

        # 動画書き出し
        clip.write_videofile(
            output_path,
            fps=self.fps,
            codec="libx264",
            audio_codec="aac",
            preset="medium",
            bitrate="5000k",
            logger=None,  # MoviePyのログを抑制
        )

        clip.close()

        file_size = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"動画生成完了: {output_path} ({file_size:.1f}MB)")

        return output_path


def generate_trade_video(
    trade_data: dict,
    output_path: Optional[str] = None,
    line_url: str = "",
    bgm_path: Optional[str] = None,
) -> str:
    """
    取引結果の動画を生成する便利関数。
    
    Args:
        trade_data: 取引データ辞書
        output_path: 出力ファイルパス
        line_url: LINEオープンチャットURL
        bgm_path: BGM音声ファイルパス
    
    Returns:
        str: 生成された動画のファイルパス
    """
    generator = VideoGenerator()
    return generator.generate(trade_data, output_path, line_url, bgm_path)


# ============================================================
# テスト実行
# ============================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    sample_data = {
        "date": "2026-03-11",
        "net_profit": 45230,
        "cumulative_profit": 328450,
        "total_trades": 8,
        "winning_trades": 6,
        "losing_trades": 2,
        "win_rate": 75.0,
    }

    print("動画生成テスト開始...")
    path = generate_trade_video(
        trade_data=sample_data,
        line_url="https://line.me/ti/g2/xxxxx"
    )
    print(f"生成完了: {path}")
