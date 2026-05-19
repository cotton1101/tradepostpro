"""
TradePost Pro - 国際化（i18n）モジュール
日本語・英語・中国語に対応した多言語テキスト管理
"""

from typing import Dict, Optional


# サポートする言語
SUPPORTED_LANGUAGES = ["ja", "en", "zh"]
DEFAULT_LANGUAGE = "ja"

# 翻訳辞書
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # === 画像テンプレート用テキスト ===
    "daily_report_title": {
        "ja": "本日の取引結果",
        "en": "Daily Trading Report",
        "zh": "今日交易结果",
    },
    "daily_profit_loss": {
        "ja": "本日の損益",
        "en": "Today's P&L",
        "zh": "今日盈亏",
    },
    "total_trades": {
        "ja": "取引回数",
        "en": "Total Trades",
        "zh": "交易次数",
    },
    "win_rate": {
        "ja": "勝率",
        "en": "Win Rate",
        "zh": "胜率",
    },
    "wins": {
        "ja": "勝ち",
        "en": "Wins",
        "zh": "盈利",
    },
    "losses": {
        "ja": "負け",
        "en": "Losses",
        "zh": "亏损",
    },
    "cumulative_profit": {
        "ja": "累計損益",
        "en": "Cumulative P&L",
        "zh": "累计盈亏",
    },
    "currency_yen": {
        "ja": "円",
        "en": "JPY",
        "zh": "日元",
    },
    "trades_unit": {
        "ja": "回",
        "en": "",
        "zh": "次",
    },

    # === SNS投稿テキスト ===
    "post_header": {
        "ja": "📊 本日のFX取引結果",
        "en": "📊 Today's FX Trading Results",
        "zh": "📊 今日外汇交易结果",
    },
    "post_profit": {
        "ja": "💰 損益: {amount}円",
        "en": "💰 P&L: ¥{amount}",
        "zh": "💰 盈亏: {amount}日元",
    },
    "post_trades": {
        "ja": "📈 取引: {count}回（{wins}勝{losses}敗）",
        "en": "📈 Trades: {count} ({wins}W-{losses}L)",
        "zh": "📈 交易: {count}次（{wins}胜{losses}负）",
    },
    "post_win_rate": {
        "ja": "🎯 勝率: {rate}%",
        "en": "🎯 Win Rate: {rate}%",
        "zh": "🎯 胜率: {rate}%",
    },
    "post_cumulative": {
        "ja": "📊 累計: {amount}円",
        "en": "📊 Cumulative: ¥{amount}",
        "zh": "📊 累计: {amount}日元",
    },
    "post_line_invite": {
        "ja": "👥 LINEオープンチャットで詳細を共有中！\n参加はこちら👇\n{url}",
        "en": "👥 Join our LINE Open Chat for details!\nJoin here👇\n{url}",
        "zh": "👥 加入LINE群聊获取详情！\n点击加入👇\n{url}",
    },
    "post_hashtags_x": {
        "ja": "#FX #トレード #XM #投資 #FX自動投稿",
        "en": "#FX #Trading #XM #Investment #AutoPost",
        "zh": "#外汇 #交易 #XM #投资 #自动发布",
    },
    "post_hashtags_instagram": {
        "ja": "#FX #トレード #XM #投資 #FX自動投稿 #副業 #アフィリエイト #FXトレーダー",
        "en": "#FX #Trading #XM #Investment #AutoPost #SideHustle #Affiliate #FXTrader",
        "zh": "#外汇 #交易 #XM #投资 #自动发布 #副业 #联盟营销 #外汇交易员",
    },
    "no_trades_today": {
        "ja": "本日の取引はありませんでした",
        "en": "No trades today",
        "zh": "今日无交易",
    },

    # === 週次・月次レポート ===
    "weekly_report_title": {
        "ja": "今週の取引結果",
        "en": "Weekly Trading Report",
        "zh": "本周交易结果",
    },
    "monthly_report_title": {
        "ja": "今月の取引結果",
        "en": "Monthly Trading Report",
        "zh": "本月交易结果",
    },
    "period": {
        "ja": "期間",
        "en": "Period",
        "zh": "期间",
    },
    "total_profit_loss": {
        "ja": "合計損益",
        "en": "Total P&L",
        "zh": "总盈亏",
    },
    "trading_days": {
        "ja": "取引日数",
        "en": "Trading Days",
        "zh": "交易天数",
    },
    "best_day": {
        "ja": "最高日",
        "en": "Best Day",
        "zh": "最佳日",
    },
    "worst_day": {
        "ja": "最低日",
        "en": "Worst Day",
        "zh": "最差日",
    },
    "average_daily": {
        "ja": "日平均",
        "en": "Daily Avg",
        "zh": "日均",
    },

    # === ダッシュボード ===
    "dashboard_title": {
        "ja": "ダッシュボード",
        "en": "Dashboard",
        "zh": "仪表盘",
    },
    "settings": {
        "ja": "設定",
        "en": "Settings",
        "zh": "设置",
    },
    "sns_settings": {
        "ja": "SNS設定",
        "en": "SNS Settings",
        "zh": "社交媒体设置",
    },
    "plan_settings": {
        "ja": "プラン設定",
        "en": "Plan Settings",
        "zh": "套餐设置",
    },
    "post_history": {
        "ja": "投稿履歴",
        "en": "Post History",
        "zh": "发布历史",
    },
    "login": {
        "ja": "ログイン",
        "en": "Login",
        "zh": "登录",
    },
    "register": {
        "ja": "新規登録",
        "en": "Sign Up",
        "zh": "注册",
    },
    "logout": {
        "ja": "ログアウト",
        "en": "Logout",
        "zh": "退出",
    },

    # === メール通知 ===
    "email_post_success_subject": {
        "ja": "【TradePost Pro】本日の自動投稿が完了しました",
        "en": "[TradePost Pro] Daily auto-post completed",
        "zh": "【TradePost Pro】今日自动发布已完成",
    },
    "email_post_failed_subject": {
        "ja": "【TradePost Pro】自動投稿でエラーが発生しました",
        "en": "[TradePost Pro] Auto-post error occurred",
        "zh": "【TradePost Pro】自动发布出现错误",
    },
    "email_trial_ending_subject": {
        "ja": "【TradePost Pro】無料トライアルがまもなく終了します",
        "en": "[TradePost Pro] Your free trial is ending soon",
        "zh": "【TradePost Pro】免费试用即将结束",
    },
    "email_welcome_subject": {
        "ja": "【TradePost Pro】ご登録ありがとうございます",
        "en": "[TradePost Pro] Welcome to TradePost Pro",
        "zh": "【TradePost Pro】感谢您的注册",
    },
}


