# TradePost Pro - Makefile
# Docker操作の便利コマンド集

.PHONY: help build up down restart logs status clean

# デフォルト
help: ## ヘルプを表示
	@echo "TradePost Pro - Docker管理コマンド"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ============================================================
# 開発環境
# ============================================================
build: ## イメージをビルド
	docker compose build

up: ## 開発環境を起動
	docker compose up -d
	@echo "✓ 開発環境が起動しました"
	@echo "  ダッシュボード: http://localhost"
	@echo "  API: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

down: ## 環境を停止
	docker compose down

restart: ## 環境を再起動
	docker compose restart

logs: ## ログを表示
	docker compose logs -f --tail=100

logs-backend: ## バックエンドログを表示
	docker compose logs -f backend

logs-dashboard: ## ダッシュボードログを表示
	docker compose logs -f dashboard

logs-scheduler: ## スケジューラーログを表示
	docker compose logs -f scheduler

status: ## コンテナ状態を確認
	docker compose ps

# ============================================================
# 本番環境
# ============================================================
prod-up: ## 本番環境を起動（Nginx SSL含む）
	docker compose --profile production up -d
	@echo "✓ 本番環境が起動しました"

prod-down: ## 本番環境を停止
	docker compose --profile production down

# ============================================================
# データベース
# ============================================================
db-shell: ## MySQLシェルに接続
	docker compose exec db mysql -u tradepost -p tradepost

db-backup: ## データベースバックアップ
	@mkdir -p backups
	docker compose exec db mysqldump -u root -p$${DB_ROOT_PASSWORD:-rootpassword} tradepost > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ バックアップ完了"

db-restore: ## データベースリストア (FILE=backups/xxx.sql)
	docker compose exec -T db mysql -u root -p$${DB_ROOT_PASSWORD:-rootpassword} tradepost < $(FILE)
	@echo "✓ リストア完了"

# ============================================================
# テスト
# ============================================================
test: ## テストを実行
	docker compose exec backend python3 -m pytest tests/ -v

test-dry-run: ## ドライランテスト
	docker compose exec backend python3 main.py --sample --dry-run

# ============================================================
# メンテナンス
# ============================================================
clean: ## 未使用リソースを削除
	docker compose down -v --remove-orphans
	docker system prune -f

shell-backend: ## バックエンドのシェルに入る
	docker compose exec backend /bin/bash

shell-dashboard: ## ダッシュボードのシェルに入る
	docker compose exec dashboard /bin/bash

update: ## アプリケーションを更新
	git pull
	docker compose build
	docker compose up -d
	@echo "✓ 更新完了"
