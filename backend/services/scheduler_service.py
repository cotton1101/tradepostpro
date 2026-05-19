"""
投稿スケジューラーサービス
==========================
ユーザーごとの投稿スケジュール管理、リトライ処理、キュー管理を行います。

機能:
  - ユーザー別の投稿時間設定
  - 失敗時の自動リトライ（最大3回、指数バックオフ）
  - 投稿ジョブキュー管理
  - スケジュール実行エンジン
"""

import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional, Dict

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float
from sqlalchemy.orm import Session

from backend.models.database import (
    Base, User, SNSAccount, TradeDataRecord, PostHistory,
    PlanType, PlatformType, PostStatus, get_db, SessionLocal
)
from backend.services.plan_service import PlanService

logger = logging.getLogger(__name__)


# ============================================================
# ジョブキューモデル
# ============================================================

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class PostJob(Base):
    """投稿ジョブキューテーブル"""
    __tablename__ = "post_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    platform = Column(String(50), nullable=False)
    status = Column(String(20), default=JobStatus.QUEUED.value, nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    trade_data_id = Column(Integer, nullable=True)
    template_id = Column(String(50), default="dark_classic")
    generate_video = Column(Boolean, default=False)
    result_post_id = Column(String(255), nullable=True)  # 外部投稿ID
    result_image_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserSchedule(Base):
    """ユーザー投稿スケジュール設定テーブル"""
    __tablename__ = "user_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    is_enabled = Column(Boolean, default=True)
    post_hour = Column(Integer, default=7)       # 投稿時刻（時）
    post_minute = Column(Integer, default=0)     # 投稿時刻（分）
    timezone = Column(String(50), default="Asia/Tokyo")
    template_id = Column(String(50), default="dark_classic")
    generate_video = Column(Boolean, default=False)
    line_openchat_url = Column(String(500), nullable=True)

    # 各SNSの有効/無効（個別制御）
    post_to_x = Column(Boolean, default=True)
    post_to_instagram = Column(Boolean, default=True)
    post_to_threads = Column(Boolean, default=True)
    post_to_tiktok = Column(Boolean, default=True)
    post_to_line = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ============================================================
# スケジューラーサービス
# ============================================================

class SchedulerService:
    """投稿スケジューラーサービス"""

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 60  # 秒（指数バックオフの基準）

    @staticmethod
    def get_user_schedule(db: Session, user_id: int) -> Optional[UserSchedule]:
        """ユーザーのスケジュール設定を取得"""
        return db.query(UserSchedule).filter(
            UserSchedule.user_id == user_id
        ).first()

    @staticmethod
    def upsert_user_schedule(
        db: Session,
        user_id: int,
        post_hour: int = 7,
        post_minute: int = 0,
        timezone: str = "Asia/Tokyo",
        template_id: str = "dark_classic",
        generate_video: bool = False,
        line_openchat_url: str = "",
        platforms: Optional[Dict[str, bool]] = None,
    ) -> UserSchedule:
        """ユーザーのスケジュール設定を作成/更新"""
        schedule = db.query(UserSchedule).filter(
            UserSchedule.user_id == user_id
        ).first()

        if not schedule:
            schedule = UserSchedule(user_id=user_id)
            db.add(schedule)

        schedule.post_hour = post_hour
        schedule.post_minute = post_minute
        schedule.timezone = timezone
        schedule.template_id = template_id
        schedule.generate_video = generate_video
        schedule.line_openchat_url = line_openchat_url

        if platforms:
            schedule.post_to_x = platforms.get("x", True)
            schedule.post_to_instagram = platforms.get("instagram", True)
            schedule.post_to_threads = platforms.get("threads", True)
            schedule.post_to_tiktok = platforms.get("tiktok", True)
            schedule.post_to_line = platforms.get("line", True)

        db.commit()
        db.refresh(schedule)
        return schedule

    @staticmethod
    def create_post_jobs(
        db: Session,
        user_id: int,
        scheduled_at: datetime,
        trade_data_id: int,
        template_id: str = "dark_classic",
        generate_video: bool = False,
        platforms: Optional[List[str]] = None,
    ) -> List[PostJob]:
        """投稿ジョブをキューに追加"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"ユーザーが見つかりません: {user_id}")

        plan_config = PlanService.get_plan_config(user.plan)

        # 有効なSNSアカウントを取得
        accounts = db.query(SNSAccount).filter(
            SNSAccount.user_id == user_id,
            SNSAccount.is_enabled == True
        ).all()

        if platforms:
            accounts = [a for a in accounts if a.platform.value in platforms]

        # プラン制限を適用
        accounts = accounts[:plan_config.max_sns_count]

        jobs = []
        for acc in accounts:
            # 動画生成チェック
            should_video = generate_video and plan_config.video_generation

            job = PostJob(
                user_id=user_id,
                platform=acc.platform.value,
                status=JobStatus.QUEUED.value,
                scheduled_at=scheduled_at,
                trade_data_id=trade_data_id,
                template_id=template_id,
                generate_video=should_video,
                max_retries=SchedulerService.MAX_RETRIES,
            )
            db.add(job)
            jobs.append(job)

        db.commit()
        for job in jobs:
            db.refresh(job)

        logger.info(f"ユーザー {user_id}: {len(jobs)}件のジョブをキューに追加")
        return jobs

    @staticmethod
    def get_pending_jobs(db: Session, limit: int = 50) -> List[PostJob]:
        """実行待ちのジョブを取得（スケジュール時刻を過ぎたもの）"""
        now = datetime.utcnow()
        return db.query(PostJob).filter(
            PostJob.status.in_([JobStatus.QUEUED.value, JobStatus.RETRY.value]),
            PostJob.scheduled_at <= now,
        ).order_by(PostJob.scheduled_at.asc()).limit(limit).all()

    @staticmethod
    def get_retry_jobs(db: Session, limit: int = 20) -> List[PostJob]:
        """リトライ待ちのジョブを取得"""
        now = datetime.utcnow()
        return db.query(PostJob).filter(
            PostJob.status == JobStatus.RETRY.value,
            PostJob.next_retry_at <= now,
        ).order_by(PostJob.next_retry_at.asc()).limit(limit).all()

    @staticmethod
    def mark_job_running(db: Session, job: PostJob):
        """ジョブを実行中に更新"""
        job.status = JobStatus.RUNNING.value
        job.started_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def mark_job_success(db: Session, job: PostJob, post_id: str = "", image_url: str = ""):
        """ジョブを成功に更新"""
        job.status = JobStatus.SUCCESS.value
        job.completed_at = datetime.utcnow()
        job.result_post_id = post_id
        job.result_image_url = image_url
        db.commit()
        logger.info(f"ジョブ {job.id} ({job.platform}) 成功")

    @staticmethod
    def mark_job_failed(db: Session, job: PostJob, error: str):
        """ジョブを失敗/リトライに更新"""
        job.retry_count += 1
        job.error_message = error

        if job.retry_count < job.max_retries:
            # 指数バックオフでリトライ
            delay = SchedulerService.RETRY_BASE_DELAY * (2 ** (job.retry_count - 1))
            job.status = JobStatus.RETRY.value
            job.next_retry_at = datetime.utcnow() + timedelta(seconds=delay)
            logger.warning(
                f"ジョブ {job.id} ({job.platform}) 失敗 "
                f"(リトライ {job.retry_count}/{job.max_retries}, "
                f"次回: {delay}秒後): {error}"
            )
        else:
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.utcnow()
            logger.error(
                f"ジョブ {job.id} ({job.platform}) 最終失敗 "
                f"(リトライ上限到達): {error}"
            )

        db.commit()

    @staticmethod
    def cancel_job(db: Session, job_id: int, user_id: int) -> bool:
        """ジョブをキャンセル"""
        job = db.query(PostJob).filter(
            PostJob.id == job_id,
            PostJob.user_id == user_id,
            PostJob.status.in_([JobStatus.QUEUED.value, JobStatus.RETRY.value])
        ).first()

        if not job:
            return False

        job.status = JobStatus.CANCELLED.value
        job.completed_at = datetime.utcnow()
        db.commit()
        return True

    @staticmethod
    def get_job_history(
        db: Session,
        user_id: int,
        limit: int = 50,
        status: Optional[str] = None,
    ) -> List[PostJob]:
        """ジョブ履歴を取得"""
        query = db.query(PostJob).filter(PostJob.user_id == user_id)
        if status:
            query = query.filter(PostJob.status == status)
        return query.order_by(PostJob.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_job_stats(db: Session, user_id: int) -> dict:
        """ジョブ統計を取得"""
        total = db.query(PostJob).filter(PostJob.user_id == user_id).count()
        success = db.query(PostJob).filter(
            PostJob.user_id == user_id,
            PostJob.status == JobStatus.SUCCESS.value
        ).count()
        failed = db.query(PostJob).filter(
            PostJob.user_id == user_id,
            PostJob.status == JobStatus.FAILED.value
        ).count()
        queued = db.query(PostJob).filter(
            PostJob.user_id == user_id,
            PostJob.status.in_([JobStatus.QUEUED.value, JobStatus.RETRY.value])
        ).count()

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "queued": queued,
            "success_rate": (success / total * 100) if total > 0 else 0,
        }


# ============================================================
# スケジュール実行エンジン
# ============================================================

class ScheduleEngine:
    """
    定期実行エンジン。
    cronやsystemdタイマーから毎分呼び出され、
    スケジュール時刻に達したユーザーのジョブを生成します。
    """

    @staticmethod
    def generate_scheduled_jobs():
        """
        全ユーザーのスケジュールを確認し、
        投稿時刻に達したユーザーのジョブを生成します。
        """
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            # JST = UTC + 9
            jst_now = now + timedelta(hours=9)
            current_hour = jst_now.hour
            current_minute = jst_now.minute

            # 該当時刻のスケジュールを取得
            schedules = db.query(UserSchedule).filter(
                UserSchedule.is_enabled == True,
                UserSchedule.post_hour == current_hour,
                UserSchedule.post_minute == current_minute,
            ).all()

            for schedule in schedules:
                try:
                    ScheduleEngine._process_user_schedule(db, schedule, now)
                except Exception as e:
                    logger.error(f"ユーザー {schedule.user_id} のスケジュール処理エラー: {e}")

            logger.info(
                f"スケジュール確認完了: {jst_now.strftime('%H:%M')} JST, "
                f"{len(schedules)}件のスケジュールを処理"
            )
        finally:
            db.close()

    @staticmethod
    def _process_user_schedule(db: Session, schedule: UserSchedule, now: datetime):
        """個別ユーザーのスケジュールを処理"""
        user = db.query(User).filter(User.id == schedule.user_id).first()
        if not user or not user.is_active:
            return

        # 最新の取引データを取得
        trade_record = db.query(TradeDataRecord).filter(
            TradeDataRecord.user_id == user.id
        ).order_by(TradeDataRecord.date.desc()).first()

        if not trade_record:
            logger.warning(f"ユーザー {user.id}: 取引データなし、スキップ")
            return

        # 今日のジョブが既に存在するか確認（重複防止）
        today = now.strftime("%Y-%m-%d")
        existing = db.query(PostJob).filter(
            PostJob.user_id == user.id,
            PostJob.created_at >= datetime.strptime(today, "%Y-%m-%d"),
        ).first()

        if existing:
            logger.info(f"ユーザー {user.id}: 本日のジョブは既に存在、スキップ")
            return

        # 有効なプラットフォームを決定
        platforms = []
        if schedule.post_to_x:
            platforms.append("x")
        if schedule.post_to_instagram:
            platforms.append("instagram")
        if schedule.post_to_threads:
            platforms.append("threads")
        if schedule.post_to_tiktok:
            platforms.append("tiktok")
        if schedule.post_to_line:
            platforms.append("line")

        # ジョブ生成
        jobs = SchedulerService.create_post_jobs(
            db=db,
            user_id=user.id,
            scheduled_at=now,
            trade_data_id=trade_record.id,
            template_id=schedule.template_id,
            generate_video=schedule.generate_video,
            platforms=platforms,
        )

        logger.info(f"ユーザー {user.id}: {len(jobs)}件のジョブを生成")

    @staticmethod
    def process_pending_jobs():
        """
        キュー内の実行待ちジョブを処理します。
        cronから毎分呼び出されることを想定。
        """
        db = SessionLocal()
        try:
            # 通常ジョブ
            pending = SchedulerService.get_pending_jobs(db, limit=20)
            # リトライジョブ
            retries = SchedulerService.get_retry_jobs(db, limit=10)

            all_jobs = pending + retries

            if not all_jobs:
                return

            logger.info(f"処理対象ジョブ: {len(all_jobs)}件 (通常: {len(pending)}, リトライ: {len(retries)})")

            for job in all_jobs:
                try:
                    ScheduleEngine._execute_job(db, job)
                except Exception as e:
                    SchedulerService.mark_job_failed(db, job, str(e))
        finally:
            db.close()

    @staticmethod
    def _execute_job(db: Session, job: PostJob):
        """
        個別ジョブを実行します。
        
        注: 実際のSNS投稿処理はここから各モジュールを呼び出します。
        本番環境では modules/post_x.py 等を import して実行します。
        """
        SchedulerService.mark_job_running(db, job)

        try:
            # 取引データの取得
            trade_record = None
            if job.trade_data_id:
                trade_record = db.query(TradeDataRecord).filter(
                    TradeDataRecord.id == job.trade_data_id
                ).first()

            if not trade_record:
                raise ValueError("取引データが見つかりません")

            # SNSアカウントの取得
            account = db.query(SNSAccount).filter(
                SNSAccount.user_id == job.user_id,
                SNSAccount.platform == job.platform,
                SNSAccount.is_enabled == True
            ).first()

            if not account:
                raise ValueError(f"有効な{job.platform}アカウントが見つかりません")

            # ここで実際のSNS投稿処理を実行
            # 各プラットフォーム別の投稿モジュールを呼び出す
            result = _dispatch_post(
                platform=job.platform,
                account=account,
                trade_record=trade_record,
                template_id=job.template_id,
                generate_video=job.generate_video,
            )

            SchedulerService.mark_job_success(
                db, job,
                post_id=result.get("post_id", ""),
                image_url=result.get("image_url", ""),
            )

        except Exception as e:
            SchedulerService.mark_job_failed(db, job, str(e))


def _dispatch_post(
    platform: str,
    account,
    trade_record,
    template_id: str = "dark_classic",
    generate_video: bool = False,
) -> dict:
    """
    プラットフォーム別の投稿処理をディスパッチします。
    
    Returns:
        dict: {"post_id": str, "image_url": str}
    """
    # TradeDataオブジェクトの構築
    from modules.utils import TradeData
    trade_data = TradeData(
        date=trade_record.date,
        platform=trade_record.platform,
        account_balance=trade_record.account_balance,
        daily_profit=trade_record.daily_profit,
        daily_loss=trade_record.daily_loss,
        net_profit=trade_record.net_profit,
        total_trades=trade_record.total_trades,
        winning_trades=trade_record.winning_trades,
        losing_trades=trade_record.losing_trades,
        win_rate=trade_record.win_rate,
        cumulative_profit=trade_record.cumulative_profit,
        currency=trade_record.currency,
    )

    # 画像生成
    from modules.image_templates import render_template
    image_path = render_template(template_id, trade_data)

    # 動画生成（プレミアムプランのみ）
    video_path = None
    if generate_video:
        from modules.video_generator import generate_trade_video
        video_path = generate_trade_video(trade_data.to_dict())

    # 画像アップロード
    image_url = ""
    try:
        from modules.image_uploader import upload_image
        image_url = upload_image(image_path)
    except Exception as e:
        logger.warning(f"画像アップロード失敗: {e}")

    # プラットフォーム別投稿
    result = {"post_id": "", "image_url": image_url}

    if platform == "x":
        from modules.post_x import post_to_x
        post_result = post_to_x(trade_data)
        result["post_id"] = post_result.get("tweet_id", "")

    elif platform == "instagram":
        from modules.post_instagram import post_to_instagram
        post_result = post_to_instagram(trade_data, image_url)
        result["post_id"] = post_result.get("post_id", "")

    elif platform == "threads":
        from modules.post_threads import post_to_threads
        post_result = post_to_threads(trade_data, image_url)
        result["post_id"] = post_result.get("post_id", "")

    elif platform == "tiktok":
        from modules.post_tiktok import post_to_tiktok
        media = video_path if video_path else image_path
        post_result = post_to_tiktok(trade_data, media)
        result["post_id"] = post_result.get("post_id", "")

    elif platform == "line":
        from modules.post_line import post_to_line
        post_result = post_to_line(trade_data, image_url)
        result["post_id"] = post_result.get("message_id", "")

    return result


# ============================================================
# CLI エントリーポイント
# ============================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="投稿スケジューラー")
    parser.add_argument("--generate", action="store_true", help="スケジュールジョブを生成")
    parser.add_argument("--process", action="store_true", help="キュー内のジョブを処理")
    parser.add_argument("--both", action="store_true", help="生成と処理の両方を実行")
    args = parser.parse_args()

    if args.generate or args.both:
        print("スケジュールジョブ生成中...")
        ScheduleEngine.generate_scheduled_jobs()

    if args.process or args.both:
        print("ジョブ処理中...")
        ScheduleEngine.process_pending_jobs()

    if not (args.generate or args.process or args.both):
        print("使い方: --generate, --process, --both のいずれかを指定してください")
