# 暗号資産損益計算ツール - 開発メモ

## サービス構成

| サービス | 用途 | URL |
|---|---|---|
| Vercel | フロントエンド（自動デプロイ） | https://crypto-tax-frontend.vercel.app |
| Render | バックエンド（FastAPI） | https://crypto-tax-backend.onrender.com |
| Supabase | データベース・ストレージ | https://supabase.com/dashboard/project/zipalomsrwilometryst |
| GitHub | ソースコード管理 | https://github.com/Kana-digital |

---

## ログイン方法

- **Supabase / Render / Vercel** → すべて GitHub アカウント（`Kana-digital`）でログイン
- **Anthropic Platform**（APIキー管理）→ https://platform.claude.com

---

## 環境変数（Render に設定済み）

| 変数名 | 説明 |
|---|---|
| `ANTHROPIC_API_KEY` | Claude Haiku 用 APIキー（Anthropic Platform で取得） |
| `SUPABASE_URL` | `https://zipalomsrwilometryst.supabase.co` |
| `SUPABASE_ANON_KEY` | Supabase の anon キー（ダッシュボード → Project Settings → API で確認） |

---

## Supabase 構成

### テーブル: `exchange_requests`

```sql
create table exchange_requests (
  id uuid default gen_random_uuid() primary key,
  exchange_name text not null,
  email text not null,
  csv_path text,               -- Supabase Storage 内のパス（任意）
  created_at timestamptz default now(),
  unique(exchange_name, email) -- 同一メールからの重複投票を防止
);
```

### Storage バケット: `exchange-csvs`

- 非公開バケット（`public: false`）
- ユーザーがリクエスト時に添付した取引履歴CSVが保存される
- ファイルパス形式：`{取引所名}/{uuid}.csv`
- **確認方法**：Supabase ダッシュボード → Storage → exchange-csvs

---

## 実装済み機能

### 1. 損益計算（コア機能）
- CSVアップロード → 取引データ解析 → 損益計算
- 対応計算方法：総平均法・移動平均法
- 対応取引所：Coincheck・SBI VC Trade・bitbank
- PDF出力、CSV出力に対応

### 2. AIサポートチャット
- 画面右下の 💬 ボタンから起動
- Claude Haiku（`claude-haiku-4-5-20251001`）が対応
- バックエンドエンドポイント：`POST /chat`

### 3. 取引所リクエスト機能
- ユーザーが希望取引所をリクエストできる
- 同じ取引所に3人リクエストしたら「実装予定」フラグが立つ
- CSVを添付してもらうことで実装時にフォーマット確認が可能
- バックエンドエンドポイント：`POST /request-exchange`、`GET /exchange-requests`

### 4. アフィリエイト表示（広告対応）
- 景品表示法ステルスマーケティング規制（2023年）に対応
- 「広告（PR）」バッジと開示文を表示
- 対応予定取引所：Coincheck（AccessTrade）・bitbank（AccessTrade）・SBI VC Trade（A8.net）
  - ※アフィリエイト審査承認後、`App.tsx` 内の `COINCHECK_AFFILIATE_URL` 等を実際のURLに差し替え

---

## アフィリエイトURL差し替え手順

`crypto-tax-frontend/src/App.tsx` 内の以下3箇所を差し替える：

```
COINCHECK_AFFILIATE_URL  → AccessTrade で発行したURL
BITBANK_AFFILIATE_URL    → AccessTrade で発行したURL
SBIVC_AFFILIATE_URL      → A8.net で発行したURL
```

---

## バックエンド構成（main.py）

```
/calculate        POST  CSVアップロード → 損益計算
/calculate/pdf    POST  CSVアップロード → PDF出力
/chat             POST  AIサポートチャット
/request-exchange POST  取引所リクエスト（CSV添付可）
/exchange-requests GET  リクエスト一覧・集計
```

---

## デプロイフロー

1. コードを編集
2. `git push origin main`
3. Render（バックエンド）と Vercel（フロントエンド）が自動でビルド・デプロイ

---

## セキュリティ対応済み

- アップロードCSVの一時ファイルを `finally` ブロックで確実に削除
- CORS を `*.vercel.app` と `*.onrender.com` に限定
- Supabase の `exchange-csvs` バケットは非公開（service_role のみ読み取り可）