class I18n:
    """国際化ヘルパークラス"""

    def __init__(self, language: str = DEFAULT_LANGUAGE):
        if language not in SUPPORTED_LANGUAGES:
            language = DEFAULT_LANGUAGE
        self.language = language

    def t(self, key: str, **kwargs) -> str:
        """翻訳テキストを取得"""
        translation = TRANSLATIONS.get(key, {})
        text = translation.get(self.language, translation.get(DEFAULT_LANGUAGE, key))
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text

    def set_language(self, language: str):
        """言語を変更"""
        if language in SUPPORTED_LANGUAGES:
            self.language = language

    @staticmethod
    def get_supported_languages() -> list:
        """サポートする言語一覧を返す"""
        return SUPPORTED_LANGUAGES.copy()

    @staticmethod
    def get_language_name(code: str) -> str:
        """言語コードから表示名を返す"""
        names = {
            "ja": "日本語",
            "en": "English",
            "zh": "中文",
        }
        return names.get(code, code)


# デフォルトインスタンス
_default_i18n = I18n()


def t(key: str, **kwargs) -> str:
    """グローバル翻訳関数"""
    return _default_i18n.t(key, **kwargs)


def set_language(language: str):
    """グローバル言語設定"""
    _default_i18n.set_language(language)


if __name__ == "__main__":
    # テスト
    for lang in SUPPORTED_LANGUAGES:
        i18n = I18n(lang)
        print(f"\n=== {i18n.get_language_name(lang)} ({lang}) ===")
        print(i18n.t("daily_report_title"))
        print(i18n.t("post_profit", amount="+17,000"))
        print(i18n.t("post_trades", count=12, wins=8, losses=4))
        print(i18n.t("post_win_rate", rate="66.7"))
