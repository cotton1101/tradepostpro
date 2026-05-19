"""
エフェクト付き動画生成モジュール
テンプレート画像にパーティクルエフェクトをかけて5秒MP4動画を生成
"""

import os
import math
import random
import tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from dataclasses import dataclass, field
from typing import List, Optional

# --- パーティクル定義 ---

@dataclass
class Particle:
    x: float
    y: float
    size: float
    color: tuple  # (R, G, B)
    alpha: float  # 0.0 ~ 1.0
    vx: float = 0.0
    vy: float = 0.0
    lifetime: float = 5.0
    age: float = 0.0
    rotation: float = 0.0
    rotation_speed: float = 0.0

    @property
    def alive(self):
        return self.age < self.lifetime


class ParticleSystem:
    def __init__(self):
        self.particles: List[Particle] = []

    def update(self, dt: float):
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.age += dt
            p.rotation += p.rotation_speed * dt
        self.particles = [p for p in self.particles if p.alive]

    def render(self, base_img: Image.Image) -> Image.Image:
        overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        for p in self.particles:
            if not p.alive:
                continue
            a = int(p.alpha * 255)
            color = (*p.color, a)
            half = p.size / 2
            draw.ellipse(
                [p.x - half, p.y - half, p.x + half, p.y + half],
                fill=color,
            )
        return Image.alpha_composite(base_img, overlay)


# --- エフェクト定義 ---

EFFECTS = {
    "sparkle": {"name": "キラキラ", "description": "星型の光が輝くエフェクト"},
    "confetti": {"name": "紙吹雪", "description": "カラフルな紙吹雪が舞う"},
    "glow_pulse": {"name": "グロー", "description": "画像全体が光る波動"},
    "rising_particles": {"name": "上昇パーティクル", "description": "光の粒が浮かび上がる"},
    "gold_rain": {"name": "ゴールドレイン", "description": "金色の粒が降り注ぐ"},
}


def _draw_star(draw, cx, cy, size, color, alpha):
    """4点の星形を描画"""
    a = int(alpha * 255)
    c = (*color, a)
    points = []
    for i in range(8):
        angle = math.pi / 4 * i - math.pi / 2
        r = size if i % 2 == 0 else size * 0.4
        points.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(points, fill=c)


def _draw_rect(draw, cx, cy, w, h, color, alpha, rotation=0):
    """回転四角形を描画"""
    a = int(alpha * 255)
    c = (*color, a)
    cos_r = math.cos(rotation)
    sin_r = math.sin(rotation)
    corners = [(-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)]
    points = []
    for dx, dy in corners:
        rx = dx * cos_r - dy * sin_r + cx
        ry = dx * sin_r + dy * cos_r + cy
        points.append((rx, ry))
    draw.polygon(points, fill=c)


# --- エフェクトフレーム生成 ---

def _make_sparkle_frame(base_rgba: Image.Image, t: float, duration: float, rng_seed: int) -> Image.Image:
    """キラキラエフェクト: ランダム位置に星が点滅"""
    w, h = base_rgba.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rng = random.Random(rng_seed)
    num_stars = 40
    for i in range(num_stars):
        sx = rng.randint(0, w)
        sy = rng.randint(0, h)
        base_size = rng.uniform(5, 25)
        phase = rng.uniform(0, math.pi * 2)
        speed = rng.uniform(1.5, 4.0)

        # 点滅: sin波で明滅
        alpha = max(0, math.sin(t * speed + phase))
        alpha = alpha ** 1.5  # よりシャープな点滅
        size = base_size * (0.5 + 0.5 * alpha)

        color = rng.choice([
            (255, 255, 255),
            (255, 255, 200),
            (255, 230, 150),
            (200, 220, 255),
        ])
        _draw_star(draw, sx, sy, size, color, alpha * 0.9)

        # グロー
        if alpha > 0.3:
            glow_size = size * 3
            glow_alpha = alpha * 0.2
            a_int = int(glow_alpha * 255)
            draw.ellipse(
                [sx - glow_size, sy - glow_size, sx + glow_size, sy + glow_size],
                fill=(*color, a_int),
            )

    return Image.alpha_composite(base_rgba, overlay)


