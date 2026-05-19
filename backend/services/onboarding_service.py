"""
ユーザーオンボーディングウィザードサービス
新規ユーザーの初期設定を段階的にガイドする
"""

import json
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class OnboardingStatus(Enum):
    """オンボーディングステータス"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class StepStatus(Enum):
    """ステップステータス"""
    PENDING = "pending"
    CURRENT = "current"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class OnboardingStep:
    """オンボーディングステップ"""
    id: str
    order: int
    title: str
    description: str
    icon: str
    help_text: str
    is_required: bool = True
    is_skippable: bool = True
    estimated_minutes: int = 2
    validation_rules: dict = field(default_factory=dict)
    fields: list = field(default_factory=list)


@dataclass
class UserOnboardingState:
    """ユーザーのオンボーディング状態"""
    user_id: str
    status: OnboardingStatus = OnboardingStatus.NOT_STARTED
    current_step: int = 0
    completed_steps: list = field(default_factory=list)
    skipped_steps: list = field(default_factory=list)
    step_data: dict = field(default_factory=dict)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    completion_percent: float = 0.0


class OnboardingService:
    """オンボーディングウィザード管理サービス"""

    def __init__(self):
        self.steps = self._define_steps()
        self.user_states: dict = {}  # user_id -> UserOnboardingState

    def _define_steps(self) -> List[OnboardingStep]:
        """オンボーディングステップを定義"""
        return [
            OnboardingStep(
                id="welcome",
                order=1,
                title="ようこそ TradePost Pro へ",
                description="サービスの概要と主な機能をご紹介します",
                icon="👋",
                help_text="TradePost Proは、FXトレード結果を自動でSNSに投稿するサービスです。3つのステップで簡単に始められます。",
                is_required=True,
                is_skippable=False,
                estimated_minutes=1,
                fields=[
                    {"name": "display_name", "type": "text", "label": "表示名", "required": True, "placeholder": "トレーダー名を入力"},
                    {"name": "timezone", "type": "select", "label": "タイムゾーン", "required": True, "default": "Asia/Tokyo",
                     "options": ["Asia/Tokyo", "America/New_York", "Europe/London", "Asia/Shanghai", "Asia/Singapore"]},
                    {"name": "language", "type": "select", "label": "言語", "required": True, "default": "ja",
                     "options": [{"value": "ja", "label": "日本語"}, {"value": "en", "label": "English"}, {"value": "zh", "label": "中文"}]},
                ],
            ),
            OnboardingStep(
                id="mt_connection",
                order=2,
                title="MT4/MT5 を接続",
                description="取引プラットフォームを接続して、トレード結果を自動取得します",
                icon="🔗",
                help_text="MT4またはMT5のログファイルパスを設定してください。VPS上で動作している場合は、ログファイルの場所を指定します。",
                is_required=True,
                is_skippable=True,
                estimated_minutes=5,
                fields=[
                    {"name": "platform", "type": "radio", "label": "プラットフォーム", "required": True,
                     "options": [{"value": "mt4", "label": "MetaTrader 4"}, {"value": "mt5", "label": "MetaTrader 5"}]},
                    {"name": "log_path", "type": "text", "label": "ログファイルパス", "required": True,
                     "placeholder": "C:\\Users\\...\\Terminal\\logs"},
                    {"name": "account_number", "type": "text", "label": "口座番号", "required": False,
                     "placeholder": "12345678"},
                    {"name": "broker", "type": "select", "label": "ブローカー", "required": True, "default": "xm",
                     "options": ["XM Trading", "XM Global", "XM Zero"]},
                ],
                validation_rules={"log_path": {"type": "path", "must_exist": True}},
            ),
            OnboardingStep(
                id="sns_accounts",
                order=3,
                title="SNS アカウントを連携",
                description="投稿先のSNSアカウントを連携します",
                icon="📱",
                help_text="最低1つのSNSアカウントを連携してください。後から追加・変更も可能です。",
                is_required=True,
                is_skippable=True,
                estimated_minutes=5,
                fields=[
                    {"name": "twitter_enabled", "type": "toggle", "label": "X (Twitter)", "default": False,
                     "sub_fields": [
                         {"name": "twitter_api_key", "type": "text", "label": "API Key", "required": True},
                         {"name": "twitter_api_secret", "type": "password", "label": "API Secret", "required": True},
                     ]},
                    {"name": "instagram_enabled", "type": "toggle", "label": "Instagram", "default": False,
                     "sub_fields": [
                         {"name": "instagram_token", "type": "text", "label": "アクセストークン", "required": True},
                     ]},
                    {"name": "tiktok_enabled", "type": "toggle", "label": "TikTok", "default": False},
                    {"name": "threads_enabled", "type": "toggle", "label": "Threads", "default": False},
                    {"name": "line_enabled", "type": "toggle", "label": "LINE Open Chat", "default": False,
                     "sub_fields": [
                         {"name": "line_channel_token", "type": "text", "label": "チャネルトークン", "required": True},
                     ]},
                ],
            ),
            OnboardingStep(
                id="template_selection",
                order=4,
                title="テンプレートを選択",
                description="投稿画像のデザインテンプレートを選びましょう",
                icon="🎨",
                help_text="5種類のテンプレートから選択できます。プレミアムプランでは全テンプレートが利用可能です。",
                is_required=False,
                is_skippable=True,
                estimated_minutes=2,
                fields=[
                    {"name": "template_id", "type": "template_picker", "label": "テンプレート", "required": True, "default": "dark_classic",
                     "options": [
                         {"value": "dark_classic", "label": "ダーククラシック", "preview": "/templates/dark_classic.png", "premium": False},
                         {"value": "neon_glow", "label": "ネオングロー", "preview": "/templates/neon_glow.png", "premium": False},
                         {"value": "minimal_white", "label": "ミニマルホワイト", "preview": "/templates/minimal_white.png", "premium": False},
                         {"value": "gold_luxury", "label": "ゴールドラグジュアリー", "preview": "/templates/gold_luxury.png", "premium": True},
                         {"value": "gradient_wave", "label": "グラデーションウェーブ", "preview": "/templates/gradient_wave.png", "premium": True},
                     ]},
                ],
            ),
            OnboardingStep(
                id="posting_schedule",
                order=5,
                title="投稿スケジュールを設定",
                description="自動投稿のタイミングを設定します",
                icon="⏰",
                help_text="毎日指定した時間に自動投稿されます。最適な投稿時間は朝7時（JST）です。",
                is_required=False,
                is_skippable=True,
                estimated_minutes=2,
                fields=[
                    {"name": "post_time", "type": "time", "label": "投稿時刻", "required": True, "default": "07:00"},
                    {"name": "post_days", "type": "checkbox_group", "label": "投稿曜日", "required": True,
                     "default": ["mon", "tue", "wed", "thu", "fri"],
                     "options": [
                         {"value": "mon", "label": "月"}, {"value": "tue", "label": "火"},
                         {"value": "wed", "label": "水"}, {"value": "thu", "label": "木"},
                         {"value": "fri", "label": "金"}, {"value": "sat", "label": "土"},
                         {"value": "sun", "label": "日"},
                     ]},
                    {"name": "include_weekends", "type": "toggle", "label": "週末も投稿する", "default": False},
                ],
            ),
            OnboardingStep(
                id="notification_setup",
                order=6,
                title="通知設定",
                description="プッシュ通知やメール通知の設定を行います",
                icon="🔔",
                help_text="投稿完了やエラー発生時に通知を受け取れます。",
                is_required=False,
                is_skippable=True,
                estimated_minutes=1,
                fields=[
                    {"name": "push_enabled", "type": "toggle", "label": "プッシュ通知", "default": True},
                    {"name": "email_enabled", "type": "toggle", "label": "メール通知", "default": True},
                    {"name": "notify_post_success", "type": "toggle", "label": "投稿成功時", "default": True},
                    {"name": "notify_post_failed", "type": "toggle", "label": "投稿失敗時", "default": True},
                    {"name": "notify_daily_summary", "type": "toggle", "label": "日次サマリー", "default": True},
                ],
            ),
            OnboardingStep(
                id="complete",
                order=7,
                title="設定完了！",
                description="おめでとうございます！すべての設定が完了しました",
                icon="🎉",
                help_text="ダッシュボードから投稿状況を確認できます。何かお困りのことがあればサポートまでお問い合わせください。",
                is_required=True,
                is_skippable=False,
                estimated_minutes=0,
                fields=[],
            ),
        ]

    def start_onboarding(self, user_id: str) -> dict:
        """オンボーディングを開始"""
        state = UserOnboardingState(
            user_id=user_id,
            status=OnboardingStatus.IN_PROGRESS,
            current_step=0,
            started_at=datetime.now().isoformat(),
        )
        self.user_states[user_id] = state

        return self._get_step_response(user_id)

    def get_current_step(self, user_id: str) -> dict:
        """現在のステップを取得"""
        return self._get_step_response(user_id)

    def submit_step(self, user_id: str, step_id: str, data: dict) -> dict:
        """ステップのデータを送信"""
        state = self.user_states.get(user_id)
        if not state:
            return {"success": False, "error": "オンボーディングが開始されていません"}

        current_step = self.steps[state.current_step]
        if current_step.id != step_id:
            return {"success": False, "error": "ステップIDが一致しません"}

        # バリデーション
        validation = self._validate_step_data(current_step, data)
        if not validation["valid"]:
            return {"success": False, "errors": validation["errors"]}

        # データ保存
        state.step_data[step_id] = data
        state.completed_steps.append(step_id)

        # 次のステップへ
        if state.current_step < len(self.steps) - 1:
            state.current_step += 1
            state.completion_percent = (len(state.completed_steps) / len(self.steps)) * 100
        else:
            state.status = OnboardingStatus.COMPLETED
            state.completed_at = datetime.now().isoformat()
            state.completion_percent = 100.0

        return {
            "success": True,
            "next": self._get_step_response(user_id),
        }

    def skip_step(self, user_id: str, step_id: str) -> dict:
        """ステップをスキップ"""
        state = self.user_states.get(user_id)
        if not state:
            return {"success": False, "error": "オンボーディングが開始されていません"}

        current_step = self.steps[state.current_step]
        if not current_step.is_skippable:
            return {"success": False, "error": "このステップはスキップできません"}

        state.skipped_steps.append(step_id)

        if state.current_step < len(self.steps) - 1:
            state.current_step += 1
            state.completion_percent = ((len(state.completed_steps) + len(state.skipped_steps)) / len(self.steps)) * 100

        return {
            "success": True,
            "next": self._get_step_response(user_id),
        }

    def get_progress(self, user_id: str) -> dict:
        """オンボーディング進捗を取得"""
        state = self.user_states.get(user_id)
        if not state:
            return {
                "status": OnboardingStatus.NOT_STARTED.value,
                "completion_percent": 0,
                "steps": [],
            }

        steps_progress = []
        for i, step in enumerate(self.steps):
            if step.id in state.completed_steps:
                status = StepStatus.COMPLETED
            elif step.id in state.skipped_steps:
                status = StepStatus.SKIPPED
            elif i == state.current_step:
                status = StepStatus.CURRENT
            else:
                status = StepStatus.PENDING

            steps_progress.append({
                "id": step.id,
                "order": step.order,
                "title": step.title,
                "icon": step.icon,
                "status": status.value,
                "is_required": step.is_required,
            })

        return {
            "status": state.status.value,
            "current_step": state.current_step,
            "completion_percent": round(state.completion_percent, 1),
            "completed_steps": len(state.completed_steps),
            "total_steps": len(self.steps),
            "steps": steps_progress,
            "started_at": state.started_at,
            "completed_at": state.completed_at,
        }

    def get_collected_data(self, user_id: str) -> dict:
        """収集されたデータを取得"""
        state = self.user_states.get(user_id)
        if not state:
            return {}
        return state.step_data

    def reset_onboarding(self, user_id: str) -> bool:
        """オンボーディングをリセット"""
        if user_id in self.user_states:
            del self.user_states[user_id]
            return True
        return False

    def _get_step_response(self, user_id: str) -> dict:
        """ステップレスポンスを構築"""
        state = self.user_states.get(user_id)
        if not state or state.status == OnboardingStatus.COMPLETED:
            return {
                "status": "completed",
                "message": "オンボーディングは完了しています",
            }

        step = self.steps[state.current_step]
        return {
            "step": {
                "id": step.id,
                "order": step.order,
                "title": step.title,
                "description": step.description,
                "icon": step.icon,
                "help_text": step.help_text,
                "is_required": step.is_required,
                "is_skippable": step.is_skippable,
                "estimated_minutes": step.estimated_minutes,
                "fields": step.fields,
            },
            "progress": {
                "current": state.current_step + 1,
                "total": len(self.steps),
                "percent": round(state.completion_percent, 1),
            },
        }

    def _validate_step_data(self, step: OnboardingStep, data: dict) -> dict:
        """ステップデータのバリデーション"""
        errors = []
        for field_def in step.fields:
            name = field_def["name"]
            required = field_def.get("required", False)

            if required and (name not in data or not data[name]):
                errors.append({
                    "field": name,
                    "message": f"{field_def['label']}は必須です",
                })

        return {"valid": len(errors) == 0, "errors": errors}

    def generate_onboarding_component(self) -> str:
        """フロントエンド用のオンボーディングコンポーネントを生成"""
        return """
