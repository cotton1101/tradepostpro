"""
TradePost Pro - メール通知システム
PHP Mail Proxy（Xserver）を優先し、SMTP をフォールバックとして使用。
"""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

# メール設定
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "info@sns-tool.online")
PHP_MAIL_URL = os.getenv("PHP_MAIL_URL", "https://sns-tool.online/tradepostpro/server/send_mail.php")
PHP_MAIL_KEY = os.getenv("PHP_MAIL_KEY", "")
SITE_URL = os.getenv("FRONTEND_URL", "https://sns-tool.online/tradepostpro")

EMAIL_CONFIG = {
    "smtp_host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "smtp_port": int(os.getenv("SMTP_PORT", "587")),
    "smtp_user": os.getenv("SMTP_USER", ""),
    "smtp_password": os.getenv("SMTP_PASSWORD", ""),
    "from_name": "TradePost Pro",
    "from_email": os.getenv("SMTP_FROM", "info@sns-tool.online"),
    "reply_to": os.getenv("SMTP_REPLY_TO", "info@sns-tool.online"),
}


class EmailTemplate:
    """メールテンプレート"""

    @staticmethod
    def _base_html(content: str, title: str = "") -> str:
        return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
</head>
<body style="margin:0; padding:0; background-color:#0d1117; font-family:'Helvetica Neue',Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#0d1117;">
        <tr>
            <td align="center" style="padding:40px 20px;">
                <table width="600" cellpadding="0" cellspacing="0" style="background-color:#161b22; border-radius:12px; overflow:hidden;">
                    <tr>
                        <td style="background:linear-gradient(135deg,#00d4aa,#0984e3); padding:30px; text-align:center;">
                            <h1 style="color:#ffffff; margin:0; font-size:24px;">TradePost Pro</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:30px; color:#c9d1d9;">
                            {content}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:20px 30px; background-color:#0d1117; text-align:center; border-top:1px solid #30363d;">
                            <p style="color:#8b949e; font-size:12px; margin:0;">
                                &copy; 2026 TradePost Pro. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    # ------------------------------------------------------------------
    # ユーザー向けテンプレート
    # ------------------------------------------------------------------

    @classmethod
    def post_success(cls, data: Dict) -> Dict:
        platforms = ", ".join(data.get("platforms", []))
        content = f"""
            <h2 style="color:#00d4aa; margin-top:0;">投稿が完了しました</h2>
            <p>本日の取引結果が正常に投稿されました。</p>
            <table width="100%" cellpadding="10" style="background-color:#0d1117; border-radius:8px; margin:20px 0;">
                <tr><td style="color:#8b949e;">日付</td><td style="color:#ffffff; text-align:right;">{data.get('date', '')}</td></tr>
                <tr><td style="color:#8b949e;">損益</td><td style="color:{'#00d4aa' if data.get('profit', 0) >= 0 else '#ff4757'}; text-align:right; font-size:18px; font-weight:bold;">{'+' if data.get('profit', 0) >= 0 else ''}{data.get('profit', 0):,.0f}円</td></tr>
                <tr><td style="color:#8b949e;">投稿先</td><td style="color:#ffffff; text-align:right;">{platforms}</td></tr>
            </table>
        """
        return {"subject": f"投稿完了: {data.get('date', '')} の取引結果", "html": cls._base_html(content, "投稿完了通知")}

    @classmethod
    def post_failure(cls, data: Dict) -> Dict:
        error_list = ""
        for err in data.get("errors", []):
            error_list += f'<li style="margin:5px 0;">{err["platform"]}: {err["message"]}</li>'
        content = f"""
            <h2 style="color:#ff4757; margin-top:0;">投稿に失敗しました</h2>
            <p>以下のプラットフォームへの投稿でエラーが発生しました。</p>
            <div style="background-color:#2d0f0f; border:1px solid #5c1a1a; border-radius:8px; padding:15px; margin:20px 0;">
                <ul style="color:#ff6b6b; margin:0; padding-left:20px;">{error_list}</ul>
            </div>
        """
        return {"subject": "投稿エラー: 一部のプラットフォームへの投稿に失敗しました", "html": cls._base_html(content, "投稿エラー通知")}

    @classmethod
    def welcome(cls, data: Dict) -> Dict:
        content = f"""
            <h2 style="color:#00d4aa; margin-top:0;">TradePost Proへようこそ！</h2>
            <p>{data.get('name', 'ユーザー')}さん、ご登録ありがとうございます。</p>
            <p>以下のステップで簡単に始められます。</p>
            <div style="margin:20px 0;">
                <div style="background-color:#0d1117; border-radius:8px; padding:15px; margin:10px 0; border-left:3px solid #00d4aa;">
                    <strong style="color:#00d4aa;">Step 1</strong>
                    <span style="color:#c9d1d9;"> MT4/MT5の接続設定</span>
                </div>
                <div style="background-color:#0d1117; border-radius:8px; padding:15px; margin:10px 0; border-left:3px solid #0984e3;">
                    <strong style="color:#0984e3;">Step 2</strong>
                    <span style="color:#c9d1d9;"> SNSアカウントの連携</span>
                </div>
                <div style="background-color:#0d1117; border-radius:8px; padding:15px; margin:10px 0; border-left:3px solid #f0b429;">
                    <strong style="color:#f0b429;">Step 3</strong>
                    <span style="color:#c9d1d9;"> 投稿テンプレートの選択</span>
                </div>
            </div>
        """
        return {"subject": "TradePost Proへようこそ！", "html": cls._base_html(content, "ようこそ")}

    @classmethod
    def plan_upgraded(cls, data: Dict) -> Dict:
        content = f"""
            <h2 style="color:#00d4aa; margin-top:0;">プランのアップグレードが完了しました</h2>
            <table width="100%" cellpadding="10" style="background-color:#0d1117; border-radius:8px; margin:20px 0;">
                <tr><td style="color:#8b949e;">新プラン</td><td style="color:#00d4aa; text-align:right; font-weight:bold;">{data.get('plan_name', '')}</td></tr>
                <tr><td style="color:#8b949e;">月額</td><td style="color:#ffffff; text-align:right;">{data.get('price', 0):,}円/月</td></tr>
            </table>
            <p>新しいプランの全機能をお楽しみください。</p>
        """
        return {"subject": f"{data.get('plan_name', '')}プランへのアップグレード完了", "html": cls._base_html(content, "プランアップグレード")}

    @classmethod
    def trial_reminder(cls, data: Dict) -> Dict:
        days = data.get("remaining_days", 0)
        content = f"""
            <h2 style="color:#f0b429; margin-top:0;">トライアル残り{days}日</h2>
            <p>TradePost Proの無料トライアルが残り{days}日となりました。</p>
        """
        return {"subject": f"トライアル残り{days}日 - TradePost Pro", "html": cls._base_html(content, "トライアルリマインダー")}

    @classmethod
    def weekly_report(cls, data: Dict) -> Dict:
        profit = data.get("total_profit", 0)
        color = "#00d4aa" if profit >= 0 else "#ff4757"
        sign = "+" if profit >= 0 else ""
        content = f"""
            <h2 style="color:#ffffff; margin-top:0;">週次レポート</h2>
            <p style="color:#8b949e;">{data.get('period', '')}</p>
            <div style="text-align:center; margin:30px 0;">
                <p style="color:#8b949e; margin:0;">週間損益</p>
                <p style="color:{color}; font-size:36px; font-weight:bold; margin:5px 0;">{sign}{profit:,.0f}円</p>
            </div>
            <table width="100%" cellpadding="10" style="background-color:#0d1117; border-radius:8px; margin:20px 0;">
                <tr><td style="color:#8b949e;">取引回数</td><td style="color:#ffffff; text-align:right;">{data.get('total_trades', 0)}回</td></tr>
                <tr><td style="color:#8b949e;">勝率</td><td style="color:#ffffff; text-align:right;">{data.get('win_rate', 0)}%</td></tr>
                <tr><td style="color:#8b949e;">投稿回数</td><td style="color:#ffffff; text-align:right;">{data.get('posts_count', 0)}回</td></tr>
            </table>
        """
        return {"subject": f"週次レポート: {sign}{profit:,.0f}円", "html": cls._base_html(content, "週次レポート")}

    # ------------------------------------------------------------------
    # 2FA 認証コード
    # ------------------------------------------------------------------

    @classmethod
    def two_factor_code(cls, data: Dict) -> Dict:
        code = data.get("code", "000000")
        content = f"""
            <h2 style="color:#00d4aa; margin-top:0;">認証コード</h2>
            <p>ログインの認証コードです。10分以内に入力してください。</p>
            <div style="text-align:center; margin:30px 0;">
                <div style="display:inline-block; background-color:#0d1117; border:2px solid #00d4aa; border-radius:12px; padding:20px 40px;">
                    <span style="color:#00d4aa; font-size:36px; font-weight:bold; letter-spacing:8px;">{code}</span>
                </div>
            </div>
            <p style="color:#8b949e; font-size:13px;">このコードに心当たりがない場合は無視してください。</p>
        """
        return {"subject": f"認証コード: {code} - TradePost Pro", "html": cls._base_html(content, "認証コード")}

    # ------------------------------------------------------------------
    # 管理者向けテンプレート
    # ------------------------------------------------------------------

    @classmethod
    def admin_new_registration(cls, data: Dict) -> Dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"""
            <h2 style="color:#0984e3; margin-top:0;">新規ユーザー登録</h2>
            <table width="100%" cellpadding="10" style="background-color:#0d1117; border-radius:8px; margin:20px 0;">
                <tr><td style="color:#8b949e;">名前</td><td style="color:#ffffff; text-align:right;">{data.get('name', '')}</td></tr>
                <tr><td style="color:#8b949e;">メール</td><td style="color:#ffffff; text-align:right;">{data.get('email', '')}</td></tr>
                <tr><td style="color:#8b949e;">プラン</td><td style="color:#ffffff; text-align:right;">{data.get('plan', 'FREE')}</td></tr>
                <tr><td style="color:#8b949e;">登録日時</td><td style="color:#ffffff; text-align:right;">{now}</td></tr>
            </table>
        """
        return {"subject": f"【新規登録】{data.get('name', '')} ({data.get('email', '')})", "html": cls._base_html(content, "新規ユーザー登録")}

    @classmethod
    def admin_new_subscription(cls, data: Dict) -> Dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"""
            <h2 style="color:#00d4aa; margin-top:0;">新規サブスクリプション</h2>
            <table width="100%" cellpadding="10" style="background-color:#0d1117; border-radius:8px; margin:20px 0;">
                <tr><td style="color:#8b949e;">ユーザー</td><td style="color:#ffffff; text-align:right;">{data.get('name', '')} ({data.get('email', '')})</td></tr>
                <tr><td style="color:#8b949e;">プラン</td><td style="color:#00d4aa; text-align:right; font-weight:bold;">{data.get('plan_name', '')}</td></tr>
                <tr><td style="color:#8b949e;">Subscription ID</td><td style="color:#ffffff; text-align:right; font-size:12px;">{data.get('subscription_id', '')}</td></tr>
                <tr><td style="color:#8b949e;">日時</td><td style="color:#ffffff; text-align:right;">{now}</td></tr>
            </table>
        """
        return {"subject": f"【サブスク】{data.get('name', '')} → {data.get('plan_name', '')}", "html": cls._base_html(content, "新規サブスクリプション")}

    @classmethod
    def contact_form(cls, data: Dict) -> Dict:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"""
            <h2 style="color:#f0b429; margin-top:0;">お問い合わせ</h2>
            <table width="100%" cellpadding="10" style="background-color:#0d1117; border-radius:8px; margin:20px 0;">
                <tr><td style="color:#8b949e;">名前</td><td style="color:#ffffff; text-align:right;">{data.get('name', '')}</td></tr>
                <tr><td style="color:#8b949e;">メール</td><td style="color:#ffffff; text-align:right;">{data.get('email', '')}</td></tr>
                <tr><td style="color:#8b949e;">件名</td><td style="color:#ffffff; text-align:right;">{data.get('subject', '')}</td></tr>
                <tr><td style="color:#8b949e;">日時</td><td style="color:#ffffff; text-align:right;">{now}</td></tr>
            </table>
            <div style="background-color:#0d1117; border-radius:8px; padding:20px; margin:20px 0; border-left:3px solid #f0b429;">
                <p style="color:#c9d1d9; white-space:pre-wrap; margin:0;">{data.get('message', '')}</p>
            </div>
        """
        return {"subject": f"【お問い合わせ】{data.get('subject', '')} - {data.get('name', '')}", "html": cls._base_html(content, "お問い合わせ")}


