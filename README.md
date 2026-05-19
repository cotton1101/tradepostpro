# tradepostpro - FX実績連動マルチSNS自動投稿ツール

> XMアフィリエイトの毎日の取引結果（MT4/MT5）を自動取得し、損益レポート画像を生成して
> X / Threads / Instagram / TikTok / LINE オープンチャットへ全自動投稿する
> Cotton-Web の自社開発ツールです。

## ✨ 主な機能

- **MT4/MT5 データ連携** — MT5 Python API または MT4 EA（MQL4）からの CSV 出力を自動取得
- **画像自動生成** — Pillow + カスタムテンプレートで、ダークテーマの美しい損益レポート画像を生成
- **マルチSNS投稿** — X(Twitter) / Instagram / Threads / TikTok / LINE オープンチャットに一括配信
- **AI連携** — 投稿文の自動生成（Claude API / OpenAI API 対応）
- **多言語対応** — i18n モジュール組み込み
- **動画レポート生成** — moviepy で動画化（YouTube/TikTok対応）
- **管理ダッシュボード** — FastAPI + GraphQL ベースの API、認証・課金・監査ログ対応
- **自動実行** — cron / Windows タスクスケジューラで毎日の自動投稿

## 🛠️ 技術スタック

### バックエンド
- **Python 3.11+**
- **FastAPI** + **Uvicorn / Gunicorn**
- **SQLAlchemy** + **MySQL (PyMySQL)**
- **GraphQL**（Strawberry）

### 認証・課金
- **PyJWT** + **python-jose** + **passlib (bcrypt)**
- **TOTP / 2FA**（pyotp）
- **Stripe**（決済）

### 画像・動画生成
- **Pillow**（画像）
- **moviepy** + **FFmpeg**（動画）
- **fpdf2**（PDF レポート）

### SNS連携
- **tweepy**（X / Twitter）
- **line-bot-sdk**（LINE）
- **Instagram Graph API** / **Threads API** / **TikTok API**

### インフラ
- **Docker** + **docker-compose**
- **Nginx** リバースプロキシ
- **AWS / VPS** 上で稼働中

## 🚀 セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/cotton1101/tradepostpro.git
cd tradepostpro

# 依存パッケージのインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .env を編集し、各SNSのAPIキー / MT5ログイン情報 / DB接続情報 を設定
```

## 🐳 Docker での起動

```bash
make up        # 開発環境を起動
make logs      # ログ確認
make down      # 停止
```

起動後：
- ダッシュボード: `http://localhost`
- API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

## 📌 使い方（CLI）

### 通常実行（全SNSに投稿）
```bash
python main.py
```

### ドライラン（実投稿せずテスト）
```bash
python main.py --dry-run
```

### 特定のSNSのみに投稿
```bash
python main.py --platforms x line
```

### サンプルデータでテスト
```bash
python main.py --sample --dry-run
```

### MT4 モードで実行（CSVから読み込み）
```bash
python main.py --mt4
```

## ⏰ 自動実行の設定

### Linux (VPS) の場合（cron）

```bash
chmod +x scripts/setup_cron.sh
./scripts/setup_cron.sh
```

### Windows (VPS) の場合（タスクスケジューラ）

1. Windowsの「タスクスケジューラ」を開く
2. 「基本タスクの作成」をクリック
3. トリガーを「毎日 7:00」に設定
4. 操作を「プログラムの開始」にし、`scripts/run_daily.bat` を指定

## 🔧 MT4 連携の設定

1. `mt4_ea/DailyTradeExporter.mq4` を MT4 の `MQL4/Experts/` フォルダにコピー
2. MT4 上でコンパイルし、任意のチャートにアタッチ
3. EA のパラメータで出力時刻（サーバー時間）を設定
4. `.env` の `MT4_CSV_DIR` に、MT4 の `MQL4/Files/` フォルダのパスを設定

## ⚠️ 注意事項

- Instagram / Threads / TikTok / LINE への画像投稿には、画像が **インターネット上で公開アクセス可能（HTTPS）** である必要があります
- 各SNS API のレート制限に注意
- 投稿頻度や内容は各プラットフォームの利用規約を遵守すること
- 金融商品（FX）に関する発信は、各国の法規制に注意

## 🌐 運用

このツールは Cotton-Web で本番運用中です：
**https://sns-tool.online/tradepostpro/**

「FX実績を自動で SNS にレポート発信したい」という課題感から自社開発。
「外部APIデータ → AI整形 → マルチSNSへ自動配信」というパターンの実装例として、
売上・株価・KPI などあらゆる外部データを発信したい案件にそのまま応用できます。

## 📝 ライセンス

MIT License

## 👤 作者

**Cotton-Web（山田 英紀 / Hi）**

業務システム制作 × SNS自動化 × AI連携 を一人で完結するエンジニアです。

- 自社サイト: [https://sns-tool.online](https://sns-tool.online)
- 連絡先: yamada@sns-tool.online

### 関連プロダクト

- [posutto](https://github.com/cotton1101/posutto) - マルチSNS自動投稿ツール
- [tubetto](https://github.com/cotton1101/tubetto) - YouTube動画自動生成・公開ツール
- [keiri](https://github.com/cotton1101/keiri) - 個人事業主向け経理ソフト

---

SNS自動化・AI連携プロダクト・業務システム制作のご相談は yamada@sns-tool.online までお気軽にどうぞ。
