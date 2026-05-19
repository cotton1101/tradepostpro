# TradePost Pro - Public API リファレンス

## 概要

TradePost Pro Public APIは、外部アプリケーションからTradePost Proの機能にアクセスするためのREST APIです。取引データの送信、SNS投稿の実行、スケジュール管理などをプログラムから操作できます。

**Base URL**: `https://api.tradepost-pro.com/api/v1`

**API Version**: 1.0.0

---

## 認証

すべてのAPIリクエストには、HTTPヘッダーにAPIキーを含める必要があります。

```
X-API-Key: your_api_key_here
```

APIキーはダッシュボードの「設定」→「API設定」から発行できます。

### レート制限

| プラン | リクエスト上限 |
|--------|--------------|
| ライト | 300 req/hour |
| スタンダード | 1,000 req/hour |
| プレミアム | 5,000 req/hour |

レート制限に達した場合、`429 Too Many Requests` が返されます。

レスポンスヘッダーで残りリクエスト数を確認できます：

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1709200000
```

---

## エンドポイント一覧

### 取引データ

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/trades` | 取引データを送信 |
| GET | `/trades` | 取引履歴を取得 |
| GET | `/trades/summary` | 取引サマリーを取得 |

### 投稿

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/posts` | SNSに投稿 |
| GET | `/posts` | 投稿履歴を取得 |
| GET | `/posts/{post_id}` | 投稿詳細を取得 |

### スケジュール

| メソッド | パス | 説明 |
|---------|------|------|
| POST | `/schedules` | 投稿スケジュールを設定 |
| GET | `/schedules` | スケジュール一覧を取得 |
| DELETE | `/schedules/{schedule_id}` | スケジュールを削除 |

### テンプレート

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/templates` | 利用可能なテンプレート一覧 |

### アカウント

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/account` | アカウント情報を取得 |
| GET | `/account/usage` | API使用量を取得 |

### Webhook

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/webhooks` | Webhook一覧を取得 |

### システム

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/status` | APIステータス（認証不要） |

---

## 詳細リファレンス

### POST /trades - 取引データを送信

MT4/MT5の日次取引データを送信します。

**リクエストボディ:**

```json
{
  "date": "2026-03-11",
  "profit": 17000,
  "total_trades": 12,
  "wins": 8,
  "losses": 4,
  "cumulative_profit": 250000,
  "account_id": "MT5-12345",
  "platform": "mt5"
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| date | string | Yes | 取引日（YYYY-MM-DD） |
| profit | number | Yes | 日次損益（円） |
| total_trades | integer | Yes | 取引回数 |
| wins | integer | Yes | 勝ち数 |
| losses | integer | Yes | 負け数 |
| cumulative_profit | number | No | 累計損益（円） |
| account_id | string | No | 口座ID |
| platform | string | No | mt4 or mt5（デフォルト: mt5） |

**レスポンス:**

```json
{
  "success": true,
  "data": {
    "trade_id": "a1b2c3d4e5f6g7h8",
    "date": "2026-03-11",
    "profit": 17000,
    "win_rate": 66.7,
    "status": "received"
  },
  "message": "取引データを受信しました",
  "timestamp": "2026-03-11T07:00:00"
}
```

### POST /posts - SNSに投稿

最新の取引データを使用してSNSに投稿します。

**リクエストボディ:**

```json
{
  "platforms": ["x", "instagram", "threads"],
  "template": "dark_classic",
  "language": "ja",
  "custom_text": null,
  "include_affiliate_link": true
}
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| platforms | array | Yes | 投稿先SNS（x, instagram, threads, tiktok, line） |
| template | string | No | 画像テンプレート名（デフォルト: dark_classic） |
| language | string | No | 言語（ja, en, zh） |
| custom_text | string | No | カスタムテキスト |
| include_affiliate_link | boolean | No | アフィリエイトリンクを含める |

**レスポンス:**

```json
{
  "success": true,
  "data": {
    "post_id": "p1q2r3s4t5u6v7w8",
    "platforms": ["x", "instagram", "threads"],
    "template": "dark_classic",
    "status": "queued",
    "estimated_completion": "30秒以内"
  },
  "message": "投稿ジョブをキューに追加しました"
}
```

### POST /schedules - 投稿スケジュールを設定

**リクエストボディ:**

```json
{
  "post_time": "07:00",
  "timezone": "Asia/Tokyo",
  "platforms": ["x", "instagram"],
  "template": "neon_glow",
  "enabled": true
}
```

### GET /trades - 取引履歴を取得

**クエリパラメータ:**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| start_date | string | 開始日（YYYY-MM-DD） |
| end_date | string | 終了日（YYYY-MM-DD） |
| page | integer | ページ番号（デフォルト: 1） |
| per_page | integer | 1ページあたりの件数（1-100、デフォルト: 20） |

### GET /trades/summary - 取引サマリー

**クエリパラメータ:**

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| period | string | daily, weekly, monthly |

---

## エラーレスポンス

すべてのエラーは以下の形式で返されます：

```json
{
  "detail": {
    "error": "error_code",
    "message": "エラーの説明"
  }
}
```

### エラーコード一覧

| HTTPステータス | エラーコード | 説明 |
|--------------|------------|------|
| 400 | bad_request | リクエストが不正 |
| 401 | invalid_api_key | APIキーが無効 |
| 403 | plan_limit_exceeded | プラン制限超過 |
| 404 | not_found | リソースが見つからない |
| 429 | rate_limit_exceeded | レート制限超過 |
| 500 | internal_error | サーバー内部エラー |

---

## SDKとサンプルコード

### Python

```python
import requests

API_KEY = "your_api_key"
BASE_URL = "https://api.tradepost-pro.com/api/v1"
headers = {"X-API-Key": API_KEY}

# 取引データ送信
response = requests.post(f"{BASE_URL}/trades", headers=headers, json={
    "date": "2026-03-11",
    "profit": 17000,
    "total_trades": 12,
    "wins": 8,
    "losses": 4,
})
print(response.json())

# SNS投稿
response = requests.post(f"{BASE_URL}/posts", headers=headers, json={
    "platforms": ["x", "instagram"],
    "template": "dark_classic",
})
print(response.json())
```

### cURL

```bash
# 取引データ送信
curl -X POST https://api.tradepost-pro.com/api/v1/trades \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-03-11","profit":17000,"total_trades":12,"wins":8,"losses":4}'

# APIステータス確認
curl https://api.tradepost-pro.com/api/v1/status
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

const client = axios.create({
  baseURL: 'https://api.tradepost-pro.com/api/v1',
  headers: { 'X-API-Key': 'your_api_key' }
});

// 取引データ送信
const res = await client.post('/trades', {
  date: '2026-03-11',
  profit: 17000,
  total_trades: 12,
  wins: 8,
  losses: 4,
});
console.log(res.data);
```

---

## Webhookイベント

Webhookを設定すると、以下のイベント発生時に指定URLへPOSTリクエストが送信されます。

| イベント | 説明 |
|---------|------|
| `post.completed` | 投稿が完了した |
| `post.failed` | 投稿が失敗した |
| `trade.received` | 取引データを受信した |
| `schedule.executed` | スケジュール投稿が実行された |
| `plan.changed` | プランが変更された |

詳細は「Webhook通知」セクションを参照してください。
