@echo off
REM ============================================================
REM XM Affiliate SNS Auto Poster - Windows用実行バッチ
REM ============================================================
REM Windows VPS上でタスクスケジューラから実行するためのバッチファイルです。
REM
REM 【タスクスケジューラの設定手順】
REM 1. タスクスケジューラを開く
REM 2. 「基本タスクの作成」をクリック
REM 3. 名前: "XM SNS Auto Poster"
REM 4. トリガー: 毎日 7:00
REM 5. 操作: プログラムの開始
REM    - プログラム: このバッチファイルのフルパス
REM    - 開始: このバッチファイルのディレクトリ
REM ============================================================

echo ============================================
echo   XM Affiliate SNS Auto Poster
echo   %date% %time%
echo ============================================

REM プロジェクトディレクトリに移動
cd /d "%~dp0\.."

REM Python実行
python main.py

echo.
echo 実行完了: %date% %time%
pause
