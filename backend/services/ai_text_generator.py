"""
TradePost Pro - AI投稿文自動生成サービス
GPT APIを使って取引結果に応じた魅力的な投稿文を自動生成
"""

import os
import json
import random
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, List


@dataclass
class GeneratedPost:
    """生成された投稿文"""
    platform: str = ""
    text: str = ""
    hashtags: List[str] = field(default_factory=list)
    tone: str = ""
    char_count: int = 0
    model_used: str = ""


class AITextGenerator:
    """AI投稿文自動生成サービス"""

    PLATFORM_LIMITS = {
        "x": 280,
        "instagram": 2200,
        "threads": 500,
        "tiktok": 2200,
        "line": 5000,
    }

    TONES = {
        "professional": "プロフェッショナルで信頼感のある",
        "casual": "カジュアルで親しみやすい",
        "motivational": "モチベーションを高める熱い",
        "analytical": "データ分析的で知的な",
        "humorous": "ユーモアを交えた楽しい",
    }

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4.1-mini"):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.client = None
        if self.api_key:
            try:
                from openai import OpenAI
                self.client = OpenAI()
            except ImportError:
                pass

    # ============================================================
    # プロンプト構築
    # ============================================================

    def _build_system_prompt(self, platform: str, tone: str) -> str:
        """システムプロンプトを構築"""
        tone_desc = self.TONES.get(tone, self.TONES["professional"])
        char_limit = self.PLATFORM_LIMITS.get(platform, 500)

        return f"""あなたはFXトレードの結果をSNSに投稿するプロのコピーライターです。
以下のルールに従って{tone_desc}トーンで投稿文を生成してください。

【ルール】
1. {platform}向けの投稿文を生成すること（最大{char_limit}文字）
2. 取引結果のデータを魅力的に伝えること
3. フォロワーの興味を引く書き出しにすること
4. LINEオープンチャットへの誘導文を自然に含めること
5. 適切なハッシュタグを3〜5個含めること
6. 絵文字は適度に使用すること（使いすぎない）
7. 利益の場合はポジティブに、損失の場合は学びや反省を含めること
8. 投資助言にならないよう注意すること

【出力形式】
JSON形式で以下を返してください：
{{"text": "投稿本文", "hashtags": ["タグ1", "タグ2", ...]}}"""

    def _build_user_prompt(self, trade_data: Dict) -> str:
        """ユーザープロンプトを構築"""
        profit = trade_data.get("profit", 0)
        profit_str = f"+{profit:,}円" if profit >= 0 else f"{profit:,}円"
        result = "利益" if profit >= 0 else "損失"

        return f"""以下のFXトレード結果をもとに投稿文を生成してください。

【本日のトレード結果】
- 日付: {trade_data.get('date', datetime.now().strftime('%Y年%m月%d日'))}
- 日次損益: {profit_str}（{result}）
- 取引回数: {trade_data.get('total_trades', 0)}回
- 勝敗: {trade_data.get('wins', 0)}勝{trade_data.get('losses', 0)}敗
- 勝率: {trade_data.get('win_rate', 0):.1f}%
- 累計損益: {trade_data.get('cumulative_profit', 0):+,}円

【LINEオープンチャットURL】
{trade_data.get('line_url', 'https://line.me/ti/g2/xxxxx')}"""

    # ============================================================
    # AI生成
    # ============================================================

    def generate_with_ai(
        self,
        trade_data: Dict,
        platform: str = "x",
        tone: str = "professional",
    ) -> GeneratedPost:
        """GPT APIを使って投稿文を生成"""
        if not self.client:
            return self._generate_fallback(trade_data, platform, tone)

        system_prompt = self._build_system_prompt(platform, tone)
        user_prompt = self._build_user_prompt(trade_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.8,
                max_tokens=500,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            parsed = json.loads(content)

            text = parsed.get("text", "")
            hashtags = parsed.get("hashtags", [])

            # 文字数制限チェック
            limit = self.PLATFORM_LIMITS.get(platform, 500)
            if len(text) > limit:
                text = text[:limit - 3] + "..."

            return GeneratedPost(
                platform=platform,
                text=text,
                hashtags=hashtags,
                tone=tone,
                char_count=len(text),
                model_used=self.model,
            )

        except Exception as e:
            print(f"AI生成エラー: {e}")
            return self._generate_fallback(trade_data, platform, tone)

    def generate_multi_platform(
        self,
        trade_data: Dict,
        platforms: Optional[List[str]] = None,
        tone: str = "professional",
    ) -> Dict[str, GeneratedPost]:
        """複数プラットフォーム向けの投稿文を一括生成"""
        if platforms is None:
            platforms = ["x", "instagram", "threads", "tiktok", "line"]

        results = {}
        for platform in platforms:
            results[platform] = self.generate_with_ai(trade_data, platform, tone)

        return results

    # ============================================================
    # フォールバック（API未設定時のテンプレート生成）
    # ============================================================

    def _generate_fallback(
        self,
        trade_data: Dict,
        platform: str,
        tone: str,
    ) -> GeneratedPost:
        """AIが使えない場合のテンプレートベース生成"""
        profit = trade_data.get("profit", 0)
        wins = trade_data.get("wins", 0)
        losses = trade_data.get("losses", 0)
        win_rate = trade_data.get("win_rate", 0)
        date = trade_data.get("date", datetime.now().strftime("%Y/%m/%d"))
        line_url = trade_data.get("line_url", "")

        if profit >= 0:
            profit_str = f"+{profit:,}円"
            templates = self._get_profit_templates(platform)
        else:
            profit_str = f"{profit:,}円"
            templates = self._get_loss_templates(platform)

        template = random.choice(templates)
        text = template.format(
            date=date,
            profit=profit_str,
            wins=wins,
            losses=losses,
            win_rate=f"{win_rate:.1f}",
            line_url=line_url,
        )

        hashtags = ["FX", "トレード", "投資", "FX初心者", "デイトレ"]

        return GeneratedPost(
            platform=platform,
            text=text,
            hashtags=hashtags,
            tone=tone,
            char_count=len(text),
            model_used="template_fallback",
        )

    def _get_profit_templates(self, platform: str) -> List[str]:
        """利益時のテンプレート"""
        if platform == "x":
            return [
                "【{date} トレード結果】\n\n日次損益: {profit}\n勝率: {win_rate}% ({wins}勝{losses}敗)\n\n今日も着実にプラスで終了。\n詳しい手法はLINEで公開中\n{line_url}\n\n#FX #トレード",
                "本日のFX結果\n{profit} ({wins}勝{losses}敗)\n\n勝率{win_rate}%で安定した1日でした。\nリアルタイムの分析はこちら\n{line_url}\n\n#FX #投資",
                "{date}\n結果: {profit}\n\nコツコツ積み上げていきます。\n毎日の結果を共有中\n{line_url}\n\n#FX #デイトレ",
            ]
        else:
            return [
                "{date} のトレード結果\n\n日次損益: {profit}\n取引: {wins}勝{losses}敗 (勝率{win_rate}%)\n\n今日もプラスで終えることができました。\n毎日の結果やトレード手法について、LINEオープンチャットで詳しく共有しています。\n\n参加はこちら: {line_url}\n\n#FX #トレード #投資 #FX初心者",
                "本日のFXトレード結果\n\n{profit} / 勝率{win_rate}%\n{wins}勝{losses}敗\n\n安定した結果を出せた1日でした。\nリアルタイムの分析や手法はLINEオープンチャットで公開中です。\n\n{line_url}\n\n#FX #デイトレ #投資初心者",
            ]

    def _get_loss_templates(self, platform: str) -> List[str]:
        """損失時のテンプレート"""
        if platform == "x":
            return [
                "【{date} トレード結果】\n\n日次損益: {profit}\n勝率: {win_rate}% ({wins}勝{losses}敗)\n\n今日はマイナスでしたが、損切りルールを守れました。\n振り返りはLINEで共有中\n{line_url}\n\n#FX #トレード",
                "{date}\n結果: {profit}\n\n負けた日こそ学びがある。\n反省点をLINEで共有しています\n{line_url}\n\n#FX #投資",
            ]
        else:
            return [
                "{date} のトレード結果\n\n日次損益: {profit}\n取引: {wins}勝{losses}敗 (勝率{win_rate}%)\n\n今日はマイナスの結果となりましたが、損切りルールを徹底できたことは良かったです。\n毎日の振り返りをLINEオープンチャットで共有しています。\n\n{line_url}\n\n#FX #トレード #投資 #FX初心者",
            ]

    # ============================================================
    # トーン分析・提案
    # ============================================================

    def suggest_tone(self, trade_data: Dict) -> str:
        """取引結果に応じた最適なトーンを提案"""
        profit = trade_data.get("profit", 0)
        win_rate = trade_data.get("win_rate", 0)

        if profit > 10000 and win_rate > 70:
            return "motivational"
        elif profit > 0 and win_rate > 50:
            return "professional"
        elif profit > 0:
            return "casual"
        elif profit > -5000:
            return "analytical"
        else:
            return "professional"

    def get_available_tones(self) -> Dict[str, str]:
        """利用可能なトーン一覧"""
        return self.TONES.copy()


# テスト用
if __name__ == "__main__":
    generator = AITextGenerator()

    trade_data = {
        "date": "2026/03/11",
        "profit": 23500,
        "total_trades": 12,
        "wins": 8,
        "losses": 4,
        "win_rate": 66.7,
        "cumulative_profit": 185000,
        "line_url": "https://line.me/ti/g2/example",
    }

    # フォールバック生成テスト
    print("=== フォールバック生成（テンプレート） ===")
    for platform in ["x", "instagram", "threads"]:
        post = generator.generate_with_ai(trade_data, platform, "professional")
        print(f"\n[{platform}] ({post.char_count}文字, {post.model_used})")
        print(post.text[:200])

    # AI生成テスト（APIキーがある場合）
    if generator.client:
        print("\n\n=== AI生成（GPT API） ===")
        post = generator.generate_with_ai(trade_data, "x", "motivational")
        print(f"[x] ({post.char_count}文字, {post.model_used})")
        print(post.text)
        print(f"ハッシュタグ: {post.hashtags}")

    # トーン提案テスト
    suggested = generator.suggest_tone(trade_data)
    print(f"\n推奨トーン: {suggested} ({generator.TONES[suggested]})")

    # 損失時テスト
    loss_data = {**trade_data, "profit": -8500, "wins": 3, "losses": 9, "win_rate": 25.0}
    post_loss = generator.generate_with_ai(loss_data, "x", "analytical")
    print(f"\n=== 損失時 ===")
    print(f"[x] ({post_loss.char_count}文字)")
    print(post_loss.text[:200])

    print("\n✓ AI投稿文生成サービス テスト完了")
