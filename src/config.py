"""配置读写：config.json 位于项目根目录（已加入 .gitignore）。"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")

SCALE_OPTIONS = [80, 100, 120, 150]
DEFAULT_REFRESH_MINUTES = 10
DEFAULT_BG = "assets/bg.png"


@dataclass
class Config:
    pos: list | None = None  # [x, y]
    topmost: bool = True
    scale: int = 100
    refresh_minutes: int = DEFAULT_REFRESH_MINUTES
    bg: str = DEFAULT_BG

    @classmethod
    def load(cls) -> "Config":
        cfg = cls()
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            cfg.pos = data.get("pos")
            cfg.topmost = bool(data.get("topmost", True))
            cfg.scale = int(data.get("scale", 100))
            cfg.refresh_minutes = int(data.get("refresh_minutes", DEFAULT_REFRESH_MINUTES))
            cfg.bg = str(data.get("bg", DEFAULT_BG))
        except (FileNotFoundError, ValueError, TypeError, OSError):
            pass
        cfg.refresh_minutes = max(1, min(1440, cfg.refresh_minutes))
        cfg.scale = min(SCALE_OPTIONS, key=lambda s: abs(s - cfg.scale))
        return cfg

    def save(self) -> None:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(asdict(self), f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    def bg_abs(self) -> str:
        p = self.bg
        if not os.path.isabs(p):
            p = os.path.join(PROJECT_ROOT, p)
        return p
