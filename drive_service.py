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


logger = logging.getLogger(__name__)

ALL_SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/youtube.upload",
]
SCOPES = ALL_SCOPES


class GoogleDriveService:
    def __init__(self):
        self.creds: Optional[Credentials] = None
        self.drive_service = None
        self._authenticate_drive()

    def _authenticate_drive(self):
        creds_path = settings.get_credentials_path()
        token_path = settings.get_youtube_token_path()

        if token_path.exists():
            self.creds = Credentials.from_authorized_user_info(json.loads(token_path.read_text(encoding="utf-8")), SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            elif creds_path.exists():
                flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), SCOPES)
                self.creds = flow.run_local_server(port=0)
            else:
                logger.error(f"Google credentials file not found: {creds_path}")
                return

            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(self.creds.to_json(), encoding="utf-8")

        self.drive_service = build("drive", "v3", credentials=self.creds)
        logger.info("Google Drive authenticated successfully")

    def list_files_in_folder(self, folder_id: str, subfolder: str = "") -> list[dict]:
        if not self.drive_service:
            return []

        parent_id = folder_id
        if subfolder:
            subfolder_id = self._find_subfolder(parent_id, subfolder)
            if not subfolder_id:
                logger.warning(f"Subfolder '{subfolder}' not found in Drive folder")
                return []
            parent_id = subfolder_id

        query = f"'{parent_id}' in parents and trashed=false"
        try:
            results = (
                self.drive_service.files()
                .list(
                    q=query,
                    fields="files(id, name, mimeType)",
                    pageSize=100,
                )
                .execute()
            )
            files = results.get("files", [])
            logger.info(f"Found {len(files)} files in folder {subfolder or 'root'}")
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def _find_subfolder(self, parent_id: str, subfolder_name: str) -> Optional[str]:
        query = f"'{parent_id}' in parents and name='{subfolder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = self.drive_service.files().list(q=query, fields="files(id, name)").execute()
        folders = results.get("files", [])
        return folders[0]["id"] if folders else None

    def download_file(self, file_id: str, destination: Path) -> bool:
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            with open(destination, "wb") as f:
                f.write(request.execute())
            logger.info(f"Downloaded file to {destination}")
            return True
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False

    def move_file(self, file_id: str, target_folder_id: str) -> bool:
        try:
            file = self.drive_service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(file.get("parents", []))

            self.drive_service.files().update(
                fileId=file_id,
                addParents=target_folder_id,
                removeParents=previous_parents,
            ).execute()
            logger.info(f"Moved file {file_id} to folder {target_folder_id}")
            return True
        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False

    def delete_file(self, file_id: str) -> bool:
        try:
            self.drive_service.files().delete(fileId=file_id).execute()
            logger.info(f"Deleted file {file_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def get_folder_structure(self, folder_id: str) -> dict:
        if not self.drive_service:
            return {}

        folders = {
            "root": folder_id,
            "upload": self._get_or_create_folder(folder_id, settings.upload_subfolder),
            "uploaded": self._get_or_create_folder(folder_id, "uploaded"),
            "failed": self._get_or_create_folder(folder_id, "failed"),
        }
        return folders

    def _get_or_create_folder(self, parent_id: str, name: str) -> str:
        folder_id = self._find_subfolder(parent_id, name)
        if folder_id:
            return folder_id

        try:
            file_metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
            folder = self.drive_service.files().create(body=file_metadata, fields="id").execute()
            logger.info(f"Created folder '{name}' with ID {folder.get('id')}")
            return folder.get("id")
        except Exception as e:
            logger.error(f"Error creating folder '{name}': {e}")
            return ""


drive_service = GoogleDriveService()