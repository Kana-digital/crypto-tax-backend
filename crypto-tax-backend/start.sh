#!/bin/bash
# crypto-tax-backend 起動スクリプト

cd "$(dirname "$0")"

# 依存パッケージのインストール（初回のみ必要）
# pip3 install -r requirements.txt

echo "🚀 バックエンド起動中... http://localhost:8000"
uvicorn main:app --reload --host 0.0.0.0 --port 8000
