import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional
from config import settings


class LoggerService:
    _instance: Optional["LoggerService"] = None
    _log_file: Path = Path("logs/upload_logs.json")
    _upload_logs: dict = {"uploads": [], "stats": {"total": 0, "success": 0, "failed": 0}}

    def __new__(cls) -> "LoggerService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        self._log_file.parent.mkdir(parents=True, exist_ok=True)
        self._upload_logs = self._load_logs()
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler("logs/app.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def _load_logs(self) -> dict:
        if self._log_file.exists():
            try:
                with open(self._log_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {"uploads": [], "stats": {"total": 0, "success": 0, "failed": 0}}
        return {"uploads": [], "stats": {"total": 0, "success": 0, "failed": 0}}

    def _save_logs(self):
        with open(self._log_file, "w", encoding="utf-8") as f:
            json.dump(self._upload_logs, f, indent=2, ensure_ascii=False)

    def log_upload(self, filename: str, status: str, youtube_video_id: Optional[str] = None, error: Optional[str] = None):
        entry = {
            "filename": filename,
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": status,
        }
        if youtube_video_id:
            entry["youtube_video_id"] = youtube_video_id
        if error:
            entry["error"] = error

        self._upload_logs["uploads"].append(entry)
        self._upload_logs["stats"]["total"] += 1
        if status == "success":
            self._upload_logs["stats"]["success"] += 1
        elif status == "failed":
            self._upload_logs["stats"]["failed"] += 1

        self._save_logs()
        if status == "success":
            self.logger.info(f"Upload logged: {filename} -> {status}")
        else:
            self.logger.error(f"Upload logged: {filename} -> {status} | Error: {error}")

    def get_last_uploaded_sequence(self) -> int:
        uploads = self._upload_logs.get("uploads", [])
        max_seq = 0
        for entry in uploads:
            if entry.get("status") == "success":
                filename = entry.get("filename", "")
                seq = self._extract_sequence(filename)
                if seq > 0:
                    max_seq = max(max_seq, seq)
        return max_seq

    def _extract_sequence(self, filename: str) -> int:
        import re
        match = re.search(r"ota(\d+)", filename, re.IGNORECASE)
        return int(match.group(1)) if match else 0

    def get_upload_logs(self) -> dict:
        return self._upload_logs

    def get_upload_history(self, limit: int = 20) -> list:
        uploads = self._upload_logs.get("uploads", [])
        return sorted(uploads, key=lambda x: x.get("uploaded_at", ""), reverse=True)[:limit]


logger_service = LoggerService()