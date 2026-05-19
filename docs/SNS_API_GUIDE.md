# TradePost Pro - 各種SNS API申請ガイド

このドキュメントは、TradePost Proで自動投稿を行うために必要な、各SNSのAPIキー取得手順をまとめたものです。

---

## 1. X (Twitter) API 申請手順

Xの自動投稿には「X Developer Portal」でのアプリ作成とAPIキー取得が必要です。

### 1.1 必要なもの
- 電話番号認証済みのXアカウント
- 開発者アカウント（無料枠の「Free」プランで可）

### 1.2 取得手順
1. [X Developer Portal](https://developer.twitter.com/en/portal/dashboard) にアクセスし、ログインします。
2. 左メニューの「Projects & Apps」から「Add Project」をクリックします。
3. プロジェクト名（例: TradePostPro）を入力し、ユースケースとして「Making a bot」を選択します。
4. 「App setup」でアプリ名（例: TradePost_AutoPoster）を入力します。
5. 作成完了後、以下のキーが表示されるので**必ずメモ**してください。
   - `API Key` (Consumer Key)
   - `API Key Secret` (Consumer Secret)
   - `Bearer Token`
6. アプリ設定画面に戻り、「User authentication settings」の「Set up」をクリックします。
7. 「App permissions」で「Read and write」を選択します。
8. 「Type of App」で「Web App, Automated App or Bot」を選択します。
9. 「App info」のCallback URIとWebsite URLに、自身のサイトURL（例: `https://your-domain.com`）を入力して保存します。
10. 「Keys and tokens」タブに戻り、「Authentication Tokens」の「Generate」をクリックします。
11. 以下のキーが表示されるので**必ずメモ**してください。
    - `Access Token`
    - `Access Token Secret`

### 1.3 .envへの設定
```env
X_API_KEY=取得したAPI_KEY
X_API_SECRET=取得したAPI_SECRET
X_ACCESS_TOKEN=取得したACCESS_TOKEN
X_ACCESS_SECRET=取得したACCESS_SECRET
```

---

## 2. Instagram Graph API 申請手順

Instagramへの自動投稿には、Facebook開発者アカウントとInstagramプロアカウントが必要です。

### 2.1 必要なもの
- Facebookアカウント
- Instagramプロアカウント（ビジネスまたはクリエイター）
- Facebookページ（Instagramアカウントと連携済みのもの）

### 2.2 取得手順
1. [Meta for Developers](https://developers.facebook.com/) にアクセスし、ログインして「マイアプリ」を開きます。
2. 「アプリを作成」をクリックし、「ビジネス」または「その他」を選択します。
3. アプリ名と連絡先メールアドレスを入力して作成します。
4. ダッシュボードから「Instagram Graph API」を見つけて「設定」をクリックします。
5. 「Facebookログイン」も同様に設定します。
6. 「ツール」→「グラフAPIエクスプローラ」を開きます。
7. 「Facebookアプリ」で作成したアプリを選択します。
8. 「ユーザーまたはページ」で「ページアクセストークンを取得」を選択し、連携したFacebookページを選びます。
9. 以下の権限（Permissions）を追加します：
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_show_list`
   - `pages_read_engagement`
10. 「Generate Access Token」をクリックし、表示されたトークンをコピーします。
11. [アクセストークンデバッガー](https://developers.facebook.com/tools/debug/accesstoken/)でトークンを延長（無期限化）します。
12. InstagramアカウントID（IG User ID）を取得します（API経由で取得するか、外部ツールを使用）。

### 2.3 .envへの設定
```env
INSTAGRAM_ACCESS_TOKEN=取得した無期限アクセストークン
INSTAGRAM_ACCOUNT_ID=取得したInstagramアカウントID
```

---

## 3. Threads API 申請手順

Threads APIはInstagram Graph APIと同じ基盤を使用しますが、別途設定が必要です。

### 3.1 必要なもの
- Instagramアカウント（Threadsアプリにログイン済み）
- Meta開発者アカウント

### 3.2 取得手順
1. [Meta for Developers](https://developers.facebook.com/) でアプリを作成します（Instagram APIと同じアプリで可）。
2. ダッシュボードから「Threads API」を見つけて「設定」をクリックします。
3. アプリのダッシュボードで「Threads」の設定を開き、リダイレクトURIを設定します。
4. 「ツール」→「グラフAPIエクスプローラ」を開きます。
5. 以下の権限（Permissions）を追加します：
   - `threads_basic`
   - `threads_content_publish`
6. トークンを生成し、デバッガーで無期限化します。
7. ThreadsアカウントIDを取得します。

### 3.3 .envへの設定
```env
THREADS_ACCESS_TOKEN=取得した無期限アクセストークン
THREADS_ACCOUNT_ID=取得したThreadsアカウントID
```

---

## 4. TikTok Content Posting API 申請手順

TikTokへの動画/画像投稿にはTikTok for Developersでの登録が必要です。

### 4.1 必要なもの
- TikTokアカウント
- TikTok for Developersアカウント

### 4.2 取得手順
1. [TikTok for Developers](https://developers.tiktok.com/) にアクセスし、ログインします。
2. 「Manage Apps」から「Create an App」をクリックします。
3. アプリ情報を入力し、「Web」プラットフォームを選択します。
4. 「Products」で「Content Posting API」を追加します。
5. 審査に提出します（通常1〜3営業日かかります）。
6. 審査通過後、Client KeyとClient Secretが発行されます。
7. ユーザーにOAuth認証を行わせ、Access TokenとOpenIDを取得します。
   （※TradePost Proでは、管理画面からユーザー自身に認証を行わせるフローが実装されています）

### 4.3 .envへの設定（システム用）
```env
TIKTOK_CLIENT_KEY=取得したClient_Key
TIKTOK_CLIENT_SECRET=取得したClient_Secret
```

---

## 5. LINE Messaging API (オープンチャット) 申請手順

LINEオープンチャットへの自動投稿は、LINE NotifyまたはMessaging APIを使用します。
※公式のオープンチャットAPIは制限が厳しいため、通常はLINE Notifyを使用します。

### 5.1 必要なもの
- LINEアカウント

### 5.2 LINE Notifyの取得手順（推奨）
1. [LINE Notify](https://notify-bot.line.me/ja/) にアクセスし、ログインします。
2. 右上のユーザー名から「マイページ」を開きます。
3. 「トークンを発行する」をクリックします。
4. トークン名（例: TradePost）を入力し、通知を送信したいオープンチャット（またはグループ）を選択します。
5. 「発行する」をクリックし、表示されたトークンを**必ずメモ**します。
6. LINEアプリを開き、対象のオープンチャット（またはグループ）に「LINE Notify」アカウントを招待します。

### 5.3 .envへの設定
```env
LINE_NOTIFY_TOKEN=取得したトークン
```
