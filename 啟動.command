#!/bin/bash
# 簡化版啟動腳本 - 無檢查，直接啟動

cd "$(dirname "$0")"
echo "正在啟動大樂透選號系統..."
python3 lottery_gui.py
