"""
TradePost Pro - ステータスページ
サービスの稼働状況を公開するページ
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import random


class ServiceStatus(str, Enum):
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    PARTIAL_OUTAGE = "partial_outage"
    MAJOR_OUTAGE = "major_outage"
    MAINTENANCE = "maintenance"


class IncidentSeverity(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


STATUS_LABELS = {
    ServiceStatus.OPERATIONAL.value: {"ja": "正常稼働", "en": "Operational", "color": "#10B981"},
    ServiceStatus.DEGRADED.value: {"ja": "パフォーマンス低下", "en": "Degraded Performance", "color": "#F59E0B"},
    ServiceStatus.PARTIAL_OUTAGE.value: {"ja": "一部障害", "en": "Partial Outage", "color": "#F97316"},
    ServiceStatus.MAJOR_OUTAGE.value: {"ja": "重大障害", "en": "Major Outage", "color": "#EF4444"},
    ServiceStatus.MAINTENANCE.value: {"ja": "メンテナンス中", "en": "Under Maintenance", "color": "#6366F1"},
}


@dataclass
class ServiceComponent:
    """サービスコンポーネント"""
    id: str = ""
    name: str = ""
    description: str = ""
    status: str = ServiceStatus.OPERATIONAL.value
    group: str = ""
    uptime_30d: float = 99.9


@dataclass
class Incident:
    """インシデント"""
    id: str = ""
    title: str = ""
    severity: str = ""
    status: str = "investigating"  # investigating, identified, monitoring, resolved
    affected_components: List[str] = field(default_factory=list)
    updates: List[Dict] = field(default_factory=list)
    created_at: str = ""
    resolved_at: str = ""


@dataclass
class MaintenanceWindow:
    """メンテナンスウィンドウ"""
    id: str = ""
    title: str = ""
    description: str = ""
    affected_components: List[str] = field(default_factory=list)
    scheduled_start: str = ""
    scheduled_end: str = ""
    status: str = "scheduled"  # scheduled, in_progress, completed


class StatusPageService:
    """ステータスページサービス"""

    def __init__(self):
        self.components: Dict[str, ServiceComponent] = {}
        self.incidents: List[Incident] = []
        self.maintenance_windows: List[MaintenanceWindow] = []
        self._init_components()

    def _init_components(self):
        """デフォルトコンポーネントを初期化"""
        components = [
            # コアサービス
            ServiceComponent("api", "API サーバー", "メインAPIエンドポイント", group="コアサービス", uptime_30d=99.95),
            ServiceComponent("web", "Web ダッシュボード", "ユーザー管理画面", group="コアサービス", uptime_30d=99.98),
            ServiceComponent("scheduler", "投稿スケジューラー", "自動投稿処理エンジン", group="コアサービス", uptime_30d=99.90),
            ServiceComponent("db", "データベース", "MySQL データベース", group="コアサービス", uptime_30d=99.99),
            # SNS連携
            ServiceComponent("sns_x", "X (Twitter) 連携", "X APIとの接続", group="SNS連携", uptime_30d=99.80),
            ServiceComponent("sns_ig", "Instagram 連携", "Instagram Graph API", group="SNS連携", uptime_30d=99.85),
            ServiceComponent("sns_threads", "Threads 連携", "Threads API", group="SNS連携", uptime_30d=99.82),
            ServiceComponent("sns_tiktok", "TikTok 連携", "TikTok Content Posting API", group="SNS連携", uptime_30d=99.70),
            ServiceComponent("sns_line", "LINE 連携", "LINE Messaging API", group="SNS連携", uptime_30d=99.90),
            # インフラ
            ServiceComponent("storage", "画像ストレージ", "ConoHa オブジェクトストレージ", group="インフラ", uptime_30d=99.95),
            ServiceComponent("cdn", "CDN", "コンテンツ配信", group="インフラ", uptime_30d=99.99),
            ServiceComponent("payment", "決済システム", "Stripe 決済処理", group="インフラ", uptime_30d=99.99),
        ]

        for comp in components:
            self.components[comp.id] = comp

    # ============================================================
    # ステータス取得
    # ============================================================

    def get_overall_status(self) -> Dict:
        """全体のステータスを取得"""
        statuses = [c.status for c in self.components.values()]

        if ServiceStatus.MAJOR_OUTAGE.value in statuses:
            overall = ServiceStatus.MAJOR_OUTAGE.value
        elif ServiceStatus.PARTIAL_OUTAGE.value in statuses:
            overall = ServiceStatus.PARTIAL_OUTAGE.value
        elif ServiceStatus.DEGRADED.value in statuses:
            overall = ServiceStatus.DEGRADED.value
        elif ServiceStatus.MAINTENANCE.value in statuses:
            overall = ServiceStatus.MAINTENANCE.value
        else:
            overall = ServiceStatus.OPERATIONAL.value

        label = STATUS_LABELS[overall]

        return {
            "status": overall,
            "label_ja": label["ja"],
            "label_en": label["en"],
            "color": label["color"],
            "updated_at": datetime.now().isoformat(),
        }

    def get_all_components(self) -> Dict[str, List[Dict]]:
        """グループ別のコンポーネント一覧"""
        groups = {}
        for comp in self.components.values():
            if comp.group not in groups:
                groups[comp.group] = []
            label = STATUS_LABELS[comp.status]
            groups[comp.group].append({
                "id": comp.id,
                "name": comp.name,
                "description": comp.description,
                "status": comp.status,
                "status_label": label["ja"],
                "status_color": label["color"],
                "uptime_30d": comp.uptime_30d,
            })
        return groups

    def get_uptime_summary(self, days: int = 90) -> Dict:
        """稼働率サマリー"""
        avg_uptime = sum(c.uptime_30d for c in self.components.values()) / len(self.components)
        return {
            "period_days": days,
            "average_uptime": round(avg_uptime, 2),
            "components": {
                c.id: {"name": c.name, "uptime": c.uptime_30d}
                for c in self.components.values()
            },
        }

    # ============================================================
    # コンポーネント管理
    # ============================================================

    def update_component_status(self, component_id: str, status: ServiceStatus) -> Dict:
        """コンポーネントのステータスを更新"""
        comp = self.components.get(component_id)
        if not comp:
            return {"status": "error", "message": "コンポーネントが見つかりません"}

        old_status = comp.status
        comp.status = status.value

        return {
            "status": "success",
            "component": comp.name,
            "old_status": STATUS_LABELS[old_status]["ja"],
            "new_status": STATUS_LABELS[status.value]["ja"],
        }

    # ============================================================
    # インシデント管理
    # ============================================================

    def create_incident(
        self,
        title: str,
        severity: IncidentSeverity,
        affected_components: List[str],
        message: str,
    ) -> Incident:
        """インシデントを作成"""
        now = datetime.now()
        incident = Incident(
            id=f"INC-{now.strftime('%Y%m%d')}-{len(self.incidents)+1:03d}",
            title=title,
            severity=severity.value,
            affected_components=affected_components,
            created_at=now.isoformat(),
            updates=[{
                "status": "investigating",
                "message": message,
                "timestamp": now.isoformat(),
            }],
        )
        self.incidents.append(incident)

        # 影響コンポーネントのステータス更新
        for comp_id in affected_components:
            if comp_id in self.components:
                if severity == IncidentSeverity.CRITICAL:
                    self.components[comp_id].status = ServiceStatus.MAJOR_OUTAGE.value
                elif severity == IncidentSeverity.MAJOR:
                    self.components[comp_id].status = ServiceStatus.PARTIAL_OUTAGE.value
                else:
                    self.components[comp_id].status = ServiceStatus.DEGRADED.value

        return incident

    def update_incident(self, incident_id: str, status: str, message: str) -> Dict:
        """インシデントを更新"""
        incident = next((i for i in self.incidents if i.id == incident_id), None)
        if not incident:
            return {"status": "error", "message": "インシデントが見つかりません"}

        now = datetime.now()
        incident.status = status
        incident.updates.append({
            "status": status,
            "message": message,
            "timestamp": now.isoformat(),
        })

        if status == "resolved":
            incident.resolved_at = now.isoformat()
            for comp_id in incident.affected_components:
                if comp_id in self.components:
                    self.components[comp_id].status = ServiceStatus.OPERATIONAL.value

        return {"status": "success", "incident_id": incident_id, "new_status": status}

    def get_active_incidents(self) -> List[Dict]:
        """アクティブなインシデント一覧"""
        active = [i for i in self.incidents if i.status != "resolved"]
        return [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity,
                "status": i.status,
                "affected": [self.components[c].name for c in i.affected_components if c in self.components],
                "created_at": i.created_at,
                "updates": i.updates,
            }
            for i in active
        ]

    def get_incident_history(self, days: int = 30) -> List[Dict]:
        """インシデント履歴"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        recent = [i for i in self.incidents if i.created_at >= cutoff]
        return [
            {
                "id": i.id,
                "title": i.title,
                "severity": i.severity,
                "status": i.status,
                "created_at": i.created_at,
                "resolved_at": i.resolved_at,
                "duration": self._calc_duration(i),
            }
            for i in recent
        ]

    def _calc_duration(self, incident: Incident) -> str:
        """インシデントの継続時間を計算"""
        start = datetime.fromisoformat(incident.created_at)
        if incident.resolved_at:
            end = datetime.fromisoformat(incident.resolved_at)
        else:
            end = datetime.now()
        delta = end - start
        hours = delta.seconds // 3600
        minutes = (delta.seconds % 3600) // 60
        if delta.days > 0:
            return f"{delta.days}日{hours}時間"
        elif hours > 0:
            return f"{hours}時間{minutes}分"
        else:
            return f"{minutes}分"

    # ============================================================
    # メンテナンスウィンドウ
    # ============================================================

    def schedule_maintenance(
        self,
        title: str,
        description: str,
        affected_components: List[str],
        start: str,
        end: str,
    ) -> MaintenanceWindow:
        """メンテナンスをスケジュール"""
        mw = MaintenanceWindow(
            id=f"MNT-{datetime.now().strftime('%Y%m%d')}-{len(self.maintenance_windows)+1:03d}",
            title=title,
            description=description,
            affected_components=affected_components,
            scheduled_start=start,
            scheduled_end=end,
        )
        self.maintenance_windows.append(mw)
        return mw

    def get_upcoming_maintenance(self) -> List[Dict]:
        """予定されたメンテナンス一覧"""
        now = datetime.now().isoformat()
        upcoming = [m for m in self.maintenance_windows if m.scheduled_end >= now]
        return [
            {
                "id": m.id,
                "title": m.title,
                "description": m.description,
                "affected": [self.components[c].name for c in m.affected_components if c in self.components],
                "start": m.scheduled_start,
                "end": m.scheduled_end,
                "status": m.status,
            }
            for m in upcoming
        ]

    # ============================================================
    # 公開API用
    # ============================================================

    def get_status_page_data(self) -> Dict:
        """ステータスページ全体のデータ"""
        return {
            "overall": self.get_overall_status(),
            "components": self.get_all_components(),
            "active_incidents": self.get_active_incidents(),
            "upcoming_maintenance": self.get_upcoming_maintenance(),
            "uptime": self.get_uptime_summary(),
        }


