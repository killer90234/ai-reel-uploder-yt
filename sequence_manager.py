import re
import logging
from typing import Optional
from config import settings
from logger_service import logger_service


logger = logging.getLogger(__name__)


class SequenceManager:
    VIDEO_PATTERN = re.compile(r"^ota(\d+)\.(mp4|mov|mkv|avi)$", re.IGNORECASE)

    def __init__(self):
        self.last_uploaded_seq: int = logger_service.get_last_uploaded_sequence()
        logger.info(f"SequenceManager initialized. Last uploaded sequence: {self.last_uploaded_seq}")

    def extract_sequence_number(self, filename: str) -> Optional[int]:
        match = self.VIDEO_PATTERN.match(filename.strip())
        if match:
            return int(match.group(1))
        return None

    def is_valid_reel_filename(self, filename: str) -> bool:
        return self.extract_sequence_number(filename) is not None

    def get_next_pending_sequence(self, available_files: list[str]) -> Optional[int]:
        uploaded_seq = self.last_uploaded_seq

        valid_files = []
        for f in available_files:
            seq = self.extract_sequence_number(f)
            if seq is not None:
                valid_files.append((seq, f))

        valid_files.sort(key=lambda x: x[0])

        for seq, filename in valid_files:
            if seq == uploaded_seq + 1:
                return seq

        return None

    def get_next_pending_file(self, available_files: list[str]) -> Optional[tuple[int, str]]:
        next_seq = self.get_next_pending_sequence(available_files)
        if next_seq is None:
            return None

        for f in available_files:
            seq = self.extract_sequence_number(f)
            if seq == next_seq:
                return (seq, f)

        return None

    def mark_uploaded(self, filename: str):
        seq = self.extract_sequence_number(filename)
        if seq and seq > self.last_uploaded_seq:
            self.last_uploaded_seq = seq
            logger.info(f"Marked sequence {seq} as uploaded. Next expected: {self.last_uploaded_seq + 1}")

    def get_status(self) -> dict:
        return {
            "last_uploaded_sequence": self.last_uploaded_seq,
            "next_expected_sequence": self.last_uploaded_seq + 1,
        }


sequence_manager = SequenceManager()