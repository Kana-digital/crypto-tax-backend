#!/bin/bash
# crypto-tax 一括起動スクリプト

echo "🚀 バックエンド起動中..."
cd "$(dirname "$0")/crypto-tax-backend"
lsof -ti:8000 | xargs kill -9 2>/dev/null
python3.12 -m uvicorn main:app --reload &
BACKEND_PID=$!

echo "🎨 フロントエンド起動中..."
cd ~/crypto-tax-frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "✅ 起動完了！"
echo "   フロントエンド: http://localhost:5173"
echo "   バックエンド:   http://localhost:8000"
echo ""
echo "終了するには Ctrl+C を押してください"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '停止しました'" INT
wait
