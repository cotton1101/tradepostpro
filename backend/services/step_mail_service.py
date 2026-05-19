"""
メールマーケティング（ステップメール）サービス
登録後の自動フォローアップメール配信を管理する
"""

import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field
from enum import Enum


class MailTrigger(Enum):
    """メール配信トリガー"""
    REGISTRATION = "registration"
    TRIAL_START = "trial_start"
    TRIAL_ENDING = "trial_ending"
    FIRST_POST = "first_post"
    INACTIVE = "inactive"
    PLAN_UPGRADE = "plan_upgrade"
    PLAN_DOWNGRADE = "plan_downgrade"
    MILESTONE = "milestone"


class MailStatus(Enum):
    """メール配信ステータス"""
    SCHEDULED = "scheduled"
    SENT = "sent"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


@dataclass
class StepMailTemplate:
    """ステップメールテンプレート"""
    id: str
    name: str
    subject: str
    body_html: str
    body_text: str
    trigger: MailTrigger
    delay_days: int
    delay_hours: int = 0
    is_active: bool = True
    ab_variant: str = "A"


@dataclass
class MailCampaign:
    """メールキャンペーン"""
    id: str
    name: str
    description: str
    templates: list
    is_active: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class MailLog:
    """メール配信ログ"""
    user_id: str
    template_id: str
    status: MailStatus
    sent_at: str = ""
    opened_at: Optional[str] = None
    clicked_at: Optional[str] = None


