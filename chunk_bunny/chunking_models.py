from collections.abc import Generator
from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field

from enum import StrEnum


class Chunk(BaseModel):
    file_path: Path
    first_chunk_char: int
    last_chunk_char: int
    text: str
    type: str
    metadata: dict[str, Any] = Field(default={})
    breadcrumbs: list[str] = Field(default=[])

    def full_text(self, db) -> str:
        pass


class Literal(StrEnum):
    HEADER = "header"
    LITERAL = "literal"


class CodeBase(StrEnum):
    PY = "python"


class RecursiveLevel(BaseModel):
    delimiter: str
    mode: Literal | CodeBase
    include_delim: str


class BaseChunkingSettings(BaseModel):
    chunk_overlap: int
    recursive_rules: list[RecursiveLevel]


class MarkdownChunkingSettings(BaseChunkingSettings):
    pass


class CodeChunkingSettings(BaseChunkingSettings):
    pass
