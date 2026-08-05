"""余额 Provider 适配器：每个模型一个独立适配器，便于以后扩展。"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from . import keys

TIMEOUT = 10


@dataclass
class BalanceResult:
    provider: str
    amount: float | None
    currency: str = "CNY"
    available: bool | None = None
    error: str | None = None


def _http_json(url: str, api_key: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _safe(err: Exception) -> str:
    """把异常转成不含 Key 的安全描述。"""
    msg = str(err)
    if len(msg) > 200:
        msg = msg[:200] + "..."
    return msg


class DeepSeekProvider:
    name = "DeepSeek"
    url = "https://api.deepseek.com/user/balance"

    def fetch(self) -> BalanceResult:
        key = keys.deepseek_api_key()
        if not key:
            return BalanceResult(self.name, None, error="未找到 DeepSeek Key（auth.json 的 OPENAI_API_KEY）")
        try:
            data = _http_json(self.url, key)
        except urllib.error.HTTPError as e:
            return BalanceResult(self.name, None, error=f"DeepSeek 接口 HTTP {e.code}")
        except Exception as e:
            return BalanceResult(self.name, None, error=f"DeepSeek 请求失败: {_safe(e)}")
        try:
            infos = data.get("balance_infos") or []
            info = next((i for i in infos if str(i.get("currency", "")).upper() == "CNY"), None)
            if info is None and infos:
                info = infos[0]
            if info is None:
                return BalanceResult(self.name, None, error="DeepSeek 响应中没有 balance_infos")
            return BalanceResult(
                self.name,
                float(info.get("total_balance", 0)),
                currency=str(info.get("currency", "CNY")),
                available=bool(data.get("is_available")),
            )
        except Exception as e:
            return BalanceResult(self.name, None, error=f"DeepSeek 解析失败: {_safe(e)}")


class SiliconFlowProvider:
    name = "识图（硅基流动）"

    def __init__(self) -> None:
        self.url = keys.siliconflow_base_url().rstrip("/") + "/user/info"

    def fetch(self) -> BalanceResult:
        key = keys.siliconflow_api_key()
        if not key:
            return BalanceResult(self.name, None, error="未找到硅基流动 Key（.env 的 SILICONFLOW_API_KEY）")
        try:
            data = _http_json(self.url, key)
        except urllib.error.HTTPError as e:
            return BalanceResult(self.name, None, error=f"硅基流动接口 HTTP {e.code}")
        except Exception as e:
            return BalanceResult(self.name, None, error=f"硅基流动请求失败: {_safe(e)}")
        try:
            payload = data.get("data") or data
            amount = payload.get("balance")
            if amount is None:
                amount = payload.get("totalBalance") or payload.get("chargeBalance")
            if amount is None:
                return BalanceResult(self.name, None, error="硅基流动响应中没有 balance 字段")
            return BalanceResult(self.name, float(amount), currency="CNY")
        except Exception as e:
            return BalanceResult(self.name, None, error=f"硅基流动解析失败: {_safe(e)}")
