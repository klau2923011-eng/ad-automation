from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def find_media_binary(name: str) -> str | None:
    executable = f"{name}.exe" if os.name == "nt" else name
    found = shutil.which(name)
    if found:
        return found
    root = Path(os.getenv("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    matches = sorted(root.glob(f"Gyan.FFmpeg.Shared_*/*/bin/{executable}"))
    return str(matches[-1]) if matches else None


@dataclass(frozen=True)
class Settings:
    data_dir: Path

    def __post_init__(self) -> None:
        resolved = self.data_dir.expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "data_dir", resolved)

    @property
    def database_path(self) -> Path:
        return self.data_dir / "ad_automation.sqlite3"

    @property
    def ffmpeg_path(self) -> str | None:
        return os.getenv("AD_AUTOMATION_FFMPEG") or find_media_binary("ffmpeg")

    @property
    def ffprobe_path(self) -> str | None:
        return os.getenv("AD_AUTOMATION_FFPROBE") or find_media_binary("ffprobe")

    @classmethod
    def from_env(cls) -> Settings:
        data_dir = Path(os.getenv("AD_AUTOMATION_DATA_DIR", PROJECT_ROOT / "ad_automation_data"))
        return cls(data_dir=data_dir)
