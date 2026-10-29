from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


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

    @classmethod
    def from_env(cls) -> Settings:
        data_dir = Path(os.getenv("AD_AUTOMATION_DATA_DIR", PROJECT_ROOT / "ad_automation_data"))
        return cls(data_dir=data_dir)
