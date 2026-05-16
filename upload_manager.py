import os
import re
import logging
import shutil
from pathlib import Path
from typing import Optional
from config import settings
from drive_service import drive_service
from sequence_manager import sequence_manager
from ai_service import ai_service
from youtube_service import youtube_service
from logger_service import logger_service


logger = logging.getLogger(__name__)


class UploadManager:
    VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".flv", ".wmv"}

    def __init__(self):
        self.folder_structure: dict = {}
        self._initialize_folders()

    def _initialize_folders(self):
        if not settings.google_drive_folder_id:
            logger.warning("GOOGLE_DRIVE_FOLDER_ID not set")
            return

        self.folder_structure = drive_service.get_folder_structure(settings.google_drive_folder_id)
        logger.info(f"Folder structure initialized: {list(self.folder_structure.keys())}")

    def get_pending_files(self) -> list[dict]:
        if not self.folder_structure.get("upload"):
            return []

        files = drive_service.list_files_in_folder(settings.google_drive_folder_id)
        valid_files = [
            f for f in files
            if f.get("name") and Path(f["name"]).suffix.lower() in self.VIDEO_EXTENSIONS
            and sequence_manager.is_valid_reel_filename(f["name"])
        ]

        filenames = [f["name"] for f in valid_files]
        next_file = sequence_manager.get_next_pending_file(filenames)

        if not next_file:
            logger.info("No pending files to upload")
            return []

        seq_num, filename = next_file
        for f in valid_files:
            if f["name"] == filename:
                logger.info(f"Next pending file: {filename} (sequence {seq_num})")
                return [f]

        return []

    def execute_upload(self) -> tuple[bool, Optional[str], Optional[str], Optional[str]]:
        pending = self.get_pending_files()
        if not pending:
            return False, None, None, "No pending files"

        file_info = pending[0]
        file_id = file_info["id"]
        filename = file_info["name"]

        temp_path = settings.get_temp_folder() / filename

        try:
            downloaded = drive_service.download_file(file_id, temp_path)
            if not downloaded:
                return False, filename, None, "Failed to download file"

            content = ai_service.generate_content(filename)

            success, video_id, error = youtube_service.upload_short(
                file_path=temp_path,
                content=content,
                privacy_status="public",
            )

            if success:
                self._archive_file(file_id, filename, "uploaded")
                sequence_manager.mark_uploaded(filename)
                logger_service.log_upload(filename, "success", youtube_video_id=video_id)
                logger.info(f"Successfully uploaded and archived: {filename}")
                return True, filename, video_id, None
            else:
                self._archive_file(file_id, filename, "failed")
                logger_service.log_upload(filename, "failed", error=error)
                logger.error(f"Upload failed for {filename}: {error}")
                return False, filename, None, error

        except Exception as e:
            logger.error(f"Unexpected error during upload: {e}")
            self._archive_file(file_id, filename, "failed")
            logger_service.log_upload(filename, "failed", error=str(e))
            return False, filename, None, str(e)

        finally:
            if temp_path.exists():
                os.remove(temp_path)

    def _archive_file(self, file_id: str, filename: str, archive_type: str):
        target_folder_key = archive_type
        target_folder_id = self.folder_structure.get(target_folder_key)

        if not target_folder_id:
            logger.warning(f"Target folder '{target_folder_key}' not found in Drive")
            return

        success = drive_service.move_file(file_id, target_folder_id)
        if success:
            logger.info(f"Moved {filename} to {archive_type} folder in Drive")
        else:
            logger.error(f"Failed to move {filename} to {archive_type} folder")

    def get_status(self) -> dict:
        pending = self.get_pending_files()
        seq_status = sequence_manager.get_status()
        logs = logger_service.get_upload_logs()

        return {
            "sequence": seq_status,
            "pending_count": len(pending),
            "next_pending": pending[0]["name"] if pending else None,
            "total_uploads": logs.get("stats", {}).get("total", 0),
            "success_count": logs.get("stats", {}).get("success", 0),
            "failed_count": logs.get("stats", {}).get("failed", 0),
        }


upload_manager = UploadManager()