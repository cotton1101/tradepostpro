"""
パフォーマンスモニタリングサービス
APM、メトリクス収集、ヘルスチェック
"""

import time
import threading
import statistics
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum


class MetricType(Enum):
    """メトリクスタイプ"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class HealthStatus(Enum):
    """ヘルスステータス"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class Metric:
    """メトリクスデータ"""
    name: str
    type: MetricType
    value: float
    tags: dict = field(default_factory=dict)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class RequestTrace:
    """リクエストトレース"""
    trace_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    user_id: Optional[str] = None
    timestamp: str = ""
    spans: list = field(default_factory=list)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class Span:
    """トレーススパン"""
    name: str
    operation: str
    duration_ms: float
    tags: dict = field(default_factory=dict)


class PerformanceService:
    """パフォーマンスモニタリングサービス"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.traces: List[RequestTrace] = []
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self._lock = threading.Lock()

        # しきい値設定
        self.thresholds = {
            "response_time_p95_ms": 500,
            "response_time_p99_ms": 1000,
            "error_rate_percent": 5,
            "cpu_percent": 80,
            "memory_percent": 85,
            "disk_percent": 90,
        }

    # ========== メトリクス収集 ==========

    def increment(self, name: str, value: float = 1, tags: dict = None):
        """カウンターをインクリメント"""
        key = f"{name}:{str(tags or {})}"
        self.counters[key] += value
        self.metrics[name].append(Metric(name, MetricType.COUNTER, value, tags or {}))

    def gauge(self, name: str, value: float, tags: dict = None):
        """ゲージを設定"""
        key = f"{name}:{str(tags or {})}"
        self.gauges[key] = value
        self.metrics[name].append(Metric(name, MetricType.GAUGE, value, tags or {}))

    def histogram(self, name: str, value: float, tags: dict = None):
        """ヒストグラムに値を追加"""
        self.metrics[name].append(Metric(name, MetricType.HISTOGRAM, value, tags or {}))

    def timer(self, name: str):
        """タイマーコンテキストマネージャー"""
        return TimerContext(self, name)

    # ========== リクエストトレース ==========

    def record_request(self, trace: RequestTrace):
        """リクエストトレースを記録"""
        with self._lock:
            self.traces.append(trace)
            self.increment("http.requests.total", tags={"method": trace.method, "status": str(trace.status_code)})
            self.histogram("http.request.duration_ms", trace.duration_ms, tags={"path": trace.path})

            if trace.status_code >= 500:
                self.increment("http.errors.5xx")
            elif trace.status_code >= 400:
                self.increment("http.errors.4xx")

    # ========== ヘルスチェック ==========

    def health_check(self) -> dict:
        """システムヘルスチェック"""
        checks = {}

        # アプリケーション
        checks["application"] = {
            "status": HealthStatus.HEALTHY.value,
            "uptime": self._get_uptime(),
        }

        # レスポンスタイム
        recent_traces = self._get_recent_traces(minutes=5)
        if recent_traces:
            durations = [t.duration_ms for t in recent_traces]
            p95 = self._percentile(durations, 95)
            checks["response_time"] = {
                "status": HealthStatus.HEALTHY.value if p95 < self.thresholds["response_time_p95_ms"]
                    else HealthStatus.DEGRADED.value if p95 < self.thresholds["response_time_p99_ms"]
                    else HealthStatus.UNHEALTHY.value,
                "p50_ms": round(self._percentile(durations, 50), 2),
                "p95_ms": round(p95, 2),
                "p99_ms": round(self._percentile(durations, 99), 2),
                "avg_ms": round(statistics.mean(durations), 2),
            }
        else:
            checks["response_time"] = {"status": HealthStatus.HEALTHY.value, "message": "No recent requests"}

        # エラーレート
        if recent_traces:
            error_count = sum(1 for t in recent_traces if t.status_code >= 500)
            error_rate = error_count / len(recent_traces) * 100
            checks["error_rate"] = {
                "status": HealthStatus.HEALTHY.value if error_rate < self.thresholds["error_rate_percent"]
                    else HealthStatus.DEGRADED.value if error_rate < 10
                    else HealthStatus.UNHEALTHY.value,
                "rate_percent": round(error_rate, 2),
                "total_errors": error_count,
                "total_requests": len(recent_traces),
            }
        else:
            checks["error_rate"] = {"status": HealthStatus.HEALTHY.value, "rate_percent": 0}

        # システムリソース（シミュレート）
        checks["system"] = self._check_system_resources()

        # 全体ステータス
        statuses = [c.get("status", HealthStatus.HEALTHY.value) for c in checks.values()]
        if HealthStatus.UNHEALTHY.value in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED.value in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        return {
            "status": overall.value,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        }

    # ========== ダッシュボードデータ ==========

    def get_dashboard_metrics(self, hours: int = 24) -> dict:
        """ダッシュボード用メトリクスを取得"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_traces = [t for t in self.traces if datetime.fromisoformat(t.timestamp) > cutoff]

        # リクエスト統計
        request_stats = self._calculate_request_stats(recent_traces)

        # エンドポイント別統計
        endpoint_stats = self._calculate_endpoint_stats(recent_traces)

        # 時間帯別統計
        hourly_stats = self._calculate_hourly_stats(recent_traces)

        return {
            "period_hours": hours,
            "request_stats": request_stats,
            "endpoint_stats": endpoint_stats,
            "hourly_stats": hourly_stats,
            "counters": dict(self.counters),
            "gauges": dict(self.gauges),
        }

    def get_slow_requests(self, threshold_ms: float = 500, limit: int = 20) -> List[dict]:
        """遅いリクエストを取得"""
        slow = [t for t in self.traces if t.duration_ms >= threshold_ms]
        slow.sort(key=lambda t: t.duration_ms, reverse=True)
        return [
            {
                "trace_id": t.trace_id,
                "method": t.method,
                "path": t.path,
                "status_code": t.status_code,
                "duration_ms": round(t.duration_ms, 2),
                "user_id": t.user_id,
                "timestamp": t.timestamp,
                "spans": [{"name": s.name, "operation": s.operation, "duration_ms": s.duration_ms} for s in t.spans],
            }
            for t in slow[:limit]
        ]

    # ========== 内部ヘルパー ==========

    def _get_recent_traces(self, minutes: int = 5) -> List[RequestTrace]:
        """最近のトレースを取得"""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [t for t in self.traces if datetime.fromisoformat(t.timestamp) > cutoff]

    def _percentile(self, data: List[float], percentile: float) -> float:
        """パーセンタイル計算"""
        if not data:
            return 0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        lower = int(index)
        upper = lower + 1
        if upper >= len(sorted_data):
            return sorted_data[-1]
        weight = index - lower
        return sorted_data[lower] * (1 - weight) + sorted_data[upper] * weight

    def _get_uptime(self) -> str:
        """アップタイムを取得"""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.readline().split()[0])
                hours = int(uptime_seconds // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                return f"{hours}h {minutes}m"
        except Exception:
            return "N/A"

    def _check_system_resources(self) -> dict:
        """システムリソースをチェック"""
        try:
            # メモリ情報
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = int(parts[1].strip().split()[0])
                        meminfo[key] = value

            total_mem = meminfo.get('MemTotal', 1)
            free_mem = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
            mem_percent = ((total_mem - free_mem) / total_mem) * 100

            # ロードアベレージ
            load_avg = os.getloadavg()

            return {
                "status": HealthStatus.HEALTHY.value if mem_percent < self.thresholds["memory_percent"]
                    else HealthStatus.DEGRADED.value,
                "memory_percent": round(mem_percent, 1),
                "memory_total_mb": round(total_mem / 1024, 0),
                "memory_used_mb": round((total_mem - free_mem) / 1024, 0),
                "load_avg_1m": round(load_avg[0], 2),
                "load_avg_5m": round(load_avg[1], 2),
                "load_avg_15m": round(load_avg[2], 2),
            }
        except Exception as e:
            return {"status": HealthStatus.HEALTHY.value, "error": str(e)}

    def _calculate_request_stats(self, traces: List[RequestTrace]) -> dict:
        """リクエスト統計を計算"""
        if not traces:
            return {"total": 0, "avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0, "error_rate": 0}

        durations = [t.duration_ms for t in traces]
        errors = sum(1 for t in traces if t.status_code >= 500)

        return {
            "total": len(traces),
            "avg_ms": round(statistics.mean(durations), 2),
            "p50_ms": round(self._percentile(durations, 50), 2),
            "p95_ms": round(self._percentile(durations, 95), 2),
            "p99_ms": round(self._percentile(durations, 99), 2),
            "min_ms": round(min(durations), 2),
            "max_ms": round(max(durations), 2),
            "error_rate": round(errors / len(traces) * 100, 2),
            "errors_5xx": errors,
            "errors_4xx": sum(1 for t in traces if 400 <= t.status_code < 500),
        }

    def _calculate_endpoint_stats(self, traces: List[RequestTrace]) -> List[dict]:
        """エンドポイント別統計"""
        endpoint_data: Dict[str, List[RequestTrace]] = defaultdict(list)
        for t in traces:
            endpoint_data[f"{t.method} {t.path}"].append(t)

        results = []
        for endpoint, endpoint_traces in endpoint_data.items():
            durations = [t.duration_ms for t in endpoint_traces]
            results.append({
                "endpoint": endpoint,
                "requests": len(endpoint_traces),
                "avg_ms": round(statistics.mean(durations), 2),
                "p95_ms": round(self._percentile(durations, 95), 2),
                "error_rate": round(sum(1 for t in endpoint_traces if t.status_code >= 500) / len(endpoint_traces) * 100, 2),
            })

        results.sort(key=lambda x: x["requests"], reverse=True)
        return results

    def _calculate_hourly_stats(self, traces: List[RequestTrace]) -> List[dict]:
        """時間帯別統計"""
        hourly: Dict[str, List[RequestTrace]] = defaultdict(list)
        for t in traces:
            hour = datetime.fromisoformat(t.timestamp).strftime("%Y-%m-%d %H:00")
            hourly[hour].append(t)

        results = []
        for hour, hour_traces in sorted(hourly.items()):
            durations = [t.duration_ms for t in hour_traces]
            results.append({
                "hour": hour,
                "requests": len(hour_traces),
                "avg_ms": round(statistics.mean(durations), 2),
                "errors": sum(1 for t in hour_traces if t.status_code >= 500),
            })
        return results

    def generate_prometheus_metrics(self) -> str:
        """Prometheus形式のメトリクスを生成"""
        lines = []
        lines.append("# HELP http_requests_total Total HTTP requests")
        lines.append("# TYPE http_requests_total counter")
        for key, value in self.counters.items():
            lines.append(f"http_requests_total{{{key}}} {value}")

        lines.append("")
        lines.append("# HELP http_request_duration_ms HTTP request duration in milliseconds")
        lines.append("# TYPE http_request_duration_ms histogram")

        for key, value in self.gauges.items():
            lines.append(f"gauge{{{key}}} {value}")

        return "\n".join(lines)


class TimerContext:
    """タイマーコンテキストマネージャー"""
    def __init__(self, service: PerformanceService, name: str):
        self.service = service
        self.name = name
        self.start_time = 0

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        duration_ms = (time.time() - self.start_time) * 1000
        self.service.histogram(self.name, duration_ms)


# テスト実行
if __name__ == "__main__":
    import random
    import hashlib
    random.seed(42)

    service = PerformanceService()

    print("=== パフォーマンスモニタリング テスト ===")

    # リクエストトレースを生成
    print("\n--- リクエストトレース生成 ---")
    endpoints = [
        ("GET", "/api/v1/posts", [200, 200, 200, 200, 500]),
        ("POST", "/api/v1/posts/create", [201, 201, 400, 201, 500]),
        ("GET", "/api/v1/stats", [200, 200, 200, 200, 200]),
        ("POST", "/api/v1/images/generate", [200, 200, 500, 200, 200]),
        ("GET", "/api/v1/users/profile", [200, 200, 200, 401, 200]),
    ]

    for i in range(50):
        method, path, statuses = random.choice(endpoints)
        status = random.choice(statuses)
        duration = random.uniform(10, 800) if status < 500 else random.uniform(500, 3000)

        trace = RequestTrace(
            trace_id=hashlib.md5(f"trace_{i}".encode()).hexdigest()[:12],
            method=method,
            path=path,
            status_code=status,
            duration_ms=duration,
            user_id=f"user_{random.randint(1, 10):03d}",
            spans=[
                Span("db_query", "db", random.uniform(1, 50)),
                Span("cache_lookup", "cache", random.uniform(0.1, 5)),
                Span("template_render", "render", random.uniform(5, 100)),
            ],
        )
        service.record_request(trace)
    print(f"  50件のリクエストトレースを記録")

    # タイマーテスト
    print("\n--- タイマーテスト ---")
    with service.timer("test.operation"):
        time.sleep(0.05)
    print(f"  タイマー記録完了")

    # ヘルスチェック
    print("\n--- ヘルスチェック ---")
    health = service.health_check()
    print(f"  全体ステータス: {health['status']}")
    for check_name, check_data in health["checks"].items():
        print(f"    {check_name}: {check_data['status']}")

    # ダッシュボードメトリクス
    print("\n--- ダッシュボードメトリクス ---")
    dashboard = service.get_dashboard_metrics(24)
    rs = dashboard["request_stats"]
    print(f"  総リクエスト: {rs['total']}")
    print(f"  平均レスポンス: {rs['avg_ms']:.1f}ms")
    print(f"  P50: {rs['p50_ms']:.1f}ms")
    print(f"  P95: {rs['p95_ms']:.1f}ms")
    print(f"  P99: {rs['p99_ms']:.1f}ms")
    print(f"  エラーレート: {rs['error_rate']:.1f}%")

    print("\n  エンドポイント別:")
    for ep in dashboard["endpoint_stats"][:5]:
        print(f"    {ep['endpoint']}: {ep['requests']}req, avg={ep['avg_ms']:.1f}ms, err={ep['error_rate']:.1f}%")

    # 遅いリクエスト
    print("\n--- 遅いリクエスト Top 5 ---")
    slow = service.get_slow_requests(threshold_ms=300, limit=5)
    for s in slow:
        print(f"  {s['method']} {s['path']}: {s['duration_ms']:.1f}ms (status: {s['status_code']})")

    # Prometheusメトリクス
    print("\n--- Prometheusメトリクス ---")
    prom = service.generate_prometheus_metrics()
    print(f"  メトリクス行数: {len(prom.splitlines())}")

    print("\n✓ パフォーマンスモニタリングサービス テスト完了")
