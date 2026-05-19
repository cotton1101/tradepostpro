"""
全サービスの単体テスト一括実行スクリプト
各サービスの __main__ ブロックを実行して動作確認
"""

import subprocess
import sys
import os

os.chdir(os.path.join(os.path.dirname(__file__), ".."))

services_with_main = [
    "backend.services.ab_test_service",
    "backend.services.addon_service",
    "backend.services.annual_plan_service",
    "backend.services.audit_log_service",
    "backend.services.auto_reply_service",
    "backend.services.copy_trade_service",
    "backend.services.coupon_service",
    "backend.services.error_tracking_service",
    "backend.services.export_service",
    "backend.services.gamification_service",
    "backend.services.graphql_service",
    "backend.services.migration_service",
    "backend.services.notification_preferences",
    "backend.services.onboarding_service",
    "backend.services.optimal_time_service",
    "backend.services.pdf_report_service",
    "backend.services.performance_service",
    "backend.services.plan_service",
    "backend.services.pnl_calendar_service",
    "backend.services.portfolio_service",
    "backend.services.pwa_push_service",
    "backend.services.ranking_service",
    "backend.services.rate_limiter_service",
    "backend.services.realtime_service",
    "backend.services.redis_cache_service",
    "backend.services.referral_service",
    "backend.services.retargeting_service",
    "backend.services.revenue_report_service",
    "backend.services.scheduler_service",
    "backend.services.seo_blog_service",
    "backend.services.sns_analytics_service",
    "backend.services.status_page_service",
    "backend.services.step_mail_service",
    "backend.services.timezone_service",
    "backend.services.trial_service",
    "backend.services.two_factor_service",
    "backend.services.webhook_service",
    "backend.services.whitelabel_service",
]

results = {"ok": [], "fail": [], "skip": []}

for mod in services_with_main:
    print(f"\n{'='*60}")
    print(f"Testing: {mod}")
    print(f"{'='*60}")
    try:
        result = subprocess.run(
            [sys.executable, "-m", mod],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.getcwd(),
        )
        if result.returncode == 0:
            # Check if test actually ran (has output)
            if "テスト完了" in result.stdout or "test" in result.stdout.lower():
                print(f"  PASS")
                last_line = [l for l in result.stdout.strip().split("\n") if l.strip()][-1] if result.stdout.strip() else ""
                print(f"  Last: {last_line}")
                results["ok"].append(mod)
            else:
                print(f"  SKIP (no test output)")
                results["skip"].append(mod)
        else:
            print(f"  FAIL (exit code: {result.returncode})")
            if result.stderr:
                err_lines = result.stderr.strip().split("\n")
                for line in err_lines[-5:]:
                    print(f"    {line}")
            results["fail"].append((mod, result.stderr[-200:] if result.stderr else ""))
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT (30s)")
        results["fail"].append((mod, "TIMEOUT"))
    except Exception as e:
        print(f"  ERROR: {e}")
        results["fail"].append((mod, str(e)))

print(f"\n{'='*60}")
print(f"=== 最終結果 ===")
print(f"{'='*60}")
print(f"  PASS: {len(results['ok'])}")
print(f"  FAIL: {len(results['fail'])}")
print(f"  SKIP: {len(results['skip'])}")
print(f"  Total: {len(services_with_main)}")

if results["fail"]:
    print(f"\n--- 失敗したサービス ---")
    for mod, err in results["fail"]:
        print(f"  {mod}: {err[:100]}")

if results["skip"]:
    print(f"\n--- スキップしたサービス ---")
    for mod in results["skip"]:
        print(f"  {mod}")
