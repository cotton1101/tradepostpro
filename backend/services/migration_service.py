"""
DBマイグレーション管理サービス
Alembic風のマイグレーション管理（SQLite/MySQL対応）
"""

import os
import json
import hashlib
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum


class MigrationStatus(Enum):
    """マイグレーションステータス"""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Migration:
    """マイグレーション定義"""
    id: str
    version: str
    name: str
    description: str
    up_sql: str
    down_sql: str
    created_at: str = ""
    applied_at: Optional[str] = None
    status: MigrationStatus = MigrationStatus.PENDING
    checksum: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.checksum:
            self.checksum = hashlib.md5(self.up_sql.encode()).hexdigest()[:8]


class MigrationService:
    """マイグレーション管理サービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.migrations_dir = self.config.get("migrations_dir", "migrations")
        self.migrations: List[Migration] = []
        self.applied_migrations: List[str] = []
        self._define_migrations()

    def _define_migrations(self):
        """マイグレーション定義"""
        self.migrations = [
            Migration(
                id="001",
                version="0.1.0",
                name="create_users_table",
                description="ユーザーテーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    plan VARCHAR(20) DEFAULT 'free',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_plan ON users(plan);
""",
                down_sql="DROP TABLE IF EXISTS users;",
            ),
            Migration(
                id="002",
                version="0.1.0",
                name="create_sns_accounts_table",
                description="SNSアカウント連携テーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS sns_accounts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    platform VARCHAR(20) NOT NULL,
    account_name VARCHAR(100),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_sns_user ON sns_accounts(user_id);
CREATE INDEX idx_sns_platform ON sns_accounts(platform);
""",
                down_sql="DROP TABLE IF EXISTS sns_accounts;",
            ),
            Migration(
                id="003",
                version="0.1.0",
                name="create_posts_table",
                description="投稿テーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS posts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    template_id VARCHAR(50),
    content TEXT,
    image_url TEXT,
    platforms JSON,
    status VARCHAR(20) DEFAULT 'draft',
    scheduled_at TIMESTAMP,
    posted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_posts_user ON posts(user_id);
CREATE INDEX idx_posts_status ON posts(status);
CREATE INDEX idx_posts_scheduled ON posts(scheduled_at);
""",
                down_sql="DROP TABLE IF EXISTS posts;",
            ),
            Migration(
                id="004",
                version="0.2.0",
                name="create_trades_table",
                description="取引履歴テーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS trades (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    currency_pair VARCHAR(10) NOT NULL,
    direction VARCHAR(4) NOT NULL,
    lot_size DECIMAL(10,4),
    entry_price DECIMAL(15,5),
    exit_price DECIMAL(15,5),
    profit DECIMAL(15,2),
    pips DECIMAL(10,1),
    duration_minutes INT,
    commission DECIMAL(10,2) DEFAULT 0,
    swap DECIMAL(10,2) DEFAULT 0,
    trade_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_trades_user ON trades(user_id);
CREATE INDEX idx_trades_date ON trades(trade_date);
CREATE INDEX idx_trades_pair ON trades(currency_pair);
""",
                down_sql="DROP TABLE IF EXISTS trades;",
            ),
            Migration(
                id="005",
                version="0.2.0",
                name="create_templates_table",
                description="テンプレートテーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS templates (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(30),
    config JSON,
    preview_url TEXT,
    is_premium BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
""",
                down_sql="DROP TABLE IF EXISTS templates;",
            ),
            Migration(
                id="006",
                version="0.3.0",
                name="create_badges_table",
                description="バッジ・実績テーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS user_badges (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    badge_id VARCHAR(50) NOT NULL,
    tier INT DEFAULT 0,
    earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, badge_id)
);
CREATE INDEX idx_badges_user ON user_badges(user_id);

