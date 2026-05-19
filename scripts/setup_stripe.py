"""
Stripe商品・料金プラン自動セットアップスクリプト
================================================
Stripeに3つの月額サブスクリプション商品を作成し、
Price IDを.envファイルに書き込みます。

使い方:
  1. .envにSTRIPE_SECRET_KEYを設定
  2. python scripts/setup_stripe.py を実行
"""

import os
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

def main():
    secret_key = os.getenv("STRIPE_SECRET_KEY", "")
    if not secret_key or secret_key.startswith("sk_test_xxxxx"):
        print("エラー: .envにSTRIPE_SECRET_KEYを設定してください")
        sys.exit(1)

    try:
        import stripe
    except ImportError:
        print("stripeパッケージをインストール中...")
        os.system(f"{sys.executable} -m pip install stripe")
        import stripe

    stripe.api_key = secret_key

    plans = [
        {
            "name": "TradePost Pro ライト",
            "description": "SNS 2つまで、基本テンプレート3種、毎日自動投稿",
            "price": 1980,
            "plan_key": "STRIPE_PRICE_LIGHT",
        },
        {
            "name": "TradePost Pro スタンダード",
            "description": "SNS 4つまで、全テンプレート5種、毎日自動投稿",
            "price": 2980,
            "plan_key": "STRIPE_PRICE_STANDARD",
        },
        {
            "name": "TradePost Pro プレミアム",
            "description": "SNS 5つ全て、カスタムテンプレート、動画自動生成",
            "price": 4980,
            "plan_key": "STRIPE_PRICE_PREMIUM",
        },
    ]

    print("=" * 50)
    print("Stripe商品セットアップ開始")
    print("=" * 50)

    env_lines = {}

    for plan in plans:
        print(f"\n▶ {plan['name']} (¥{plan['price']}/月) を作成中...")

        # 既存のProductを検索
        existing = stripe.Product.search(query=f'name:"{plan["name"]}"')
        if existing.data:
            product = existing.data[0]
            print(f"  既存のProduct発見: {product.id}")
        else:
            product = stripe.Product.create(
                name=plan["name"],
                description=plan["description"],
                metadata={"app": "xm_sns_auto_poster"},
            )
            print(f"  Product作成: {product.id}")

        # 既存のPriceを検索
        prices = stripe.Price.list(product=product.id, active=True)
        matching_price = None
        for p in prices.data:
            if p.unit_amount == plan["price"] and p.currency == "jpy" and p.recurring:
                matching_price = p
                break

        if matching_price:
            price = matching_price
            print(f"  既存のPrice発見: {price.id}")
        else:
            price = stripe.Price.create(
                product=product.id,
                unit_amount=plan["price"],
                currency="jpy",
                recurring={"interval": "month"},
            )
            print(f"  Price作成: {price.id}")

        env_lines[plan["plan_key"]] = price.id
        print(f"  ✓ {plan['plan_key']}={price.id}")

    # .envファイルに書き込み
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")

    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            content = f.read()

        for key, value in env_lines.items():
            if key in content:
                # 既存の行を更新
                import re
                content = re.sub(rf'^{key}=.*$', f'{key}={value}', content, flags=re.MULTILINE)
            else:
                content += f"\n{key}={value}"

        with open(env_path, "w") as f:
            f.write(content)
        print(f"\n✓ .envファイルを更新しました: {env_path}")
    else:
        print(f"\n⚠ .envファイルが見つかりません: {env_path}")
        print("以下を.envに追加してください:")
        for key, value in env_lines.items():
            print(f"  {key}={value}")

    print("\n" + "=" * 50)
    print("セットアップ完了！")
    print("=" * 50)


if __name__ == "__main__":
    main()