# テスト用
if __name__ == "__main__":
    service = StatusPageService()

    print("=== 全体ステータス ===")
    overall = service.get_overall_status()
    print(f"  {overall['label_ja']} ({overall['status']})")

    print(f"\n=== コンポーネント一覧 ===")
    for group, components in service.get_all_components().items():
        print(f"\n  【{group}】")
        for comp in components:
            print(f"    {comp['name']}: {comp['status_label']} (稼働率 {comp['uptime_30d']}%)")

    print(f"\n=== インシデント作成テスト ===")
    incident = service.create_incident(
        "TikTok API接続エラー",
        IncidentSeverity.MINOR,
        ["sns_tiktok"],
        "TikTok APIへの接続でタイムアウトが発生しています。調査中です。",
    )
    print(f"  作成: {incident.id} - {incident.title}")

    # ステータス更新
    overall = service.get_overall_status()
    print(f"  全体ステータス: {overall['label_ja']}")

    # インシデント更新
    service.update_incident(incident.id, "identified", "原因を特定しました。TikTok側のAPI障害です。")
    service.update_incident(incident.id, "resolved", "TikTok APIが復旧しました。正常に動作しています。")

    overall = service.get_overall_status()
    print(f"  解決後ステータス: {overall['label_ja']}")

    print(f"\n=== メンテナンススケジュール ===")
    mw = service.schedule_maintenance(
        "定期メンテナンス",
        "データベースの最適化とセキュリティアップデートを実施します。",
        ["api", "db"],
        "2026-03-15T02:00:00",
        "2026-03-15T04:00:00",
    )
    upcoming = service.get_upcoming_maintenance()
    for m in upcoming:
        print(f"  {m['title']}: {m['start'][:16]} 〜 {m['end'][:16]}")
        print(f"    影響: {', '.join(m['affected'])}")

    print(f"\n=== 稼働率サマリー ===")
    uptime = service.get_uptime_summary()
    print(f"  平均稼働率: {uptime['average_uptime']}%")

    print("\n✓ ステータスページサービス テスト完了")
