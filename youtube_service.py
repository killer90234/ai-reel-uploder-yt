import os
import json
import logging
from pathlib import Path
from typing import Optional
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request
from config import settings
from ai_service import ai_service, NvidiaAIContent


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


class YouTubeService:
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    def __init__(self):
        self.creds: Optional[Credentials] = None
        self.youtube = None
        self._authenticate()

    def _authenticate(self):
        creds_path = settings.get_credentials_path()
        token_path = settings.get_youtube_token_path()

        if token_path.exists():
            try:
                self.creds = Credentials.from_authorized_user_info(json.loads(token_path.read_text(encoding="utf-8")), SCOPES)
            except Exception:
                self.creds = None

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
                token_path.write_text(self.creds.to_json(), encoding="utf-8")
            else:
                logger.warning("YouTube credentials invalid or missing. Upload will fail.")

        try:
            self.youtube = build(self.API_SERVICE_NAME, self.API_VERSION, credentials=self.creds, developerKey=None)
            logger.info("YouTube API authenticated successfully")
        except Exception as e:
            logger.error(f"Failed to build YouTube service: {e}")

    def refresh_credentials(self):
        self._authenticate()

    def upload_short(
        self,
        file_path: Path,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[list[str]] = None,
        category_id: str = "22",
        privacy_status: str = "public",
        content: Optional[NvidiaAIContent] = None,
    ) -> tuple[bool, Optional[str], Optional[str]]:
        if not self.youtube:
            return False, None, "YouTube service not initialized"

        if not file_path.exists():
            return False, None, f"File not found: {file_path}"

        if content:
            final_title = content.title if not title else title
            hashtags_str = " ".join(content.hashtags)
            final_description = f"{content.caption}\n\n{hashtags_str}" if not description else description
            final_tags = content.hashtags if not tags else tags
        else:
            final_title = title or file_path.stem
            final_description = description or ""
            final_tags = tags or []

        body = {
            "snippet": {
                "title": final_title[:100],
                "description": final_description[:5000],
                "tags": [t.lstrip("#") for t in final_tags[:500]],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            },
        }

        try:
            media = MediaFileUpload(str(file_path), chunksize=-1, resumable=True)

            request = self.youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media,
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    logger.info(f"Upload progress: {progress}%")

            video_id = response.get("id")
            if video_id:
                logger.info(f"Upload successful. Video ID: {video_id}")
                return True, video_id, None
            else:
                return False, None, "No video ID returned"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"YouTube upload error: {error_msg}")
            return False, None, error_msg


youtube_service = YouTubeService()