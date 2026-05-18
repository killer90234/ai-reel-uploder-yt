import os
import json
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    nvidia_api_key: str = Field(default="", alias="NVIDIA_API_KEY")
    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field(default="", alias="GOOGLE_CLIENT_SECRET")
    youtube_refresh_token: str = Field(default="", alias="YOUTUBE_REFRESH_TOKEN")
    google_drive_folder_id: str = Field(default="", alias="GOOGLE_DRIVE_FOLDER_ID")
    upload_times: str = Field(default="09:00,14:00,19:00", alias="UPLOAD_TIMES")
    start_sequence: int = Field(default=0, alias="START_SEQUENCE")

    google_credentials_path: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials/google_credentials.json")
    youtube_token_path: str = os.getenv("YOUTUBE_TOKEN_PATH", "credentials/token.json")
    upload_logs_path: str = "logs/upload_logs.json"
    temp_folder: str = "temp"
    uploaded_folder: str = "uploaded"
    failed_folder: str = "failed"
    upload_subfolder: str = "upload"

    upload_times_list: list[str] = []

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.upload_times_list = [t.strip() for t in self.upload_times.split(",") if t.strip()]

    def get_credentials_path(self) -> Path:
        return Path(self.google_credentials_path)

    def get_youtube_token_path(self) -> Path:
        return Path(self.youtube_token_path)

    def get_logs_path(self) -> Path:
        return Path(self.upload_logs_path)

    def get_temp_folder(self) -> Path:
        p = Path(self.temp_folder)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_uploaded_folder(self) -> Path:
        p = Path(self.uploaded_folder)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_failed_folder(self) -> Path:
        p = Path(self.failed_folder)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def get_upload_subfolder(self) -> Path:
        return Path(self.upload_subfolder)


settings = Settings()