class StepMailService:
    """ステップメール管理サービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.smtp_host = self.config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.from_email = self.config.get("from_email", "noreply@tradepost-pro.com")
        self.from_name = self.config.get("from_name", "TradePost Pro")

        # デフォルトのステップメールシーケンス
        self.default_sequences = self._create_default_sequences()
        self.mail_logs: list = []

    def _create_default_sequences(self) -> dict:
        """デフォルトのステップメールシーケンスを作成"""
        return {
            "welcome_sequence": MailCampaign(
                id="welcome_seq",
                name="ウェルカムシーケンス",
                description="新規登録ユーザー向けのオンボーディングメール",
                templates=[
                    StepMailTemplate(
                        id="welcome_01",
                        name="ウェルカムメール",
                        subject="TradePost Proへようこそ！🎉 設定を始めましょう",
                        body_html=self._get_welcome_template(),
                        body_text="TradePost Proへのご登録ありがとうございます。",
                        trigger=MailTrigger.REGISTRATION,
                        delay_days=0,
                        delay_hours=0,
                    ),
                    StepMailTemplate(
                        id="welcome_02",
                        name="MT4/MT5接続ガイド",
                        subject="【ステップ1】MT4/MT5を接続して自動投稿を始めよう",
                        body_html=self._get_mt_setup_template(),
                        body_text="MT4/MT5の接続方法をご案内します。",
                        trigger=MailTrigger.REGISTRATION,
                        delay_days=1,
                    ),
                    StepMailTemplate(
                        id="welcome_03",
                        name="SNS連携ガイド",
                        subject="【ステップ2】SNSアカウントを連携しましょう",
                        body_html=self._get_sns_setup_template(),
                        body_text="SNSアカウントの連携方法をご案内します。",
                        trigger=MailTrigger.REGISTRATION,
                        delay_days=3,
                    ),
                    StepMailTemplate(
                        id="welcome_04",
                        name="テンプレート紹介",
                        subject="【ステップ3】お好みのテンプレートを選びましょう 🎨",
                        body_html=self._get_template_intro(),
                        body_text="投稿テンプレートの選び方をご紹介します。",
                        trigger=MailTrigger.REGISTRATION,
                        delay_days=5,
                    ),
                    StepMailTemplate(
                        id="welcome_05",
                        name="活用Tips",
                        subject="TradePost Proを最大限活用する5つのコツ 💡",
                        body_html=self._get_tips_template(),
                        body_text="TradePost Proの活用Tipsをお届けします。",
                        trigger=MailTrigger.REGISTRATION,
                        delay_days=7,
                    ),
                ],
            ),
            "trial_sequence": MailCampaign(
                id="trial_seq",
                name="トライアルシーケンス",
                description="無料トライアル期間中のフォローアップ",
                templates=[
                    StepMailTemplate(
                        id="trial_01",
                        name="トライアル開始",
                        subject="無料トライアルが始まりました！7日間で全機能をお試しください",
                        body_html=self._get_trial_start_template(),
                        body_text="無料トライアルが開始されました。",
                        trigger=MailTrigger.TRIAL_START,
                        delay_days=0,
                    ),
                    StepMailTemplate(
                        id="trial_02",
                        name="トライアル中間",
                        subject="トライアル残り3日！プレミアム機能は試しましたか？",
                        body_html=self._get_trial_mid_template(),
                        body_text="トライアル期間の残りが3日になりました。",
                        trigger=MailTrigger.TRIAL_START,
                        delay_days=4,
                    ),
                    StepMailTemplate(
                        id="trial_03",
                        name="トライアル終了前日",
                        subject="⏰ 明日トライアルが終了します｜特別割引のご案内",
                        body_html=self._get_trial_ending_template(),
                        body_text="トライアル期間が明日終了します。",
                        trigger=MailTrigger.TRIAL_ENDING,
                        delay_days=6,
                    ),
                ],
            ),
            "reactivation_sequence": MailCampaign(
                id="reactivation_seq",
                name="リアクティベーションシーケンス",
                description="非アクティブユーザーの再活性化",
                templates=[
                    StepMailTemplate(
                        id="react_01",
                        name="最近見かけません",
                        subject="お元気ですか？TradePost Proの新機能をご紹介",
                        body_html=self._get_reactivation_template(),
                        body_text="最近TradePost Proをご利用いただいていないようです。",
                        trigger=MailTrigger.INACTIVE,
                        delay_days=7,
                    ),
                    StepMailTemplate(
                        id="react_02",
                        name="特別オファー",
                        subject="【限定】復帰特別割引 30%OFF クーポンをプレゼント 🎁",
                        body_html=self._get_special_offer_template(),
                        body_text="特別割引クーポンをお届けします。",
                        trigger=MailTrigger.INACTIVE,
                        delay_days=14,
                    ),
                ],
            ),
            "milestone_sequence": MailCampaign(
                id="milestone_seq",
                name="マイルストーンシーケンス",
                description="達成記念メール",
                templates=[
                    StepMailTemplate(
                        id="mile_01",
                        name="初投稿おめでとう",
                        subject="🎉 初めてのSNS自動投稿が完了しました！",
                        body_html=self._get_first_post_template(),
                        body_text="初めてのSNS自動投稿が完了しました。",
                        trigger=MailTrigger.FIRST_POST,
                        delay_days=0,
                    ),
                ],
            ),
        }

    def get_pending_mails(self, user_id: str, trigger: MailTrigger, days_since_trigger: int) -> list:
        """配信すべきメールを取得"""
        pending = []
        for campaign in self.default_sequences.values():
            if not campaign.is_active:
                continue
            for template in campaign.templates:
                if not template.is_active:
                    continue
                if template.trigger != trigger:
                    continue
                if template.delay_days <= days_since_trigger:
                    already_sent = any(
                        log.user_id == user_id and log.template_id == template.id
                        for log in self.mail_logs
                    )
                    if not already_sent:
                        pending.append(template)
        return pending

    def send_mail(self, user_id: str, user_email: str, template: StepMailTemplate) -> dict:
        """メールを送信"""
        # トラッキングピクセルを挿入
        tracking_pixel = f'<img src="https://api.tradepost-pro.com/track/open/{user_id}/{template.id}" width="1" height="1" />'
        body_with_tracking = template.body_html + tracking_pixel

        # 実際のSMTP送信（本番環境用）
        log = MailLog(
            user_id=user_id,
            template_id=template.id,
            status=MailStatus.SENT,
            sent_at=datetime.now().isoformat(),
        )
        self.mail_logs.append(log)

        return {
            "success": True,
            "template_id": template.id,
            "user_id": user_id,
            "email": user_email,
            "subject": template.subject,
            "sent_at": log.sent_at,
        }

    def track_open(self, user_id: str, template_id: str) -> bool:
        """メール開封をトラッキング"""
        for log in self.mail_logs:
            if log.user_id == user_id and log.template_id == template_id:
                log.status = MailStatus.OPENED
                log.opened_at = datetime.now().isoformat()
                return True
        return False

    def track_click(self, user_id: str, template_id: str) -> bool:
        """リンククリックをトラッキング"""
        for log in self.mail_logs:
            if log.user_id == user_id and log.template_id == template_id:
                log.status = MailStatus.CLICKED
                log.clicked_at = datetime.now().isoformat()
                return True
        return False

    def get_campaign_stats(self, campaign_id: str) -> dict:
        """キャンペーンの統計情報を取得"""
        campaign = self.default_sequences.get(campaign_id)
        if not campaign:
            return {}

        template_ids = [t.id for t in campaign.templates]
        relevant_logs = [l for l in self.mail_logs if l.template_id in template_ids]

        total_sent = len(relevant_logs)
        total_opened = sum(1 for l in relevant_logs if l.status in (MailStatus.OPENED, MailStatus.CLICKED))
        total_clicked = sum(1 for l in relevant_logs if l.status == MailStatus.CLICKED)

        return {
            "campaign_id": campaign_id,
            "campaign_name": campaign.name,
            "total_sent": total_sent,
            "total_opened": total_opened,
            "total_clicked": total_clicked,
            "open_rate": (total_opened / total_sent * 100) if total_sent > 0 else 0,
            "click_rate": (total_clicked / total_sent * 100) if total_sent > 0 else 0,
        }

    def unsubscribe(self, user_id: str) -> bool:
        """メール配信を停止"""
        for log in self.mail_logs:
            if log.user_id == user_id:
                log.status = MailStatus.UNSUBSCRIBED
        return True

    # HTMLテンプレート
    def _get_welcome_template(self) -> str:
        return """