<!-- Onboarding Wizard Component -->
<div id="onboarding-wizard" class="fixed inset-0 z-50 bg-gray-900/80 flex items-center justify-center" x-data="onboardingWizard()">
  <div class="bg-white rounded-2xl shadow-2xl max-w-2xl w-full mx-4 overflow-hidden">
    <!-- Progress Bar -->
    <div class="bg-gray-100 px-6 py-3">
      <div class="flex items-center justify-between mb-2">
        <span class="text-sm text-gray-600" x-text="`ステップ ${currentStep + 1} / ${totalSteps}`"></span>
        <span class="text-sm text-gray-600" x-text="`${progressPercent}%`"></span>
      </div>
      <div class="w-full bg-gray-200 rounded-full h-2">
        <div class="bg-indigo-600 h-2 rounded-full transition-all duration-500" :style="`width: ${progressPercent}%`"></div>
      </div>
    </div>

    <!-- Step Content -->
    <div class="p-8">
      <div class="text-center mb-6">
        <span class="text-4xl" x-text="step.icon"></span>
        <h2 class="text-2xl font-bold mt-3" x-text="step.title"></h2>
        <p class="text-gray-600 mt-2" x-text="step.description"></p>
      </div>

      <!-- Dynamic Fields -->
      <div class="space-y-4" x-html="renderFields()"></div>

      <!-- Help Text -->
      <div class="mt-4 p-3 bg-blue-50 rounded-lg text-sm text-blue-700" x-show="step.help_text">
        <span x-text="step.help_text"></span>
      </div>
    </div>

    <!-- Navigation -->
    <div class="px-8 py-4 bg-gray-50 flex justify-between">
      <button @click="skipStep()" x-show="step.is_skippable"
        class="px-4 py-2 text-gray-600 hover:text-gray-800">スキップ</button>
      <div class="flex gap-3">
        <button @click="prevStep()" x-show="currentStep > 0"
          class="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-100">戻る</button>
        <button @click="nextStep()"
          class="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700">
          <span x-text="currentStep === totalSteps - 1 ? '完了' : '次へ'"></span>
        </button>
      </div>
    </div>
  </div>
