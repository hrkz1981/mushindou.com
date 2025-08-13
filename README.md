# Sanity + Next.js ブログプロジェクト

このプロジェクトは、SanityをCMSとして使用し、Next.jsでフロントエンドを構築したブログおよびランディングページのシステムです。

## プロジェクト構成

```
.
└── my-blog-frontend/     # Next.js フロントエンド + Sanity Studio
    ├── src/
    │   ├── app/          # App Router
    │   └── lib/          # ユーティリティ
    ├── schemas/          # Sanity コンテンツスキーマ
    ├── sanity.config.ts  # Sanity設定
    └── package.json
```

## セットアップ手順

### 1. Sanity CLIでプロジェクトを初期化

1. [Sanity.io](https://sanity.io)でアカウントを作成し、ログイン
   ```bash
   sanity login
   ```

2. プロジェクトディレクトリで初期化
   ```bash
   cd my-blog-frontend
   sanity init
   ```
   - 既存のプロジェクトを選択するか、新しいプロジェクトを作成
   - プロジェクトIDがsanity.config.tsに自動的に設定されます

3. パッケージをインストール:
   ```bash
   npm install
   ```

### 2. 開発サーバーの起動

1. Sanity Studioを起動:
   ```bash
   npm run sanity:dev
   ```
   - ブラウザで http://localhost:3333 にアクセス

2. Next.jsフロントエンドを起動（別ターミナル）:
   ```bash
   npm run dev
   ```
   - ブラウザで http://localhost:3000 にアクセス

## 利用可能なスキーマ

### ブログ関連
- **Post** (`post`): ブログ記事
- **Author** (`author`): 著者情報
- **Category** (`category`): カテゴリー
- **Block Content** (`blockContent`): リッチテキストコンテンツ

### ランディングページ関連
- **Landing Page** (`landingPage`): ランディングページ
- **Hero** (`hero`): ヒーローセクション
- **Features** (`features`): 機能紹介セクション

## 機能

### ブログ機能
- ブログ記事の作成・編集
- 著者管理
- カテゴリー分類
- SEO設定
- 画像管理

### ランディングページ機能
- ヒーローセクション
- 機能紹介セクション
- お客様の声
- CTA（コール・トゥ・アクション）
- SEO設定

## アクセス先

- **Sanity Studio**: http://localhost:3333 (デフォルト)
- **Next.js フロントエンド**: http://localhost:3000

## 次のステップ

1. Sanity Studioでコンテンツを作成
2. フロントエンドでコンテンツを確認
3. デザインのカスタマイズ
4. デプロイの設定

## 注意事項

- 現在、npmのキャッシュ問題により一部のパッケージのインストールが制限されています
- プロジェクトIDは実際のSanityプロジェクトIDに変更する必要があります
- 本番環境への適用前に、適切なセキュリティ設定を行ってください