"""
SEO最適化ブログ自動生成サービス
取引結果を元にSEO記事を自動生成し、WordPressに投稿する
"""

import json
import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class BlogArticle:
    """ブログ記事データ"""
    title: str
    slug: str
    content: str
    excerpt: str
    meta_title: str
    meta_description: str
    keywords: list
    categories: list
    tags: list
    featured_image_url: Optional[str] = None
    status: str = "draft"
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SEOBlogService:
    """SEOブログ自動生成・WordPress投稿サービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.wp_url = self.config.get("wordpress_url", "")
        self.wp_user = self.config.get("wordpress_user", "")
        self.wp_app_password = self.config.get("wordpress_app_password", "")
        self.openai_api_key = self.config.get("openai_api_key", "")

        # SEOテンプレート
        self.article_templates = {
            "daily_report": {
                "title_patterns": [
                    "【{date}】FXトレード日報｜{result}の{amount}円を達成",
                    "{date}のFX取引結果：{win_rate}の勝率で{amount}円の{result}",
                    "FX日次レポート {date}｜{trades}回の取引で{amount}円{result}",
                ],
                "categories": ["FXトレード日報", "取引結果"],
                "base_keywords": ["FX", "トレード", "日報", "取引結果", "XM"],
            },
            "weekly_summary": {
                "title_patterns": [
                    "【週間まとめ】{start_date}〜{end_date}のFXトレード結果",
                    "FX週間レポート：{amount}円の{result}｜{start_date}〜{end_date}",
                ],
                "categories": ["FX週間レポート", "取引結果"],
                "base_keywords": ["FX", "週間", "まとめ", "トレード結果"],
            },
            "monthly_analysis": {
                "title_patterns": [
                    "【{year}年{month}月】FXトレード月間レポート｜{amount}円の{result}",
                    "{year}年{month}月のFX取引分析：勝率{win_rate}で{amount}円{result}",
                ],
                "categories": ["FX月間レポート", "取引分析"],
                "base_keywords": ["FX", "月間", "分析", "レポート", "トレード"],
            },
            "strategy_insight": {
                "title_patterns": [
                    "FXで{amount}円{result}した手法を公開｜{date}の取引振り返り",
                    "【FX手法】{win_rate}の勝率を実現した{date}のトレード戦略",
                ],
                "categories": ["FX手法", "トレード戦略"],
                "base_keywords": ["FX", "手法", "戦略", "トレード", "勝率"],
            },
        }

    def generate_article(self, trade_data: dict, template_type: str = "daily_report") -> BlogArticle:
        """取引データからSEO最適化された記事を生成"""
        template = self.article_templates.get(template_type, self.article_templates["daily_report"])

        # 基本データの準備
        date_str = trade_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        profit = trade_data.get("daily_profit", 0)
        win_rate = trade_data.get("win_rate", 0)
        total_trades = trade_data.get("total_trades", 0)
        wins = trade_data.get("wins", 0)
        losses = trade_data.get("losses", 0)

        result = "利益" if profit >= 0 else "損失"
        amount = abs(profit)

        # タイトル生成
        title = self._generate_title(template, {
            "date": date_str,
            "result": result,
            "amount": f"{amount:,.0f}",
            "win_rate": f"{win_rate:.1f}%",
            "trades": total_trades,
        })

        # スラッグ生成
        slug = self._generate_slug(date_str, template_type)

        # 記事本文生成
        content = self._generate_content(trade_data, template_type)

        # メタデータ生成
        meta_title = f"{title} | TradePost Pro"
        if len(meta_title) > 60:
            meta_title = meta_title[:57] + "..."

        meta_description = self._generate_meta_description(trade_data, template_type)

        # キーワード生成
        keywords = self._generate_keywords(trade_data, template)

        # タグ生成
        tags = self._generate_tags(trade_data)

        # 抜粋生成
        excerpt = self._generate_excerpt(trade_data, template_type)

        return BlogArticle(
            title=title,
            slug=slug,
            content=content,
            excerpt=excerpt,
            meta_title=meta_title,
            meta_description=meta_description,
            keywords=keywords,
            categories=template["categories"],
            tags=tags,
            status="draft",
        )

    def _generate_title(self, template: dict, params: dict) -> str:
        """SEO最適化されたタイトルを生成"""
        import random
        pattern = random.choice(template["title_patterns"])
        try:
            title = pattern.format(**params)
        except KeyError:
            title = f"FXトレード結果 {params.get('date', '')}｜{params.get('amount', '0')}円の{params.get('result', '結果')}"
        return title

    def _generate_slug(self, date_str: str, template_type: str) -> str:
        """URLスラッグを生成"""
        date_part = date_str.replace("-", "")
        type_map = {
            "daily_report": "daily",
            "weekly_summary": "weekly",
            "monthly_analysis": "monthly",
            "strategy_insight": "strategy",
        }
        return f"fx-trade-{type_map.get(template_type, 'report')}-{date_part}"

    def _generate_content(self, trade_data: dict, template_type: str) -> str:
        """SEO最適化された記事本文を生成"""
        date_str = trade_data.get("date", datetime.now().strftime("%Y-%m-%d"))
        profit = trade_data.get("daily_profit", 0)
        win_rate = trade_data.get("win_rate", 0)
        total_trades = trade_data.get("total_trades", 0)
        wins = trade_data.get("wins", 0)
        losses = trade_data.get("losses", 0)
        cumulative = trade_data.get("cumulative_profit", 0)

        result_text = "プラス" if profit >= 0 else "マイナス"
        emoji_result = "📈" if profit >= 0 else "📉"

        content = f"""