</div>
"""


# テスト実行
if __name__ == "__main__":
    service = OnboardingService()

    print("=== オンボーディングステップ一覧 ===")
    for step in service.steps:
        req = "必須" if step.is_required else "任意"
        skip = "スキップ可" if step.is_skippable else "スキップ不可"
        print(f"  {step.icon} ステップ{step.order}: {step.title} ({req}, {skip}, 約{step.estimated_minutes}分)")

    print("\n=== オンボーディング開始 ===")
    result = service.start_onboarding("user_001")
    print(f"  現在のステップ: {result['step']['title']}")
    print(f"  進捗: {result['progress']['current']}/{result['progress']['total']}")

    print("\n=== ステップ1送信 ===")
    result = service.submit_step("user_001", "welcome", {
        "display_name": "FXトレーダー太郎",
        "timezone": "Asia/Tokyo",
        "language": "ja",
    })
    print(f"  成功: {result['success']}")
    print(f"  次のステップ: {result['next']['step']['title']}")

    print("\n=== ステップ2送信 ===")
    result = service.submit_step("user_001", "mt_connection", {
        "platform": "mt4",
        "log_path": "C:\\Users\\Trader\\AppData\\Roaming\\MetaTrader 4\\logs",
        "account_number": "12345678",
        "broker": "XM Trading",
    })
    print(f"  成功: {result['success']}")
    print(f"  次のステップ: {result['next']['step']['title']}")

    print("\n=== ステップ3スキップ ===")
    result = service.skip_step("user_001", "sns_accounts")
    print(f"  成功: {result['success']}")
    print(f"  次のステップ: {result['next']['step']['title']}")

    print("\n=== 進捗確認 ===")
    progress = service.get_progress("user_001")
    print(f"  ステータス: {progress['status']}")
    print(f"  完了率: {progress['completion_percent']}%")
    print(f"  完了ステップ: {progress['completed_steps']}/{progress['total_steps']}")
    for step in progress["steps"]:
        print(f"    {step['icon']} {step['title']}: {step['status']}")

    print("\n=== 収集データ ===")
    data = service.get_collected_data("user_001")
    for step_id, step_data in data.items():
        print(f"  {step_id}: {json.dumps(step_data, ensure_ascii=False)}")

    print("\n✓ オンボーディングウィザードサービス テスト完了")
