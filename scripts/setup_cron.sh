#!/bin/bash
# ============================================================
# XM Affiliate SNS Auto Poster - cron設定スクリプト
# ============================================================
# 毎朝7時（JST）に自動投稿を実行するcronジョブを設定します。
#
# 使い方:
#   chmod +x scripts/setup_cron.sh
#   ./scripts/setup_cron.sh
# ============================================================

set -e

# プロジェクトディレクトリ
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_PATH=$(which python3)
LOG_DIR="${PROJECT_DIR}/logs"

echo "============================================"
echo "  XM Affiliate SNS Auto Poster"
echo "  cron設定スクリプト"
echo "============================================"
echo ""
echo "プロジェクト: ${PROJECT_DIR}"
echo "Python: ${PYTHON_PATH}"
echo "ログ: ${LOG_DIR}"
echo ""

# ログディレクトリの作成
mkdir -p "${LOG_DIR}"

# cronジョブの内容
# 毎朝7:00 JST (UTC 22:00 前日) に実行
# ※サーバーのタイムゾーンがJSTの場合は "0 7 * * *"
# ※サーバーのタイムゾーンがUTCの場合は "0 22 * * *"

# サーバーのタイムゾーンを確認
TIMEZONE=$(timedatectl show --property=Timezone --value 2>/dev/null || echo "unknown")
echo "サーバーのタイムゾーン: ${TIMEZONE}"
echo ""

if [[ "$TIMEZONE" == "Asia/Tokyo" ]] || [[ "$TIMEZONE" == "JST" ]]; then
    CRON_SCHEDULE="0 7 * * *"
    echo "JST環境: 毎朝 7:00 JST に実行します"
else
    CRON_SCHEDULE="0 22 * * *"
    echo "UTC環境: 毎日 22:00 UTC (= 7:00 JST) に実行します"
fi

CRON_JOB="${CRON_SCHEDULE} cd ${PROJECT_DIR} && ${PYTHON_PATH} main.py >> ${LOG_DIR}/cron_\$(date +\%Y-\%m-\%d).log 2>&1"

echo ""
echo "設定するcronジョブ:"
echo "  ${CRON_JOB}"
echo ""

# 既存のcronジョブを確認
EXISTING_CRON=$(crontab -l 2>/dev/null || echo "")

# 既に同じジョブが存在するか確認
if echo "$EXISTING_CRON" | grep -q "xm-sns-auto-poster"; then
    echo "既存のcronジョブが見つかりました。更新します。"
    # 既存のジョブを削除
    NEW_CRON=$(echo "$EXISTING_CRON" | grep -v "xm-sns-auto-poster")
else
    NEW_CRON="$EXISTING_CRON"
fi

# 新しいcronジョブを追加
echo "${NEW_CRON}
# XM Affiliate SNS Auto Poster - 毎朝7時自動投稿
${CRON_JOB}" | crontab -

echo ""
echo "✓ cronジョブの設定が完了しました！"
echo ""
echo "確認:"
crontab -l | grep -A1 "xm-sns-auto-poster" || echo "(設定なし)"
echo ""
echo "============================================"
echo "  設定完了"
echo "============================================"
