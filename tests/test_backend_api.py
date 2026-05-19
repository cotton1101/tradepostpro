"""
TradePost Pro - バックエンドAPI ユニットテスト
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPlanService:
    """プランサービスのテスト"""

    def test_plan_config_light(self):
        """ライトプランの設定テスト"""
        from backend.services.plan_service import PlanService

        config = PlanService.get_plan_config("light")
        assert config is not None
        assert config.max_sns_count == 2
        assert config.video_generation is False

    def test_plan_config_standard(self):
        """スタンダードプランの設定テスト"""
        from backend.services.plan_service import PlanService

        config = PlanService.get_plan_config("standard")
        assert config is not None
        assert config.max_sns_count == 4
        assert config.video_generation is False

    def test_plan_config_premium(self):
        """プレミアムプランの設定テスト"""
        from backend.services.plan_service import PlanService

        config = PlanService.get_plan_config("premium")
        assert config is not None
        assert config.max_sns_count == 5
        assert config.video_generation is True

    def test_can_use_platform_within_limit(self):
        """プラットフォーム数が制限内のテスト"""
        from backend.services.plan_service import PlanService

        result = PlanService.can_use_platform("light", 1)
        assert result is True

    def test_can_use_platform_exceeds_limit(self):
        """プラットフォーム数が制限超過のテスト"""
        from backend.services.plan_service import PlanService

        result = PlanService.can_use_platform("light", 3)
        assert result is False

    def test_can_generate_video_premium(self):
        """プレミアムプランの動画許可テスト"""
        from backend.services.plan_service import PlanService

        result = PlanService.can_generate_video("premium")
        assert result is True

    def test_can_generate_video_light(self):
        """ライトプランの動画拒否テスト"""
        from backend.services.plan_service import PlanService

        result = PlanService.can_generate_video("light")
        assert result is False

    def test_can_use_template_basic(self):
        """基本テンプレートのアクセステスト"""
        from backend.services.plan_service import PlanService

        result = PlanService.can_use_template("light", "basic")
        assert result is True

    def test_can_use_template_premium_only(self):
        """プレミアムテンプレートのアクセス制限テスト"""
        from backend.services.plan_service import PlanService

        result = PlanService.can_use_template("light", "premium")
        assert result is False

    def test_get_all_plans(self):
        """全プラン一覧の取得テスト"""
        from backend.services.plan_service import PlanService

        plans = PlanService.get_all_plans()
        assert len(plans) >= 3
        plan_ids = [p["plan_id"] for p in plans]
        assert "light" in plan_ids
        assert "standard" in plan_ids
        assert "premium" in plan_ids

    def test_get_available_platforms(self):
        """利用可能プラットフォーム数の取得テスト"""
        from backend.services.plan_service import PlanService

        assert PlanService.get_available_platforms("light") == 2
        assert PlanService.get_available_platforms("standard") == 4
        assert PlanService.get_available_platforms("premium") == 5


class TestSchedulerService:
    """スケジューラーサービスのテスト"""

    def test_scheduler_init(self):
        """スケジューラーの初期化テスト"""
        from backend.services.scheduler_service import ScheduleEngine

        engine = ScheduleEngine()
        assert engine is not None

    def test_job_status_enum(self):
        """ジョブステータスの列挙型テスト"""
        from backend.services.scheduler_service import JobStatus

        assert JobStatus.QUEUED is not None
        assert JobStatus.RUNNING is not None
        assert JobStatus.SUCCESS is not None
        assert JobStatus.FAILED is not None
