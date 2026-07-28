from typing import Any, Optional
from pydantic import BaseModel, Field


class MemoryFileInfo(BaseModel):
    file_key: str
    file_type: str
    file_name: str


class MemoryParseRequest(BaseModel):
    user_id: str
    role_id: str
    memory_id: str
    theme_name: str
    subjective_desc: str = ""
    files: list[MemoryFileInfo] = Field(default_factory=list)


class MemoryFileDeleteRequest(BaseModel):
    user_id: str
    role_id: str
    memory_id: str
    file_key: str
    file_name: str


class MemoryThemeDeleteRequest(BaseModel):
    user_id: str
    role_id: str
    memory_id: str


class APIResponse(BaseModel):
    code: int
    message: str
    data: Optional[Any] = None