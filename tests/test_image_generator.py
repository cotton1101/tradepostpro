"""
TradePost Pro - 画像生成モジュール ユニットテスト
"""

import os
import sys
import pytest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestImageGenerator:
    """image_generator.py のテスト"""

    def test_generate_image_profit(self, trade_data_profit, output_dir):
        """利益時の画像生成テスト"""
        from modules.image_generator import ImageGenerator

        gen = ImageGenerator()
        output_path = Path(output_dir) / "test_profit.jpg"
        result = gen.generate(trade_data_profit, output_path=output_path)
        assert result is not None
        assert os.path.exists(str(result))
        assert os.path.getsize(str(result)) > 0

    def test_generate_image_loss(self, trade_data_loss, output_dir):
        """損失時の画像生成テスト"""
        from modules.image_generator import ImageGenerator

        gen = ImageGenerator()
        output_path = Path(output_dir) / "test_loss.jpg"
        result = gen.generate(trade_data_loss, output_path=output_path)
        assert result is not None
        assert os.path.exists(str(result))
        assert os.path.getsize(str(result)) > 0

    def test_generate_image_zero(self, trade_data_zero, output_dir):
        """取引なし時の画像生成テスト"""
        from modules.image_generator import ImageGenerator

        gen = ImageGenerator()
        output_path = Path(output_dir) / "test_zero.jpg"
        result = gen.generate(trade_data_zero, output_path=output_path)
        assert result is not None
        assert os.path.exists(str(result))


class TestImageTemplates:
    """image_templates.py のテスト"""

    TEMPLATE_NAMES = [
        "dark_classic",
        "neon_glow",
        "minimal_white",
        "gold_luxury",
        "gradient_wave",
    ]

    def test_all_templates_generate(self, trade_data_profit, output_dir):
        """全テンプレートが正常に画像を生成できるか"""
        from modules.image_templates import render_template

        for name in self.TEMPLATE_NAMES:
            output_path = os.path.join(output_dir, f"test_{name}.jpg")
            result = render_template(name, trade_data_profit, output_path=output_path)
            assert result is not None, f"テンプレート '{name}' の生成に失敗"
            assert os.path.exists(result), f"テンプレート '{name}' のファイルが存在しない"
            assert os.path.getsize(result) > 1000, f"テンプレート '{name}' のファイルサイズが小さすぎる"

    def test_invalid_template_name(self, trade_data_profit, output_dir):
        """存在しないテンプレート名でのエラーハンドリング"""
        from modules.image_templates import render_template

        with pytest.raises(ValueError):
            render_template("nonexistent_template", trade_data_profit)

    def test_template_list(self):
        """利用可能テンプレート一覧の取得"""
        from modules.image_templates import get_available_templates

        templates = get_available_templates(plan="premium")
        assert len(templates) >= 5
        template_ids = [t["id"] for t in templates]
        for name in self.TEMPLATE_NAMES:
            assert name in template_ids, f"テンプレート '{name}' が一覧にない"

    def test_template_plan_restriction(self):
        """プランによるテンプレート制限テスト"""
        from modules.image_templates import get_available_templates

        # ライトプラン: 基本3種のみ利用可能
        light_templates = get_available_templates(plan="light")
        available_light = [t for t in light_templates if t["available"]]
        assert len(available_light) == 3

        # プレミアムプラン: 全5種利用可能
        premium_templates = get_available_templates(plan="premium")
        available_premium = [t for t in premium_templates if t["available"]]
        assert len(available_premium) == 5

    def test_profit_color_green(self, trade_data_profit, output_dir):
        """利益時の画像生成（ファイル生成確認）"""
        from modules.image_templates import render_template

        output_path = os.path.join(output_dir, "test_profit_dark.jpg")
        result = render_template("dark_classic", trade_data_profit, output_path=output_path)
        assert os.path.exists(result)

    def test_loss_color_red(self, trade_data_loss, output_dir):
        """損失時の画像生成（ファイル生成確認）"""
        from modules.image_templates import render_template

        output_path = os.path.join(output_dir, "test_loss_dark.jpg")
        result = render_template("dark_classic", trade_data_loss, output_path=output_path)
        assert os.path.exists(result)
