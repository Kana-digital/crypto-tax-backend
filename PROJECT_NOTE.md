# 暗号資産税計算ツール プロジェクトメモ

## 概要
暗号資産（仮想通貨）の売買履歴CSVから譲渡損益を自動計算し、PDFレポートを出力するWebアプリ。

## 構成
| 役割 | 場所 | 起動 |
|------|------|------|
| バックエンド | `~/crypto-tax-backend/crypto-tax-backend/` | `python3.12 -m uvicorn main:app --reload` |
| フロントエンド | `~/crypto-tax-frontend/` | `npm run dev` |

**一括起動：** `~/crypto-tax-backend/start-all.sh`

## アクセス先
- フロントエンド: http://localhost:5173
- バックエンドAPI: http://localhost:8000
- APIドキュメント: http://localhost:8000/docs

## 対応取引所
- Coincheck
- SBI VC Trade
- bitbank

## 計算方法
- 総平均法
- 移動平均法

## APIエンドポイント
- `POST /calculate` → JSON形式で損益を返す
- `POST /calculate/pdf` → 損益計算書PDFをダウンロード

## ファイル構成
```
crypto-tax-backend/
├── start-all.sh              # 一括起動スクリプト
└── crypto-tax-backend/
    ├── main.py               # FastAPIメイン（PDF出力含む）
    ├── requirements.txt      # 必要パッケージ一覧
    ├── start.sh              # バックエンド単体起動
    ├── parsers/
    │   ├── coincheck.py
    │   ├── sbivc.py
    │   └── bitbank.py
    └── calculators/
        ├── total_average.py  # 総平均法
        └── moving_average.py # 移動平均法
```

## 今後やりたいこと（アイデア）
- [ ] 対応取引所を増やす（binance、GMOコインなど）
- [ ] 年ごとの損益サマリー表示
- [ ] 複数CSVの一括アップロード
- [ ] freee・確定申告ソフト連携

## 環境
- Python: 3.12（pyenv）
- フレームワーク: FastAPI + uvicorn
- PDF生成: reportlab
- フロントエンド: Vite（localhost:5173）
