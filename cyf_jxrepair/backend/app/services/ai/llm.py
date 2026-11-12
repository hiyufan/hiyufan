"""可选的大模型调用（兼容 OpenAI Chat Completions 协议，如 DeepSeek、通义千问、Kimi 等）。

未在 .env 中配置 LLM_API_KEY 时不会发起任何网络请求；调用失败时返回 None，
由上层自动降级为本地离线方案，保证考场无外网也能演示。
只用标准库 urllib，不额外引入 HTTP 依赖。
"""
import json
import logging
import re
import urllib.error
import urllib.request

from app.core.config import settings

logger = logging.getLogger("cyf.jxrepair")

_JSON_BLOCK = re.compile(r"\{.*\}", re.S)


def chat_json(system_prompt: str, user_prompt: str) -> dict | None:
    if not settings.llm_enabled:
        return None
    payload = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    request = urllib.request.Request(
        f"{settings.llm_base_url.rstrip('/')}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=settings.llm_timeout_seconds) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        match = _JSON_BLOCK.search(content)  # 模型有时会在 JSON 外包一层 ```json 代码块
        return json.loads(match.group(0)) if match else None
    except (urllib.error.URLError, TimeoutError, KeyError, IndexError, ValueError) as exc:
        logger.warning("大模型调用失败，降级为本地方案: %s", exc)
        return None
