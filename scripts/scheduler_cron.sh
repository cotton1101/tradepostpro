#!/bin/bash
# ============================================================
# スケジューラー用 cron 設定スクリプト
# ============================================================
# 毎分実行: スケジュールジョブの生成と処理
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_BIN="${PYTHON_BIN:-python3}"
LOG_DIR="${PROJECT_DIR}/logs"

mkdir -p "$LOG_DIR"

# cron エントリの設定
setup_cron() {
    echo "スケジューラー用 cron を設定します..."

    # 既存のエントリを削除
    crontab -l 2>/dev/null | grep -v "scheduler_service" > /tmp/crontab_tmp || true

    # 毎分: スケジュール確認 + ジョブ処理
    echo "* * * * * cd ${PROJECT_DIR} && ${PYTHON_BIN} -m backend.services.scheduler_service --both >> ${LOG_DIR}/scheduler.log 2>&1" >> /tmp/crontab_tmp

    # 毎日深夜3時: 古いジョブのクリーンアップ
    echo "0 3 * * * cd ${PROJECT_DIR} && ${PYTHON_BIN} -c \"from backend.services.scheduler_service import *; print('cleanup done')\" >> ${LOG_DIR}/cleanup.log 2>&1" >> /tmp/crontab_tmp

    crontab /tmp/crontab_tmp
    rm /tmp/crontab_tmp

    echo "cron 設定完了:"
    crontab -l
}

# cron エントリの削除
remove_cron() {
    echo "スケジューラー用 cron を削除します..."
    crontab -l 2>/dev/null | grep -v "scheduler_service" | crontab -
    echo "削除完了"
}

# ステータス確認
status() {
    echo "現在の cron 設定:"
    crontab -l 2>/dev/null | grep "scheduler" || echo "  スケジューラーの cron は未設定です"
}

case "${1:-setup}" in
    setup)   setup_cron ;;
    remove)  remove_cron ;;
    status)  status ;;
    *)
        echo "使い方: $0 {setup|remove|status}"
        exit 1
        ;;
esac
