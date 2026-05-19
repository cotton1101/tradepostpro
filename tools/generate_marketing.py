"""
TradePost Pro - マーケティング素材生成スクリプト
OGP画像、SNS宣伝テンプレート、バナー画像を自動生成します。
"""

import os
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# フォントパス
FONT_DIR = Path(__file__).parent.parent / "assets" / "fonts"
FONT_BOLD = str(FONT_DIR / "NotoSansJP-Bold.otf")
FONT_REGULAR = str(FONT_DIR / "NotoSansJP-Regular.otf")
OUTPUT_DIR = Path(__file__).parent.parent / "marketing"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except (IOError, OSError):
        return ImageFont.load_default()


def draw_rounded_rect(draw, xy, radius, fill, outline=None, width=0):
    """角丸矩形を描画"""
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def generate_ogp_image():
    """OGP画像（1200x630）を生成"""
    W, H = 1200, 630
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # グラデーション背景
    for y in range(H):
        r = int(10 + (25 - 10) * y / H)
        g = int(10 + (15 - 10) * y / H)
        b = int(30 + (60 - 30) * y / H)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    # アクセントライン
    for i in range(3):
        y_pos = 150 + i * 150
        draw.line([(0, y_pos), (W, y_pos)], fill=(0, 200, 150, 30), width=1)

    # メインタイトル
    font_title = load_font(FONT_BOLD, 64)
    font_sub = load_font(FONT_BOLD, 32)
    font_desc = load_font(FONT_REGULAR, 24)

    # ロゴ風テキスト
    draw.text((80, 60), "TradePost", fill=(0, 200, 150), font=font_title, anchor="lt")
    draw.text((80 + draw.textlength("TradePost", font=font_title) + 10, 60), "Pro",
              fill=(255, 255, 255), font=font_title, anchor="lt")

    # キャッチコピー
    draw.text((80, 160), "FX取引結果をSNSに自動投稿", fill=(255, 255, 255), font=font_sub)
    draw.text((80, 210), "MT4/MT5の取引データを毎日自動で5つのSNSに配信", fill=(180, 180, 200), font=font_desc)

    # 対応SNSアイコン風テキスト
    sns_list = ["X", "Instagram", "Threads", "TikTok", "LINE"]
    x_pos = 80
    for sns in sns_list:
        bbox = draw.textbbox((0, 0), sns, font=load_font(FONT_BOLD, 20))
        tw = bbox[2] - bbox[0]
        draw_rounded_rect(draw, (x_pos, 290, x_pos + tw + 30, 325), radius=8, fill=(0, 200, 150, 180))
        draw.text((x_pos + 15, 293), sns, fill=(255, 255, 255), font=load_font(FONT_BOLD, 20))
        x_pos += tw + 50

    # 特徴テキスト
    features = [
        "完全自動 — 設定後は放置でOK",
        "5種類のデザインテンプレート",
        "動画生成対応（プレミアム）",
    ]
    for i, feat in enumerate(features):
        y = 380 + i * 45
        draw.text((100, y), "●", fill=(0, 200, 150), font=load_font(FONT_BOLD, 20))
        draw.text((130, y), feat, fill=(220, 220, 240), font=load_font(FONT_REGULAR, 22))

    # フッター
    draw.rectangle([(0, H - 60), (W, H)], fill=(0, 200, 150))
    draw.text((W // 2, H - 30), "月額1,980円から  |  今すぐ無料で始める",
              fill=(10, 10, 30), font=load_font(FONT_BOLD, 24), anchor="mm")

    path = OUTPUT_DIR / "ogp_image.jpg"
    img.save(str(path), "JPEG", quality=95)
    print(f"OGP画像を生成: {path}")
    return path


def generate_x_promo():
    """X (Twitter) 宣伝用画像（1200x675 16:9）"""
    W, H = 1200, 675
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # ダークグラデーション背景
    for y in range(H):
        r = int(15 + (5 - 15) * y / H)
        g = int(15 + (5 - 15) * y / H)
        b = int(35 + (20 - 35) * y / H)
        draw.line([(0, y), (W, y)], fill=(max(0, r), max(0, g), max(0, b)))

    # ネオンアクセント
    draw.rectangle([(0, 0), (W, 5)], fill=(0, 200, 150))
    draw.rectangle([(0, H - 5), (W, H)], fill=(0, 200, 150))

    font_big = load_font(FONT_BOLD, 56)
    font_mid = load_font(FONT_BOLD, 36)
    font_sm = load_font(FONT_REGULAR, 24)

    # メインメッセージ
    draw.text((W // 2, 100), "FXの取引結果、", fill=(255, 255, 255), font=font_big, anchor="mm")
    draw.text((W // 2, 170), "まだ手動で投稿してますか？", fill=(0, 200, 150), font=font_big, anchor="mm")

    # サブメッセージ
    draw.text((W // 2, 280), "TradePost Pro なら", fill=(200, 200, 220), font=font_mid, anchor="mm")
    draw.text((W // 2, 330), "MT4/MT5 → 5つのSNSに完全自動投稿", fill=(255, 255, 255), font=font_mid, anchor="mm")

    # 特徴カード
    cards = [
        ("毎朝7時", "自動投稿"),
        ("5つのSNS", "同時配信"),
        ("月額1,980円", "から利用可能"),
    ]
    card_w = 300
    card_h = 120
    start_x = (W - (card_w * 3 + 40 * 2)) // 2
    for i, (title, desc) in enumerate(cards):
        x = start_x + i * (card_w + 40)
        y = 420
        draw_rounded_rect(draw, (x, y, x + card_w, y + card_h), radius=12,
                          fill=(30, 30, 60), outline=(0, 200, 150), width=2)
        draw.text((x + card_w // 2, y + 35), title, fill=(0, 200, 150),
                  font=load_font(FONT_BOLD, 28), anchor="mm")
        draw.text((x + card_w // 2, y + 80), desc, fill=(200, 200, 220),
                  font=load_font(FONT_REGULAR, 20), anchor="mm")

    # CTA
    draw.text((W // 2, H - 40), "#TradePostPro #FX自動投稿 #XMアフィリエイト",
              fill=(100, 100, 130), font=load_font(FONT_REGULAR, 18), anchor="mm")

    path = OUTPUT_DIR / "x_promo.jpg"
    img.save(str(path), "JPEG", quality=95)
    print(f"X宣伝画像を生成: {path}")
    return path


def generate_instagram_promo():
    """Instagram 宣伝用画像（1080x1080 正方形）"""
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # パープル→ブルーグラデーション
    for y in range(H):
        r = int(80 - 60 * y / H)
        g = int(20 + 30 * y / H)
        b = int(120 + 80 * y / H)
        draw.line([(0, y), (W, y)], fill=(max(0, r), max(0, g), min(255, b)))

    font_big = load_font(FONT_BOLD, 52)
    font_mid = load_font(FONT_BOLD, 36)
    font_sm = load_font(FONT_REGULAR, 24)
    font_xs = load_font(FONT_REGULAR, 20)

    # タイトル
    draw.text((W // 2, 80), "TradePost Pro", fill=(255, 255, 255), font=font_big, anchor="mm")
    draw.text((W // 2, 140), "FX自動投稿サービス", fill=(200, 200, 255), font=font_mid, anchor="mm")

    # 中央の大きなカード
    card_x, card_y = 80, 200
    card_w, card_h = W - 160, 600
    draw_rounded_rect(draw, (card_x, card_y, card_x + card_w, card_y + card_h),
                      radius=20, fill=(20, 20, 50, 200), outline=(100, 100, 200), width=2)

    # カード内のコンテンツ
    features = [
        ("MT4/MT5対応", "取引データを自動取得"),
        ("5つのSNSに同時投稿", "X, Instagram, Threads, TikTok, LINE"),
        ("美しいテンプレート", "5種類のデザインから選択"),
        ("動画生成対応", "TikTok向けの動画も自動作成"),
        ("完全自動化", "毎朝7時に自動投稿"),
    ]

    for i, (title, desc) in enumerate(features):
        y = card_y + 50 + i * 110
        draw.text((card_x + 40, y), f"0{i + 1}", fill=(100, 200, 255), font=load_font(FONT_BOLD, 32))
        draw.text((card_x + 110, y), title, fill=(255, 255, 255), font=load_font(FONT_BOLD, 28))
        draw.text((card_x + 110, y + 40), desc, fill=(180, 180, 220), font=font_xs)

    # フッター
    draw.text((W // 2, 880), "月額 1,980円 から", fill=(100, 200, 255), font=font_mid, anchor="mm")
    draw.text((W // 2, 940), "詳しくはプロフィールのリンクから", fill=(200, 200, 240), font=font_sm, anchor="mm")

    # ハッシュタグ
    draw.text((W // 2, 1020), "#FX #自動投稿 #TradePostPro #XM",
              fill=(150, 150, 200), font=font_xs, anchor="mm")
    draw.text((W // 2, 1050), "#アフィリエイト #副業 #投資",
              fill=(150, 150, 200), font=font_xs, anchor="mm")

    path = OUTPUT_DIR / "instagram_promo.jpg"
    img.save(str(path), "JPEG", quality=95)
    print(f"Instagram宣伝画像を生成: {path}")
    return path


def generate_line_banner():
    """LINE オープンチャット誘導バナー（1200x400）"""
    W, H = 1200, 400
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # LINE風グリーングラデーション
    for y in range(H):
        r = int(0)
        g = int(180 - 40 * y / H)
        b = int(80 - 20 * y / H)
        draw.line([(0, y), (W, y)], fill=(r, max(0, g), max(0, b)))

    font_big = load_font(FONT_BOLD, 48)
    font_mid = load_font(FONT_BOLD, 32)
    font_sm = load_font(FONT_REGULAR, 24)

    # メインメッセージ
    draw.text((W // 2, 80), "FXトレーダー集まれ！", fill=(255, 255, 255), font=font_big, anchor="mm")
    draw.text((W // 2, 150), "LINEオープンチャットで毎日の取引結果を共有",
              fill=(220, 255, 220), font=font_mid, anchor="mm")

    # 特徴
    items = ["毎日の損益を自動共有", "トレーダー同士の情報交換", "参加無料"]
    x_start = (W - 900) // 2
    for i, item in enumerate(items):
        x = x_start + i * 320
        draw.text((x + 15, 230), "✓", fill=(255, 255, 100), font=load_font(FONT_BOLD, 24))
        draw.text((x + 45, 230), item, fill=(255, 255, 255), font=font_sm)

    # CTA
    cta_x, cta_y = W // 2 - 200, 300
    draw_rounded_rect(draw, (cta_x, cta_y, cta_x + 400, cta_y + 60),
                      radius=30, fill=(255, 255, 255))
    draw.text((W // 2, cta_y + 30), "今すぐ参加する →",
              fill=(0, 150, 60), font=load_font(FONT_BOLD, 28), anchor="mm")

    path = OUTPUT_DIR / "line_banner.jpg"
    img.save(str(path), "JPEG", quality=95)
    print(f"LINEバナーを生成: {path}")
    return path


def generate_pricing_card():
    """料金プラン比較画像（1200x800）"""
    W, H = 1200, 800
    img = Image.new("RGB", (W, H))
    draw = ImageDraw.Draw(img)

    # 背景
    for y in range(H):
        v = int(15 + 10 * y / H)
        draw.line([(0, y), (W, y)], fill=(v, v, v + 15))

    font_title = load_font(FONT_BOLD, 40)
    font_plan = load_font(FONT_BOLD, 32)
    font_price = load_font(FONT_BOLD, 48)
    font_feat = load_font(FONT_REGULAR, 20)

    # タイトル
    draw.text((W // 2, 50), "料金プラン", fill=(255, 255, 255), font=font_title, anchor="mm")

    # プランカード
    plans = [
        {
            "name": "ライト",
            "price": "¥1,980",
            "color": (60, 130, 200),
            "features": ["SNS 2つまで", "基本テンプレート3種", "毎日自動投稿", "メールサポート"],
        },
        {
            "name": "スタンダード",
            "price": "¥2,980",
            "color": (0, 200, 150),
            "features": ["SNS 4つまで", "全テンプレート5種", "毎日自動投稿", "優先サポート"],
        },
        {
            "name": "プレミアム",
            "price": "¥4,980",
            "color": (200, 150, 50),
            "features": ["SNS 5つ全て", "全テンプレート+カスタム", "動画生成対応", "専用サポート"],
        },
    ]

    card_w = 340
    card_h = 580
    gap = 30
    start_x = (W - (card_w * 3 + gap * 2)) // 2

    for i, plan in enumerate(plans):
        x = start_x + i * (card_w + gap)
        y = 110

        # カード背景
        draw_rounded_rect(draw, (x, y, x + card_w, y + card_h),
                          radius=16, fill=(25, 25, 45), outline=plan["color"], width=2)

        # プラン名ヘッダー
        draw_rounded_rect(draw, (x, y, x + card_w, y + 70),
                          radius=16, fill=plan["color"])
        draw.rectangle([(x, y + 50), (x + card_w, y + 70)], fill=plan["color"])
        draw.text((x + card_w // 2, y + 35), plan["name"],
                  fill=(255, 255, 255), font=font_plan, anchor="mm")

        # 価格
        draw.text((x + card_w // 2, y + 130), plan["price"],
                  fill=plan["color"], font=font_price, anchor="mm")
        draw.text((x + card_w // 2, y + 175), "/月（税込）",
                  fill=(150, 150, 170), font=font_feat, anchor="mm")

        # 区切り線
        draw.line([(x + 30, y + 210), (x + card_w - 30, y + 210)],
                  fill=(50, 50, 70), width=1)

        # 機能リスト
        for j, feat in enumerate(plan["features"]):
            fy = y + 240 + j * 50
            draw.text((x + 40, fy), "✓", fill=plan["color"], font=load_font(FONT_BOLD, 22))
            draw.text((x + 70, fy), feat, fill=(200, 200, 220), font=font_feat)

        # CTAボタン
        btn_y = y + card_h - 80
        draw_rounded_rect(draw, (x + 30, btn_y, x + card_w - 30, btn_y + 50),
                          radius=25, fill=plan["color"])
        draw.text((x + card_w // 2, btn_y + 25), "選択する",
                  fill=(255, 255, 255), font=load_font(FONT_BOLD, 22), anchor="mm")

    # 人気バッジ（スタンダード）
    badge_x = start_x + card_w + gap + card_w // 2
    draw_rounded_rect(draw, (badge_x - 50, 95, badge_x + 50, 125),
                      radius=15, fill=(200, 50, 50))
    draw.text((badge_x, 110), "人気No.1",
              fill=(255, 255, 255), font=load_font(FONT_BOLD, 16), anchor="mm")

    # フッター
    draw.text((W // 2, H - 40), "全プラン7日間無料トライアル付き",
              fill=(150, 150, 170), font=load_font(FONT_REGULAR, 22), anchor="mm")

    path = OUTPUT_DIR / "pricing_card.jpg"
    img.save(str(path), "JPEG", quality=95)
    print(f"料金プラン画像を生成: {path}")
    return path


if __name__ == "__main__":
    print("TradePost Pro - マーケティング素材生成\n")
    generate_ogp_image()
    generate_x_promo()
    generate_instagram_promo()
    generate_line_banner()
    generate_pricing_card()
    print(f"\n全ての素材を {OUTPUT_DIR} に生成しました。")