class EmailService:
    """メール送信サービス（PHP Proxy優先、SMTPフォールバック）"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or EMAIL_CONFIG

    def _send_via_php_proxy(self, to_email: str, subject: str, html_content: str) -> Dict:
        """PHP Mail Proxy 経由でメール送信"""
        if not PHP_MAIL_KEY:
            return {"success": False, "message": "PHP_MAIL_KEY未設定"}

        try:
            resp = requests.post(
                PHP_MAIL_URL,
                data={
                    "to": to_email,
                    "subject": subject,
                    "body": html_content,
                    "security_key": PHP_MAIL_KEY,
                },
                timeout=15,
            )
            result = resp.json()
            if result.get("success"):
                logger.info(f"[PHP Proxy] メール送信成功: {to_email} - {subject}")
                return {"success": True, "message": "PHP Proxy経由で送信"}
            else:
                logger.warning(f"[PHP Proxy] 送信失敗: {result.get('error', 'unknown')}")
                return {"success": False, "message": result.get("error", "PHP Proxy送信失敗")}
        except Exception as e:
            logger.warning(f"[PHP Proxy] エラー: {e}")
            return {"success": False, "message": str(e)}

    def _send_via_smtp(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> Dict:
        """SMTP 経由でメール送信"""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = f"{self.config['from_name']} <{self.config['from_email']}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            msg["Reply-To"] = self.config["reply_to"]

            if text_content:
                msg.attach(MIMEText(text_content, "plain", "utf-8"))
            msg.attach(MIMEText(html_content, "html", "utf-8"))

            if self.config["smtp_user"] and self.config["smtp_password"]:
                with smtplib.SMTP(self.config["smtp_host"], self.config["smtp_port"]) as server:
                    server.starttls()
                    server.login(self.config["smtp_user"], self.config["smtp_password"])
                    server.send_message(msg)
                logger.info(f"[SMTP] メール送信成功: {to_email} - {subject}")
                return {"success": True, "message": "SMTP経由で送信"}
            else:
                logger.warning("SMTP設定が未完了のため、メール送信をスキップ")
                return {"success": False, "message": "SMTP設定が未完了です", "dry_run": True}
        except Exception as e:
            logger.error(f"[SMTP] メール送信エラー: {e}")
            return {"success": False, "message": str(e)}

    def send_email(self, to_email: str, subject: str, html_content: str, text_content: Optional[str] = None) -> Dict:
        """メールを送信（PHP Proxy優先 → SMTPフォールバック）"""
        # 1. PHP Proxy を試行
        result = self._send_via_php_proxy(to_email, subject, html_content)
        if result["success"]:
            return result

        # 2. SMTPフォールバック
        result = self._send_via_smtp(to_email, subject, html_content, text_content)
        return result

    # ------------------------------------------------------------------
    # ユーザー向け送信メソッド
    # ------------------------------------------------------------------

    def send_welcome(self, to_email: str, data: Dict) -> Dict:
        template = EmailTemplate.welcome(data)
        return self.send_email(to_email, template["subject"], template["html"])

    def send_post_success(self, to_email: str, data: Dict) -> Dict:
        template = EmailTemplate.post_success(data)
        return self.send_email(to_email, template["subject"], template["html"])

    def send_post_failure(self, to_email: str, data: Dict) -> Dict:
        template = EmailTemplate.post_failure(data)
        return self.send_email(to_email, template["subject"], template["html"])

    def send_trial_reminder(self, to_email: str, data: Dict) -> Dict:
        template = EmailTemplate.trial_reminder(data)
        return self.send_email(to_email, template["subject"], template["html"])

    def send_plan_upgraded(self, to_email: str, data: Dict) -> Dict:
        template = EmailTemplate.plan_upgraded(data)
        return self.send_email(to_email, template["subject"], template["html"])

    def send_weekly_report(self, to_email: str, data: Dict) -> Dict:
        template = EmailTemplate.weekly_report(data)
        return self.send_email(to_email, template["subject"], template["html"])

    def send_2fa_code(self, to_email: str, code: str) -> Dict:
        template = EmailTemplate.two_factor_code({"code": code})
        return self.send_email(to_email, template["subject"], template["html"])

    # ------------------------------------------------------------------
    # 管理者向け送信メソッド
    # ------------------------------------------------------------------

    def send_admin_new_registration(self, data: Dict) -> Dict:
        template = EmailTemplate.admin_new_registration(data)
        return self.send_email(ADMIN_EMAIL, template["subject"], template["html"])

    def send_admin_new_subscription(self, data: Dict) -> Dict:
        template = EmailTemplate.admin_new_subscription(data)
        return self.send_email(ADMIN_EMAIL, template["subject"], template["html"])

    def send_admin_contact_form(self, data: Dict) -> Dict:
        template = EmailTemplate.contact_form(data)
        return self.send_email(ADMIN_EMAIL, template["subject"], template["html"])
