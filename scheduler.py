import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import settings
from upload_manager import upload_manager


logger = logging.getLogger(__name__)


class UploadScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="UTC")
        self._setup_jobs()

    def _setup_jobs(self):
        for idx, time_str in enumerate(settings.upload_times_list):
            try:
                hour, minute = time_str.split(":")
                trigger = CronTrigger(hour=int(hour), minute=int(minute), timezone="UTC")

                self.scheduler.add_job(
                    func=self._scheduled_upload,
                    trigger=trigger,
                    id=f"upload_job_{idx}",
                    name=f"Scheduled Upload {idx + 1} ({time_str})",
                    replace_existing=True,
                )
                logger.info(f"Scheduled upload job {idx + 1} at {time_str} UTC")
            except ValueError as e:
                logger.error(f"Invalid time format '{time_str}': {e}")

    def _scheduled_upload(self):
        logger.info("Scheduled upload triggered")
        try:
            success, filename, video_id, error = upload_manager.execute_upload()
            if success:
                logger.info(f"Scheduled upload completed: {filename} -> {video_id}")
            else:
                logger.warning(f"Scheduled upload failed: {filename} - {error}")
        except Exception as e:
            logger.error(f"Scheduled upload exception: {e}")

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Upload scheduler started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Upload scheduler stopped")

    def trigger_manual_upload(self):
        logger.info("Manual upload triggered")
        return upload_manager.execute_upload()

    def get_jobs(self) -> list[dict]:
        jobs = self.scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            }
            for job in jobs
        ]


scheduler_instance = UploadScheduler()