def _make_confetti_frame(base_rgba: Image.Image, t: float, duration: float, rng_seed: int) -> Image.Image:
    """紙吹雪: カラフルな四角が上から降る"""
    w, h = base_rgba.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rng = random.Random(rng_seed)
    num = 60
    colors = [
        (255, 80, 80), (80, 200, 255), (255, 220, 50),
        (100, 255, 100), (255, 120, 220), (180, 100, 255),
        (255, 160, 50), (50, 220, 180),
    ]

    for i in range(num):
        start_x = rng.uniform(-50, w + 50)
        speed_y = rng.uniform(100, 300)
        speed_x = rng.uniform(-40, 40)
        rot_speed = rng.uniform(-5, 5)
        size_w = rng.uniform(6, 14)
        size_h = rng.uniform(10, 20)
        color = rng.choice(colors)
        delay = rng.uniform(-1, 0)

        eff_t = t + delay
        if eff_t < 0:
            continue

        cx = start_x + speed_x * eff_t
        cy = -30 + speed_y * eff_t
        rotation = rot_speed * eff_t

        # 画面外に出たらループ
        if cy > h + 30:
            cy = cy % (h + 60) - 30

        # ゆらぎ
        cx += math.sin(eff_t * 3 + i) * 20

        alpha = 0.85
        _draw_rect(draw, cx, cy, size_w, size_h, color, alpha, rotation)

    return Image.alpha_composite(base_rgba, overlay)


def _make_glow_pulse_frame(base_rgba: Image.Image, t: float, duration: float, rng_seed: int) -> Image.Image:
    """グローパルス: 画像全体が周期的に明るくなる"""
    # sin波で明るさを変調
    pulse = 0.5 + 0.5 * math.sin(t * 2 * math.pi / 2.0)  # 2秒周期
    brightness = 0.05 + 0.15 * pulse  # 5% ~ 20% の加算

    arr = np.array(base_rgba, dtype=np.float32)
    # 暖色系のグロー
    glow_color = np.array([255, 220, 150, 0], dtype=np.float32)
    arr[:, :, :3] = np.clip(arr[:, :, :3] + glow_color[:3] * brightness, 0, 255)

    # 中心からのビネット風グロー
    h, w = arr.shape[:2]
    cy, cx = h / 2, w / 2
    Y, X = np.mgrid[0:h, 0:w]
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    max_dist = math.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - (dist / max_dist) * 0.5
    vignette = vignette * (0.8 + 0.2 * pulse)

    for c in range(3):
        arr[:, :, c] = np.clip(arr[:, :, c] * vignette, 0, 255)

    return Image.fromarray(arr.astype(np.uint8), "RGBA")


def _make_rising_particles_frame(base_rgba: Image.Image, t: float, duration: float, rng_seed: int) -> Image.Image:
    """上昇パーティクル: 下から上へ光の粒が浮かぶ"""
    w, h = base_rgba.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rng = random.Random(rng_seed)
    num = 50

    for i in range(num):
        start_x = rng.uniform(0, w)
        speed_y = rng.uniform(60, 200)
        size = rng.uniform(3, 10)
        phase = rng.uniform(0, math.pi * 2)
        delay = rng.uniform(0, duration)

        color = rng.choice([
            (255, 255, 255),
            (200, 230, 255),
            (150, 200, 255),
            (255, 200, 150),
        ])

        eff_t = (t + delay) % duration
        cy = h + 20 - speed_y * eff_t
        cx = start_x + math.sin(eff_t * 2 + phase) * 30

        # フェードイン/アウト
        progress = eff_t / duration
        if progress < 0.1:
            alpha = progress / 0.1
        elif progress > 0.8:
            alpha = (1.0 - progress) / 0.2
        else:
            alpha = 1.0
        alpha *= 0.7

        # パーティクル本体
        a_int = int(alpha * 255)
        draw.ellipse(
            [cx - size, cy - size, cx + size, cy + size],
            fill=(*color, a_int),
        )

        # グロー
        glow_size = size * 2.5
        glow_a = int(alpha * 0.25 * 255)
        draw.ellipse(
            [cx - glow_size, cy - glow_size, cx + glow_size, cy + glow_size],
            fill=(*color, glow_a),
        )

    return Image.alpha_composite(base_rgba, overlay)


