from pathlib import Path
from typing import Optional

from loguru import logger


class ParserService:
    """多模态文件解析器，支持文本、图片、音频、视频等文件类型。"""

    def __init__(self, llm_client=None):
        self._llm_client = llm_client
        logger.info("ParserService initialized")

    def parse_text_file(self, file_path: str) -> str:
        """解析纯文本文件，返回其内容。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Text file not found: {file_path}")

        encodings = ["utf-8", "gbk", "gb2312", "latin-1"]
        for enc in encodings:
            try:
                content = path.read_text(encoding=enc)
                logger.info(f"Parsed text file: {path.name}, encoding={enc}, chars={len(content)}")
                return content
            except (UnicodeDecodeError, UnicodeError):
                continue

        raise ValueError(f"Unable to decode text file: {file_path}")

    def parse_image_file(self, file_path: str) -> str:
        """解析图片文件，返回占位描述。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        description = f"[图片文件: {path.name}] 图片内容待通过视觉模型解析"
        logger.info(f"Parsed image file: {path.name}")
        return description

    def parse_audio_file(self, file_path: str) -> str:
        """解析音频文件，返回占位描述。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        description = f"[音频文件: {path.name}] 音频内容待通过语音识别转写"
        logger.info(f"Parsed audio file: {path.name}")
        return description

    def parse_video_file(self, file_path: str) -> str:
        """解析视频文件，返回占位描述。"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {file_path}")

        description = f"[视频文件: {path.name}] 视频内容待通过视频解析模块处理"
        logger.info(f"Parsed video file: {path.name}")
        return description

    def parse_file(self, file_path: str, file_type: str) -> str:
        """统一文件解析入口，根据文件类型路由到对应的解析器。"""
        file_type_lower = file_type.lower()

        parsers = {
            "text": self.parse_text_file,
            "txt": self.parse_text_file,
            "md": self.parse_text_file,
            "markdown": self.parse_text_file,
            "json": self.parse_text_file,
            "csv": self.parse_text_file,
            "xml": self.parse_text_file,
            "yaml": self.parse_text_file,
            "yml": self.parse_text_file,
            "log": self.parse_text_file,
            "image": self.parse_image_file,
            "jpg": self.parse_image_file,
            "jpeg": self.parse_image_file,
            "png": self.parse_image_file,
            "gif": self.parse_image_file,
            "webp": self.parse_image_file,
            "bmp": self.parse_image_file,
            "svg": self.parse_image_file,
            "audio": self.parse_audio_file,
            "mp3": self.parse_audio_file,
            "wav": self.parse_audio_file,
            "ogg": self.parse_audio_file,
            "flac": self.parse_audio_file,
            "aac": self.parse_audio_file,
            "m4a": self.parse_audio_file,
            "video": self.parse_video_file,
            "mp4": self.parse_video_file,
            "avi": self.parse_video_file,
            "mov": self.parse_video_file,
            "mkv": self.parse_video_file,
            "webm": self.parse_video_file,
            "flv": self.parse_video_file,
        }

        parser = parsers.get(file_type_lower)
        if parser is None:
            logger.warning(f"Unsupported file type: {file_type}, returning placeholder")
            return f"[不支持的文件类型: {file_type}] 文件 {file_path} 的类型暂不支持解析"

        return parser(file_path)