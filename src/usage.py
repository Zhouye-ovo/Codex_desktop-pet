"""今日用量统计（本地数据）。

DeepSeek：解析 G:\\codex-data\\home\\sessions 下 rollout-*.jsonl，
  payload.type == "token_count" 的 info.last_token_usage 增量求和（按本地日期过滤）。
识图：读取 G:\\codex-data\\home\\vision-usage.jsonl 记账文件求和。
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import time

from . import keys

_FRAC_RE = re.compile(r"\.(\d{6})\d+")


def _parse_ts(ts: str) -> _dt.datetime | None:
    if not ts:
        return None
    ts = _FRAC_RE.sub(r".\1", ts)
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    try:
        return _dt.datetime.fromisoformat(ts)
    except ValueError:
        return None


def _local_today(ts: str) -> bool:
    dt = _parse_ts(ts)
    return bool(dt and dt.astimezone().date() == _dt.date.today())


class _Cache:
    def __init__(self) -> None:
        self.value = 0
        self.expire = 0.0

    def get(self, func) -> int:
        now = time.time()
        if now >= self.expire:
            self.value = func()
            self.expire = now + 30.0
        return self.value


_deepseek_cache = _Cache()
_vision_cache = _Cache()


def deepseek_today_tokens() -> int:
    return _deepseek_cache.get(_compute_deepseek)


def vision_today_tokens() -> int:
    return _vision_cache.get(_compute_vision)


def _compute_deepseek() -> int:
    sessions_root = os.path.join(keys.CODEX_HOME, "sessions")
    total = 0
    if not os.path.isdir(sessions_root):
        return 0
    for dirpath, _dirs, files in os.walk(sessions_root):
        for fn in files:
            if not fn.startswith("rollout-") or not fn.endswith(".jsonl"):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line or '"token_count"' not in line:
                            continue
                        try:
                            obj = json.loads(line)
                        except ValueError:
                            continue
                        payload = obj.get("payload") or {}
                        if payload.get("type") != "token_count":
                            continue
                        if not _local_today(obj.get("timestamp")):
                            continue
                        info = payload.get("info") or {}
                        last = info.get("last_token_usage") or {}
                        total += int(last.get("input_tokens") or 0)
                        total += int(last.get("output_tokens") or 0)
            except OSError:
                continue
    return total


def _compute_vision() -> int:
    usage_file = os.path.join(keys.CODEX_HOME, "vision-usage.jsonl")
    total = 0
    if not os.path.isfile(usage_file):
        return 0
    try:
        with open(usage_file, "r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if not _local_today(rec.get("time")):
                    continue
                total += int(rec.get("input_tokens") or 0)
                total += int(rec.get("output_tokens") or 0)
    except OSError:
        return 0
    return total