<article class="trade-report" itemscope itemtype="https://schema.org/Article">

<h2>{emoji_result} {date_str} のFXトレード結果</h2>

<p>本日のFXトレード結果をご報告します。{date_str}は合計<strong>{total_trades}回</strong>の取引を行い、
<strong>{result_text}{abs(profit):,.0f}円</strong>の結果となりました。</p>

<div class="trade-summary-box">
<h3>📊 本日の取引サマリー</h3>
<table class="trade-table">
<thead>
<tr><th>項目</th><th>結果</th></tr>
</thead>
<tbody>
<tr><td>日次損益</td><td><strong>{profit:+,.0f}円</strong></td></tr>
<tr><td>取引回数</td><td>{total_trades}回</td></tr>
<tr><td>勝敗</td><td>{wins}勝 {losses}敗</td></tr>
<tr><td>勝率</td><td>{win_rate:.1f}%</td></tr>
<tr><td>累計損益</td><td>{cumulative:+,.0f}円</td></tr>
</tbody>
</table>
</div>

<h3>📝 本日のトレード振り返り</h3>

<p>本日は{total_trades}回のエントリーを行いました。勝率は<strong>{win_rate:.1f}%</strong>で、
{wins}勝{losses}敗という結果になりました。</p>

{"<p>利益を確保できた要因としては、エントリーポイントの見極めとリスク管理が適切に機能したことが挙げられます。特にトレンドフォロー戦略が効果的に機能しました。</p>" if profit > 0 else "<p>損失の主な要因としては、レンジ相場でのエントリータイミングの判断ミスが考えられます。今後はエントリー条件をより厳格にする必要があります。</p>"}

<h3>📈 累計パフォーマンス</h3>

<p>累計損益は<strong>{cumulative:+,.0f}円</strong>となっています。
{"順調に利益を積み上げることができています。" if cumulative > 0 else "まだマイナス圏ですが、着実にリカバリーを進めています。"}</p>

<h3>🎯 明日の戦略</h3>

<p>明日も引き続き、リスク管理を徹底しながらトレードを行っていきます。
特に以下のポイントに注意してトレードを行う予定です。</p>

<ul>
<li>主要経済指標の発表時間を事前にチェック</li>
<li>損切りラインを明確に設定してからエントリー</li>
<li>ポジションサイズの管理を徹底</li>
<li>トレンドの方向性を確認してからエントリー</li>
</ul>

<h3>💬 LINEオープンチャットで情報共有中</h3>

<p>毎日のトレード結果や相場分析をLINEオープンチャットでリアルタイムに共有しています。
FXに興味がある方はぜひご参加ください。</p>

<div class="cta-box">
<p><strong>▶ LINEオープンチャットに参加する</strong></p>
<p>無料で参加できます。トレーダー同士の情報交換の場としてご活用ください。</p>
</div>

</article>

