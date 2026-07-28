import os
import shutil
from pathlib import Path
from loguru import logger

from app.config import config


class StorageService:
    """Local storage service simulating object storage using the file system."""

    def __init__(self):
        storage_cfg = config.storage
        self._local_path = Path(storage_cfg.get("local_path", "./data/storage"))
        self._local_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"StorageService initialized, local_path={self._local_path}")

    def _resolve_path(self, key: str) -> Path:
        return self._local_path / key

    def download_file(self, key: str, local_path: str) -> str:
        """Download a file from storage to a local path."""
        src = self._resolve_path(key)
        if not src.exists():
            raise FileNotFoundError(f"File not found in storage: key={key}")
        dst = Path(local_path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        logger.info(f"Downloaded file: key={key} -> {dst}")
        return str(dst)

    def upload_file(self, local_path: str, key: str) -> str:
        """Upload a local file to storage."""
        src = Path(local_path)
        if not src.exists():
            raise FileNotFoundError(f"Local file not found: {local_path}")
        dst = self._resolve_path(key)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        logger.info(f"Uploaded file: {local_path} -> key={key}")
        return str(dst)

    def download_content(self, key: str) -> str:
        """Download a file from storage and return its text content."""
        src = self._resolve_path(key)
        if not src.exists():
            raise FileNotFoundError(f"File not found in storage: key={key}")
        content = src.read_text(encoding="utf-8")
        logger.info(f"Downloaded content: key={key}, size={len(content)} chars")
        return content

    def delete_directory(self, prefix: str) -> bool:
        """Delete all files under a given prefix directory."""
        target = self._resolve_path(prefix)
        if target.exists() and target.is_dir():
            shutil.rmtree(target)
            logger.info(f"Deleted directory: {target}")
            return True
        elif target.exists():
            target.unlink()
            logger.info(f"Deleted file: {target}")
            return True
        logger.warning(f"Path not found for deletion: {target}")
        return False