<div style="max-width:600px;margin:0 auto;font-family:'Helvetica Neue',Arial,sans-serif;">
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);padding:40px;text-align:center;border-radius:12px 12px 0 0;">
    <h1 style="color:#fff;margin:0;font-size:28px;">TradePost Proへようこそ！🎉</h1>
  </div>
  <div style="padding:30px;background:#fff;border:1px solid #e5e7eb;">
    <p style="font-size:16px;color:#374151;">ご登録ありがとうございます。</p>
    <p style="font-size:16px;color:#374151;">TradePost Proは、あなたのFXトレード結果を自動でSNSに投稿するサービスです。</p>
    <h3 style="color:#4f46e5;">3ステップで始められます：</h3>
    <ol style="color:#374151;font-size:15px;">
      <li>MT4/MT5を接続する</li>
      <li>SNSアカウントを連携する</li>
      <li>テンプレートを選んで投稿開始！</li>
    </ol>
    <div style="text-align:center;margin:30px 0;">
      <a href="https://app.tradepost-pro.com/dashboard" style="background:#4f46e5;color:#fff;padding:14px 32px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;">ダッシュボードを開く</a>
    </div>
  </div>
</div>"""

    def _get_mt_setup_template(self) -> str:
        return "<div>MT4/MT5接続ガイドのHTMLテンプレート</div>"

    def _get_sns_setup_template(self) -> str:
        return "<div>SNS連携ガイドのHTMLテンプレート</div>"

    def _get_template_intro(self) -> str:
        return "<div>テンプレート紹介のHTMLテンプレート</div>"

    def _get_tips_template(self) -> str:
        return "<div>活用TipsのHTMLテンプレート</div>"

    def _get_trial_start_template(self) -> str:
        return "<div>トライアル開始のHTMLテンプレート</div>"

    def _get_trial_mid_template(self) -> str:
        return "<div>トライアル中間のHTMLテンプレート</div>"

    def _get_trial_ending_template(self) -> str:
        return "<div>トライアル終了前日のHTMLテンプレート</div>"

    def _get_reactivation_template(self) -> str:
        return "<div>リアクティベーションのHTMLテンプレート</div>"

    def _get_special_offer_template(self) -> str:
        return "<div>特別オファーのHTMLテンプレート</div>"

    def _get_first_post_template(self) -> str:
        return "<div>初投稿おめでとうのHTMLテンプレート</div>"


# テスト実行
if __name__ == "__main__":
    service = StepMailService()

    print("=== ステップメールシーケンス一覧 ===")
    for seq_id, campaign in service.default_sequences.items():
        print(f"\n  【{campaign.name}】({len(campaign.templates)}通)")
        for t in campaign.templates:
            print(f"    Day {t.delay_days}: {t.subject}")

    print("\n=== 配信テスト ===")
    # 登録直後のメール取得
    pending = service.get_pending_mails("user_001", MailTrigger.REGISTRATION, 0)
    print(f"  登録直後の配信対象: {len(pending)}通")
    for t in pending:
        result = service.send_mail("user_001", "test@example.com", t)
        print(f"    送信: {result['subject']}")

    # 3日後のメール取得
    pending = service.get_pending_mails("user_001", MailTrigger.REGISTRATION, 3)
    print(f"  3日後の配信対象: {len(pending)}通")

    # 開封トラッキング
    service.track_open("user_001", "welcome_01")
    print("\n=== キャンペーン統計 ===")
    stats = service.get_campaign_stats("welcome_sequence")
    print(f"  キャンペーン: {stats['campaign_name']}")
    print(f"  送信数: {stats['total_sent']}")
    print(f"  開封数: {stats['total_opened']}")
    print(f"  開封率: {stats['open_rate']:.1f}%")

    print("\n✓ ステップメールサービス テスト完了")