<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{date_str}のFXトレード結果",
  "datePublished": "{datetime.now().isoformat()}",
  "author": {{
    "@type": "Organization",
    "name": "TradePost Pro"
  }},
  "description": "{date_str}のFXトレード結果。{total_trades}回の取引で{profit:+,.0f}円。勝率{win_rate:.1f}%。"
}}
</script>
"""
        return content.strip()

    def _generate_meta_description(self, trade_data: dict, template_type: str) -> str:
        """メタディスクリプションを生成（120-160文字）"""
        date_str = trade_data.get("date", "")
        profit = trade_data.get("daily_profit", 0)
        win_rate = trade_data.get("win_rate", 0)
        total_trades = trade_data.get("total_trades", 0)

        desc = f"{date_str}のFXトレード結果を公開。{total_trades}回の取引で{profit:+,.0f}円。勝率{win_rate:.1f}%。毎日の取引結果と戦略を詳しく解説しています。"

        if len(desc) > 160:
            desc = desc[:157] + "..."
        return desc

    def _generate_keywords(self, trade_data: dict, template: dict) -> list:
        """SEOキーワードを生成"""
        keywords = list(template["base_keywords"])
        date_str = trade_data.get("date", "")
        if date_str:
            keywords.append(f"FX {date_str}")
        keywords.extend(["FX 実績", "FX 収支", "FX ブログ", "XM トレード"])
        return keywords[:10]

    def _generate_tags(self, trade_data: dict) -> list:
        """記事タグを生成"""
        tags = ["FX", "トレード", "取引結果", "XM"]
        profit = trade_data.get("daily_profit", 0)
        if profit > 0:
            tags.append("利益")
        else:
            tags.append("損失")

        win_rate = trade_data.get("win_rate", 0)
        if win_rate >= 70:
            tags.append("高勝率")
        return tags

    def _generate_excerpt(self, trade_data: dict, template_type: str) -> str:
        """記事の抜粋を生成"""
        date_str = trade_data.get("date", "")
        profit = trade_data.get("daily_profit", 0)
        total_trades = trade_data.get("total_trades", 0)
        return f"{date_str}のFXトレード結果。{total_trades}回の取引で{profit:+,.0f}円の結果となりました。"

    def publish_to_wordpress(self, article: BlogArticle) -> dict:
        """WordPress REST APIで記事を投稿"""
        if not self.wp_url or not self.wp_user:
            return {"success": False, "error": "WordPress設定が未完了です"}

        import requests
        from requests.auth import HTTPBasicAuth

        endpoint = f"{self.wp_url}/wp-json/wp/v2/posts"

        post_data = {
            "title": article.title,
            "slug": article.slug,
            "content": article.content,
            "excerpt": article.excerpt,
            "status": article.status,
            "meta": {
                "_yoast_wpseo_title": article.meta_title,
                "_yoast_wpseo_metadesc": article.meta_description,
                "_yoast_wpseo_focuskw": ", ".join(article.keywords[:3]),
            },
        }

        try:
            response = requests.post(
                endpoint,
                json=post_data,
                auth=HTTPBasicAuth(self.wp_user, self.wp_app_password),
                timeout=30,
            )
            if response.status_code in (200, 201):
                result = response.json()
                return {
                    "success": True,
                    "post_id": result.get("id"),
                    "url": result.get("link"),
                    "status": result.get("status"),
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def generate_sitemap_entry(self, article: BlogArticle, base_url: str) -> str:
        """サイトマップエントリを生成"""
        return f"""  <url>
    <loc>{base_url}/{article.slug}/</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>"""

    def get_internal_links(self, current_date: str, count: int = 3) -> list:
        """内部リンク候補を生成"""
        links = []
        base_date = datetime.strptime(current_date, "%Y-%m-%d")
        for i in range(1, count + 1):
            prev_date = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
            slug = f"fx-trade-daily-{prev_date.replace('-', '')}"
            links.append({
                "slug": slug,
                "title": f"{prev_date}のFXトレード結果",
                "date": prev_date,
            })
        return links


# テスト実行
if __name__ == "__main__":
    service = SEOBlogService()

    trade_data = {
        "date": "2026-03-11",
        "daily_profit": 17000,
        "win_rate": 66.7,
        "total_trades": 12,
        "wins": 8,
        "losses": 4,
        "cumulative_profit": 285000,
    }

    # 記事生成テスト
    article = service.generate_article(trade_data, "daily_report")
    print(f"=== 生成された記事 ===")
    print(f"タイトル: {article.title}")
    print(f"スラッグ: {article.slug}")
    print(f"メタタイトル: {article.meta_title}")
    print(f"メタ説明: {article.meta_description}")
    print(f"キーワード: {', '.join(article.keywords)}")
    print(f"カテゴリ: {', '.join(article.categories)}")
    print(f"タグ: {', '.join(article.tags)}")
    print(f"抜粋: {article.excerpt}")
    print(f"本文長: {len(article.content)}文字")

    # 戦略記事テスト
    strategy_article = service.generate_article(trade_data, "strategy_insight")
    print(f"\n=== 戦略記事 ===")
    print(f"タイトル: {strategy_article.title}")

    # サイトマップテスト
    sitemap = service.generate_sitemap_entry(article, "https://example.com")
    print(f"\n=== サイトマップ ===")
    print(sitemap)

    # 内部リンクテスト
    links = service.get_internal_links("2026-03-11")
    print(f"\n=== 内部リンク候補 ===")
    for link in links:
        print(f"  {link['title']} -> /{link['slug']}/")

    print("\n✓ SEOブログ自動生成サービス テスト完了")
