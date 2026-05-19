"""
TradePost Pro - コメント自動返信Botサービス
SNSへのコメントに自動で返信
"""

import re
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class ReplyMode(str, Enum):
    TEMPLATE = "template"   # テンプレートベース
    AI = "ai"               # AI生成
    HYBRID = "hybrid"       # テンプレート + AI補完


@dataclass
class IncomingComment:
    """受信コメント"""
    comment_id: str = ""
    platform: str = ""
    post_id: str = ""
    author_name: str = ""
    author_id: str = ""
    text: str = ""
    created_at: str = ""
    is_question: bool = False
    sentiment: str = "neutral"  # positive, negative, neutral
    language: str = "ja"


@dataclass
class ReplyResult:
    """返信結果"""
    comment_id: str = ""
    reply_text: str = ""
    mode_used: str = ""
    matched_rule: str = ""
    was_sent: bool = False
    error: str = ""


class AutoReplyService:
    """コメント自動返信Botサービス"""

    # キーワードベースの返信ルール
    REPLY_RULES = {
        "greeting": {
            "keywords": ["こんにちは", "はじめまして", "初めまして", "hello", "hi"],
            "replies": [
                "こんにちは！コメントありがとうございます😊 FXに興味がありましたら、ぜひLINEオープンチャットもご覧ください！",
                "はじめまして！ご覧いただきありがとうございます✨ 一緒にFXを学んでいきましょう！",
            ],
        },
        "question_fx": {
            "keywords": ["どうやって", "やり方", "始め方", "始めたい", "初心者", "教えて"],
            "replies": [
                "ご質問ありがとうございます！FXの始め方については、LINEオープンチャットで詳しく解説していますので、ぜひご参加ください👇",
                "初心者の方も大歓迎です！基礎から学べるLINEオープンチャットをご用意していますので、お気軽にどうぞ😊",
            ],
        },
        "question_result": {
            "keywords": ["すごい", "利益", "儲かる", "稼げる", "結果"],
            "replies": [
                "ありがとうございます！毎日コツコツとトレードを続けています📈 詳しい手法はLINEオープンチャットで共有しています！",
                "ありがとうございます！良い時も悪い時もありますが、継続が大切だと思っています💪 LINEで情報交換しませんか？",
            ],
        },
        "question_tool": {
            "keywords": ["ツール", "EA", "自動売買", "MT4", "MT5", "インジケーター"],
            "replies": [
                "MT4/MT5を使ってトレードしています！ツールの詳細はLINEオープンチャットでお伝えしていますので、ぜひご参加ください🔧",
            ],
        },
        "encouragement": {
            "keywords": ["頑張って", "応援", "ファイト", "がんばれ"],
            "replies": [
                "応援ありがとうございます！これからも頑張ります💪 一緒にトレードを楽しみましょう！",
                "温かいお言葉ありがとうございます😊 引き続き結果を共有していきますね！",
            ],
        },
        "negative": {
            "keywords": ["詐欺", "嘘", "怪しい", "信用できない"],
            "replies": [
                "ご意見ありがとうございます。全ての取引結果はリアルタイムで公開しており、透明性を大切にしています。ご不明な点があればお気軽にお聞きください。",
            ],
        },
        "line_inquiry": {
            "keywords": ["LINE", "ライン", "オープンチャット", "参加", "リンク", "URL"],
            "replies": [
                "LINEオープンチャットへのご興味ありがとうございます！プロフィールのリンクからご参加いただけます😊 お待ちしています！",
            ],
        },
    }

    # スパム・不適切コメントのフィルター
    SPAM_PATTERNS = [
        r"http[s]?://(?!line\.me)",  # LINE以外のURL
        r"DMください",
        r"フォロバ",
        r"相互フォロー",
        r"副業.*万円",
        r"稼げる.*方法",
    ]

    # 返信しないキーワード
    IGNORE_PATTERNS = [
        r"^(笑|w+|草)$",
        r"^[👍❤️🔥💪✨😊]+$",  # 絵文字のみ
    ]

    def __init__(
        self,
        mode: ReplyMode = ReplyMode.HYBRID,
        line_url: str = "https://line.me/ti/g2/example",
        max_replies_per_hour: int = 30,
    ):
        self.mode = mode
        self.line_url = line_url
        self.max_replies_per_hour = max_replies_per_hour
        self.reply_count_hourly: Dict[str, int] = {}
        self.reply_history: List[ReplyResult] = []

        # OpenAI client
        self.ai_client = None
        if HAS_OPENAI and mode in [ReplyMode.AI, ReplyMode.HYBRID]:
            try:
                self.ai_client = OpenAI()
            except Exception:
                pass

    # ============================================================
    # コメント分析
    # ============================================================

    def analyze_comment(self, comment: IncomingComment) -> Dict:
        """コメントを分析"""
        analysis = {
            "is_spam": self._is_spam(comment.text),
            "should_ignore": self._should_ignore(comment.text),
            "is_question": self._is_question(comment.text),
            "sentiment": self._detect_sentiment(comment.text),
            "matched_rules": self._match_rules(comment.text),
            "language": self._detect_language(comment.text),
        }
        return analysis

    def _is_spam(self, text: str) -> bool:
        """スパム判定"""
        for pattern in self.SPAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _should_ignore(self, text: str) -> bool:
        """無視すべきコメントか判定"""
        for pattern in self.IGNORE_PATTERNS:
            if re.match(pattern, text.strip()):
                return True
        return len(text.strip()) < 2

    def _is_question(self, text: str) -> bool:
        """質問かどうか判定"""
        question_markers = ["?", "？", "ですか", "ますか", "でしょうか", "どう", "なぜ", "いつ", "どこ"]
        return any(marker in text for marker in question_markers)

    def _detect_sentiment(self, text: str) -> str:
        """感情分析（簡易版）"""
        positive_words = ["すごい", "素晴らしい", "ありがとう", "最高", "良い", "嬉しい", "応援", "頑張"]
        negative_words = ["詐欺", "嘘", "怪しい", "ダメ", "最悪", "信用できない", "損"]

        pos_count = sum(1 for w in positive_words if w in text)
        neg_count = sum(1 for w in negative_words if w in text)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"

    def _detect_language(self, text: str) -> str:
        """言語検出（簡易版）"""
        if re.search(r'[\u3040-\u309F\u30A0-\u30FF]', text):
            return "ja"
        elif re.search(r'[\u4e00-\u9fff]', text):
            return "zh"
        return "en"

    def _match_rules(self, text: str) -> List[str]:
        """マッチするルールを検索"""
        matched = []
        text_lower = text.lower()
        for rule_name, rule in self.REPLY_RULES.items():
            for keyword in rule["keywords"]:
                if keyword.lower() in text_lower:
                    matched.append(rule_name)
                    break
        return matched

    # ============================================================
    # 返信生成
    # ============================================================

    def generate_reply(self, comment: IncomingComment) -> ReplyResult:
        """コメントに対する返信を生成"""
        analysis = self.analyze_comment(comment)

        # スパム・無視対象
        if analysis["is_spam"]:
            return ReplyResult(comment_id=comment.comment_id, reply_text="", mode_used="skip", matched_rule="spam")

        if analysis["should_ignore"]:
            return ReplyResult(comment_id=comment.comment_id, reply_text="", mode_used="skip", matched_rule="ignore")

        # レート制限チェック
        if not self._check_rate_limit(comment.platform):
            return ReplyResult(
                comment_id=comment.comment_id, reply_text="",
                mode_used="skip", matched_rule="rate_limit",
                error="1時間あたりの返信上限に達しました",
            )

        # モードに応じた返信生成
        if self.mode == ReplyMode.TEMPLATE:
            return self._generate_template_reply(comment, analysis)
        elif self.mode == ReplyMode.AI:
            return self._generate_ai_reply(comment, analysis)
        else:  # HYBRID
            # まずテンプレートを試み、マッチしなければAI
            result = self._generate_template_reply(comment, analysis)
            if not result.reply_text and self.ai_client:
                result = self._generate_ai_reply(comment, analysis)
            return result

    def _generate_template_reply(
        self,
        comment: IncomingComment,
        analysis: Dict,
    ) -> ReplyResult:
        """テンプレートベースの返信"""
        import random

        matched_rules = analysis.get("matched_rules", [])

        if matched_rules:
            rule_name = matched_rules[0]
            rule = self.REPLY_RULES[rule_name]
            reply_text = random.choice(rule["replies"])

            return ReplyResult(
                comment_id=comment.comment_id,
                reply_text=reply_text,
                mode_used="template",
                matched_rule=rule_name,
            )

        # デフォルト返信
        default_replies = [
            f"コメントありがとうございます！😊 LINEオープンチャットでも情報交換していますので、ぜひご参加ください👇\n{self.line_url}",
            "ありがとうございます！引き続きトレード結果を共有していきますね✨",
        ]

        return ReplyResult(
            comment_id=comment.comment_id,
            reply_text=random.choice(default_replies),
            mode_used="template",
            matched_rule="default",
        )

    def _generate_ai_reply(
        self,
        comment: IncomingComment,
        analysis: Dict,
    ) -> ReplyResult:
        """AI生成の返信"""
        if not self.ai_client:
            return self._generate_template_reply(comment, analysis)

        try:
            prompt = f"""あなたはFXトレーダーのSNSアカウントの返信担当です。
以下のコメントに対して、親しみやすく丁寧な返信を生成してください。

ルール:
- 100文字以内で簡潔に
- LINEオープンチャットへの誘導を自然に含める
- 絵文字は1-2個まで
- 投資助言にあたる表現は避ける
- ネガティブなコメントには冷静に対応

コメント: {comment.text}
コメントの感情: {analysis['sentiment']}
質問かどうか: {analysis['is_question']}

返信:"""

            response = self.ai_client.chat.completions.create(
                model="gpt-4.1-nano",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.7,
            )

            reply_text = response.choices[0].message.content.strip()

            return ReplyResult(
                comment_id=comment.comment_id,
                reply_text=reply_text,
                mode_used="ai",
                matched_rule="ai_generated",
            )

        except Exception as e:
            # フォールバック
            return self._generate_template_reply(comment, analysis)

    # ============================================================
    # レート制限
    # ============================================================

    def _check_rate_limit(self, platform: str) -> bool:
        """レート制限チェック"""
        current_hour = datetime.now().strftime("%Y-%m-%d-%H")
        key = f"{platform}_{current_hour}"
        count = self.reply_count_hourly.get(key, 0)

        if count >= self.max_replies_per_hour:
            return False

        self.reply_count_hourly[key] = count + 1
        return True

    # ============================================================
    # バッチ処理
    # ============================================================

    def process_comments(self, comments: List[IncomingComment]) -> List[ReplyResult]:
        """複数コメントを一括処理"""
        results = []
        for comment in comments:
            result = self.generate_reply(comment)
            self.reply_history.append(result)
            results.append(result)
        return results

    def get_stats(self) -> Dict:
        """返信統計を取得"""
        total = len(self.reply_history)
        sent = len([r for r in self.reply_history if r.reply_text])
        skipped = total - sent
        by_mode = {}
        for r in self.reply_history:
            by_mode[r.mode_used] = by_mode.get(r.mode_used, 0) + 1

        return {
            "total_processed": total,
            "replies_sent": sent,
            "skipped": skipped,
            "by_mode": by_mode,
        }