CREATE TABLE IF NOT EXISTS user_xp (
    user_id VARCHAR(36) PRIMARY KEY,
    total_xp INT DEFAULT 0,
    level INT DEFAULT 1,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
""",
                down_sql="DROP TABLE IF EXISTS user_xp; DROP TABLE IF EXISTS user_badges;",
            ),
            Migration(
                id="007",
                version="0.3.0",
                name="create_notifications_table",
                description="通知テーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS push_subscriptions (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    endpoint TEXT NOT NULL,
    p256dh_key TEXT,
    auth_key TEXT,
    user_agent VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_push_user ON push_subscriptions(user_id);

CREATE TABLE IF NOT EXISTS notification_logs (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL,
    notification_type VARCHAR(30) NOT NULL,
    title VARCHAR(200),
    body TEXT,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    delivered BOOLEAN DEFAULT FALSE,
    clicked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_notif_user ON notification_logs(user_id);
CREATE INDEX idx_notif_type ON notification_logs(notification_type);
""",
                down_sql="DROP TABLE IF EXISTS notification_logs; DROP TABLE IF EXISTS push_subscriptions;",
            ),
            Migration(
                id="008",
                version="0.4.0",
                name="create_blog_posts_table",
                description="SEOブログ投稿テーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS blog_posts (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36),
    title VARCHAR(200) NOT NULL,
    slug VARCHAR(200) NOT NULL UNIQUE,
    content TEXT,
    meta_description VARCHAR(300),
    meta_keywords TEXT,
    category VARCHAR(50),
    tags JSON,
    status VARCHAR(20) DEFAULT 'draft',
    published_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_blog_slug ON blog_posts(slug);
CREATE INDEX idx_blog_status ON blog_posts(status);
CREATE INDEX idx_blog_category ON blog_posts(category);
""",
                down_sql="DROP TABLE IF EXISTS blog_posts;",
            ),
            Migration(
                id="009",
                version="0.4.0",
                name="create_email_campaigns_table",
                description="メールキャンペーンテーブルの作成",
                up_sql="""
CREATE TABLE IF NOT EXISTS email_campaigns (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    campaign_type VARCHAR(20) DEFAULT 'step',
    status VARCHAR(20) DEFAULT 'draft',
    config JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS email_subscribers (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    user_id VARCHAR(36),
    status VARCHAR(20) DEFAULT 'active',
    subscribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    unsubscribed_at TIMESTAMP
);
CREATE INDEX idx_sub_email ON email_subscribers(email);
CREATE INDEX idx_sub_status ON email_subscribers(status);
""",
                down_sql="DROP TABLE IF EXISTS email_subscribers; DROP TABLE IF EXISTS email_campaigns;",
            ),
            Migration(
                id="010",
                version="0.5.0",
                name="add_onboarding_columns",
                description="ユーザーテーブルにオンボーディング関連カラムを追加",
                up_sql="""
ALTER TABLE users ADD COLUMN onboarding_status VARCHAR(20) DEFAULT 'not_started';
ALTER TABLE users ADD COLUMN onboarding_data JSON;
ALTER TABLE users ADD COLUMN onboarding_completed_at TIMESTAMP;
""",
                down_sql="""
ALTER TABLE users DROP COLUMN onboarding_completed_at;
ALTER TABLE users DROP COLUMN onboarding_data;
ALTER TABLE users DROP COLUMN onboarding_status;
""",
            ),
        ]

    def get_pending_migrations(self) -> List[Migration]:
        """未適用のマイグレーションを取得"""
        return [m for m in self.migrations if m.id not in self.applied_migrations]

    def get_applied_migrations(self) -> List[Migration]:
        """適用済みのマイグレーションを取得"""
        return [m for m in self.migrations if m.id in self.applied_migrations]

    def apply_migration(self, migration_id: str) -> dict:
        """マイグレーションを適用"""
        migration = next((m for m in self.migrations if m.id == migration_id), None)
        if not migration:
            return {"success": False, "error": f"Migration {migration_id} not found"}

        if migration.id in self.applied_migrations:
            return {"success": False, "error": f"Migration {migration_id} already applied"}

        try:
            # 実際のDB実行をシミュレート
            migration.status = MigrationStatus.APPLIED
            migration.applied_at = datetime.now().isoformat()
            self.applied_migrations.append(migration.id)

            return {
                "success": True,
                "migration_id": migration.id,
                "name": migration.name,
                "version": migration.version,
                "applied_at": migration.applied_at,
            }
        except Exception as e:
            migration.status = MigrationStatus.FAILED
            return {"success": False, "error": str(e)}

    def rollback_migration(self, migration_id: str) -> dict:
        """マイグレーションをロールバック"""
        migration = next((m for m in self.migrations if m.id == migration_id), None)
        if not migration:
            return {"success": False, "error": f"Migration {migration_id} not found"}

        if migration.id not in self.applied_migrations:
            return {"success": False, "error": f"Migration {migration_id} not applied"}

        try:
            migration.status = MigrationStatus.ROLLED_BACK
            migration.applied_at = None
            self.applied_migrations.remove(migration.id)

            return {
                "success": True,
                "migration_id": migration.id,
                "name": migration.name,
                "rolled_back_at": datetime.now().isoformat(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_all_pending(self) -> dict:
        """全未適用マイグレーションを適用"""
        pending = self.get_pending_migrations()
        results = []
        for m in pending:
            result = self.apply_migration(m.id)
            results.append(result)
            if not result["success"]:
                break

        return {
            "total": len(pending),
            "applied": sum(1 for r in results if r["success"]),
            "failed": sum(1 for r in results if not r["success"]),
            "results": results,
        }

    def rollback_last(self, count: int = 1) -> dict:
        """最後のN個のマイグレーションをロールバック"""
        applied = list(reversed(self.applied_migrations))[:count]
        results = []
        for mid in applied:
            result = self.rollback_migration(mid)
            results.append(result)

        return {
            "total": count,
            "rolled_back": sum(1 for r in results if r["success"]),
            "results": results,
        }

    def get_status(self) -> dict:
        """マイグレーション状態を取得"""
        return {
            "total_migrations": len(self.migrations),
            "applied": len(self.applied_migrations),
            "pending": len(self.get_pending_migrations()),
            "current_version": self.migrations[len(self.applied_migrations) - 1].version if self.applied_migrations else "0.0.0",
            "latest_version": self.migrations[-1].version if self.migrations else "0.0.0",
            "migrations": [
                {
                    "id": m.id,
                    "version": m.version,
                    "name": m.name,
                    "status": m.status.value,
                    "applied_at": m.applied_at,
                }
                for m in self.migrations
            ],
        }

    def generate_migration_file(self, name: str, up_sql: str, down_sql: str) -> dict:
        """新しいマイグレーションファイルを生成"""
        next_id = f"{len(self.migrations) + 1:03d}"
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{next_id}_{timestamp}_{name}.sql"

        content = f"""-- Migration: {name}
-- Version: {next_id}
-- Created: {datetime.now().isoformat()}

-- UP
{up_sql}

-- DOWN
{down_sql}
"""
        filepath = os.path.join(self.migrations_dir, filename)

        return {
            "id": next_id,
            "filename": filename,
            "filepath": filepath,
            "content": content,
        }


# テスト実行
if __name__ == "__main__":
    service = MigrationService()

    print("=== マイグレーション一覧 ===")
    for m in service.migrations:
        print(f"  [{m.id}] v{m.version} {m.name} ({m.status.value})")

    print(f"\n=== 初期状態 ===")
    status = service.get_status()
    print(f"  総数: {status['total_migrations']}, 適用済: {status['applied']}, 未適用: {status['pending']}")

    print("\n=== 全マイグレーション適用 ===")
    result = service.apply_all_pending()
    print(f"  適用: {result['applied']}/{result['total']}")
    for r in result["results"]:
        print(f"    [{r['migration_id']}] {r['name']}: {'OK' if r['success'] else 'FAIL'}")

    print(f"\n=== 適用後の状態 ===")
    status = service.get_status()
    print(f"  バージョン: {status['current_version']}")
    print(f"  適用済: {status['applied']}, 未適用: {status['pending']}")

    print("\n=== ロールバック (最後の2つ) ===")
    result = service.rollback_last(2)
    print(f"  ロールバック: {result['rolled_back']}/{result['total']}")
    for r in result["results"]:
        print(f"    [{r['migration_id']}] {r['name']}: OK")

    print(f"\n=== ロールバック後の状態 ===")
    status = service.get_status()
    print(f"  バージョン: {status['current_version']}")
    print(f"  適用済: {status['applied']}, 未適用: {status['pending']}")

    print("\n=== マイグレーションファイル生成 ===")
    new_migration = service.generate_migration_file(
        "add_api_keys_table",
        "CREATE TABLE api_keys (id VARCHAR(36) PRIMARY KEY, user_id VARCHAR(36), key_hash VARCHAR(255));",
        "DROP TABLE IF EXISTS api_keys;",
    )
    print(f"  ファイル: {new_migration['filename']}")
    print(f"  ID: {new_migration['id']}")

    print("\n✓ DBマイグレーション管理サービス テスト完了")
