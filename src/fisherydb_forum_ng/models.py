from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class FileInventory:
    path: str
    suffix: str
    size_bytes: int


@dataclass
class LocalInventory:
    root: str
    total_files: int = 0
    by_extension: dict[str, int] = field(default_factory=dict)
    json_files: list[FileInventory] = field(default_factory=list)
    html_files: list[FileInventory] = field(default_factory=list)
    markdown_files: list[FileInventory] = field(default_factory=list)
    attachment_like_files: list[FileInventory] = field(default_factory=list)
    candidate_forum_files: list[str] = field(default_factory=list)
    detected_counts: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


ATTACHMENT_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png",
    ".gif", ".webp", ".zip", ".rar", ".7z", ".txt", ".csv"
}
