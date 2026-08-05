"""只读加载 API Key。

铁律：Key 只从现有文件读取，任何输出不得明文显示。
"""
from __future__ import annotations

import json
import os

CODEX_HOME = r"G:\codex-data\home"
AUTH_JSON = os.path.join(CODEX_HOME, "auth.json")
ENV_FILE = os.path.join(CODEX_HOME, ".env")
DEFAULT_SILICONFLOW_BASE = "https://api.siliconflow.cn/v1"


def _read_env_file() -> dict:
    data = {}
    try:
        with open(ENV_FILE, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                data[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return data


def deepseek_api_key() -> str | None:
    try:
        with open(AUTH_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        key = data.get("OPENAI_API_KEY")
        return str(key) if key else None
    except (OSError, ValueError):
        return None


def siliconflow_api_key() -> str | None:
    return _read_env_file().get("SILICONFLOW_API_KEY") or None


def siliconflow_base_url() -> str:
    return _read_env_file().get("SILICONFLOW_BASE_URL") or DEFAULT_SILICONFLOW_BASE


def key_status() -> dict:
    """仅返回是否存在及长度，绝不返回 Key 内容。"""
    dk = deepseek_api_key()
    sk = siliconflow_api_key()
    return {
        "deepseek": (dk is not None, len(dk) if dk else 0),
        "siliconflow": (sk is not None, len(sk) if sk else 0),
    }