def _make_gold_rain_frame(base_rgba: Image.Image, t: float, duration: float, rng_seed: int) -> Image.Image:
    """ゴールドレイン: 金色の粒が雨のように降る"""
    w, h = base_rgba.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    rng = random.Random(rng_seed)
    num = 80

    gold_colors = [
        (255, 215, 0),
        (255, 200, 50),
        (255, 180, 30),
        (230, 190, 80),
        (255, 230, 100),
    ]

    for i in range(num):
        start_x = rng.uniform(-20, w + 20)
        speed_y = rng.uniform(150, 400)
        size = rng.uniform(2, 6)
        delay = rng.uniform(-2, 0)
        color = rng.choice(gold_colors)

        eff_t = t + delay
        if eff_t < 0:
            continue

        cy = -20 + speed_y * eff_t
        # ループ
        cy = cy % (h + 40) - 20
        cx = start_x + math.sin(eff_t * 1.5 + i * 0.5) * 10

        alpha = 0.6 + 0.3 * math.sin(eff_t * 4 + i)

        # 縦長の楕円（雨粒風）
        a_int = int(alpha * 255)
        stretch = size * 2.5
        draw.ellipse(
            [cx - size, cy - stretch, cx + size, cy + stretch],
            fill=(*color, a_int),
        )

        # 軌跡
        trail_a = int(alpha * 0.15 * 255)
        trail_len = speed_y * 0.05
        draw.line(
            [(cx, cy), (cx, cy - trail_len)],
            fill=(*color, trail_a),
            width=max(1, int(size * 0.8)),
        )

    return Image.alpha_composite(base_rgba, overlay)


# --- フレーム生成ディスパッチ ---

FRAME_GENERATORS = {
    "sparkle": _make_sparkle_frame,
    "confetti": _make_confetti_frame,
    "glow_pulse": _make_glow_pulse_frame,
    "rising_particles": _make_rising_particles_frame,
    "gold_rain": _make_gold_rain_frame,
}


# --- メイン関数 ---

def generate_effect_video(
    image_path: str,
    effect_type: str,
    duration: float = 5.0,
    fps: int = 24,
    output_path: Optional[str] = None,
) -> str:
    """
    テンプレート画像にエフェクトをかけてMP4動画を生成

    Args:
        image_path: 入力画像パス
        effect_type: エフェクトタイプ (sparkle, confetti, glow_pulse, rising_particles, gold_rain)
        duration: 動画の長さ（秒）
        fps: フレームレート
        output_path: 出力ファイルパス（Noneの場合は自動生成）

    Returns:
        生成された動画ファイルのパス
    """
    if effect_type not in FRAME_GENERATORS:
        raise ValueError(f"Unknown effect type: {effect_type}. Available: {list(FRAME_GENERATORS.keys())}")

    # 入力画像を読み込み
    base_img = Image.open(image_path).convert("RGBA")

    # 出力パス
    if output_path is None:
        output_path = tempfile.mktemp(suffix=".mp4", prefix="effect_video_")

    frame_gen = FRAME_GENERATORS[effect_type]
    rng_seed = random.randint(0, 100000)

    def make_frame(t):
        """MoviePy用のフレーム生成関数"""
        frame_rgba = frame_gen(base_img, t, duration, rng_seed)
        # RGBAをRGBに変換（白背景合成）
        rgb = Image.new("RGB", frame_rgba.size, (255, 255, 255))
        rgb.paste(frame_rgba, mask=frame_rgba.split()[3])
        return np.array(rgb)

    # MoviePyで動画化
    from moviepy import VideoClip

    clip = VideoClip(make_frame, duration=duration)
    clip.write_videofile(
        output_path,
        fps=fps,
        codec="libx264",
        audio=False,
        logger=None,
    )

    return output_path


def get_available_effects() -> list:
    """利用可能なエフェクト一覧を返す"""
    return [
        {"id": eid, "name": info["name"], "description": info["description"]}
        for eid, info in EFFECTS.items()
    ]