# テスト用
if __name__ == "__main__":
    service = AutoReplyService(mode=ReplyMode.HYBRID)

    test_comments = [
        IncomingComment(comment_id="c1", platform="x", text="こんにちは！FXに興味があります"),
        IncomingComment(comment_id="c2", platform="instagram", text="すごい利益ですね！どうやってるんですか？"),
        IncomingComment(comment_id="c3", platform="x", text="詐欺じゃないの？"),
        IncomingComment(comment_id="c4", platform="threads", text="MT5使ってますか？"),
        IncomingComment(comment_id="c5", platform="x", text="頑張ってください！応援してます"),
        IncomingComment(comment_id="c6", platform="instagram", text="LINEのリンク教えてください"),
        IncomingComment(comment_id="c7", platform="x", text="http://spam.com 副業で100万円稼げます"),
        IncomingComment(comment_id="c8", platform="x", text="w"),
    ]

    print("=== コメント自動返信テスト ===")
    results = service.process_comments(test_comments)

    for comment, result in zip(test_comments, results):
        print(f"\n[{comment.platform}] \"{comment.text}\"")
        if result.reply_text:
            print(f"  → ({result.mode_used}/{result.matched_rule}) {result.reply_text[:80]}...")
        else:
            print(f"  → スキップ ({result.matched_rule})")

    print(f"\n=== 統計 ===")
    stats = service.get_stats()
    print(f"  処理: {stats['total_processed']}件, 返信: {stats['replies_sent']}件, スキップ: {stats['skipped']}件")
    print(f"  モード別: {stats['by_mode']}")

    print("\n✓ コメント自動返信Botサービス テスト完了")
