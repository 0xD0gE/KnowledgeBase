#!/usr/bin/env python3
"""
llm_client.py

統一封裝 Claude (Anthropic) 和 OpenAI，對外提供一致的呼叫介面。
由 answer_issue.py 引用，不直接執行。
"""

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMResponse:
    """LLM 回應的統一格式。"""
    content: str            # 最終回答（Markdown 格式）
    model: str              # 使用的模型名稱
    provider: str           # "anthropic" 或 "openai"
    tokens_used: int        # 總消耗 token 數
    found_answer: bool      # True: 知識庫有答案; False: 無法從現有文件回答
    confidence: float       # 0.0 ~ 1.0，AI 的信心分數
    source_docs: list = field(default_factory=list)  # 參考的文件路徑


def _parse_llm_json(raw: str) -> dict:
    """
    解析 LLM 輸出中的 JSON 區塊。
    LLM 被要求將結構化回應包在 ```json ... ``` 中。
    若解析失敗，回傳預設值（視為有回答但信心低）。
    """
    # 嘗試擷取 ```json ... ``` 區塊
    match = re.search(r"```json\s*\n([\s\S]*?)\n```", raw, re.IGNORECASE)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 嘗試直接解析整個輸出
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Fallback：無法解析，把 raw 當作答案
    return {
        "found_answer": True,
        "confidence": 0.4,
        "answer": raw.strip(),
        "source_docs": [],
    }


class BaseLLMClient(ABC):
    """所有 LLM 客戶端的抽象基類。"""

    @abstractmethod
    def chat(self, system_prompt: str, user_message: str) -> LLMResponse:
        """傳入 system prompt 和 user message，回傳 LLMResponse。"""

    @abstractmethod
    def is_available(self) -> bool:
        """檢查此 provider 的 API Key 是否存在。"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider 名稱（anthropic / openai）。"""


class AnthropicClient(BaseLLMClient):
    """Claude (Anthropic) LLM 客戶端。"""

    def __init__(self):
        self._api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-6")

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def chat(self, system_prompt: str, user_message: str) -> LLMResponse:
        import anthropic  # lazy import，只有在使用時才 import

        client = anthropic.Anthropic(api_key=self._api_key)
        message = client.messages.create(
            model=self._model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_content = message.content[0].text
        parsed = _parse_llm_json(raw_content)
        tokens = message.usage.input_tokens + message.usage.output_tokens

        return LLMResponse(
            content=parsed.get("answer", raw_content),
            model=self._model,
            provider=self.provider_name,
            tokens_used=tokens,
            found_answer=bool(parsed.get("found_answer", True)),
            confidence=float(parsed.get("confidence", 0.5)),
            source_docs=parsed.get("source_docs", []),
        )


class OpenAIClient(BaseLLMClient):
    """OpenAI GPT 客戶端。"""

    def __init__(self):
        self._api_key = os.environ.get("OPENAI_API_KEY", "")
        self._model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    @property
    def provider_name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def chat(self, system_prompt: str, user_message: str) -> LLMResponse:
        from openai import OpenAI  # lazy import

        client = OpenAI(api_key=self._api_key)
        completion = client.chat.completions.create(
            model=self._model,
            max_tokens=2048,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

        raw_content = completion.choices[0].message.content or ""
        parsed = _parse_llm_json(raw_content)
        tokens = completion.usage.total_tokens if completion.usage else 0

        return LLMResponse(
            content=parsed.get("answer", raw_content),
            model=self._model,
            provider=self.provider_name,
            tokens_used=tokens,
            found_answer=bool(parsed.get("found_answer", True)),
            confidence=float(parsed.get("confidence", 0.5)),
            source_docs=parsed.get("source_docs", []),
        )


def create_llm_client(provider: str | None = None) -> BaseLLMClient:
    """
    根據 provider 名稱建立 LLM 客戶端。
    若指定的 provider 無 API Key，自動 fallback 到另一個。

    優先順序：
    1. 傳入的 provider 參數
    2. 環境變數 LLM_PROVIDER
    3. 預設 anthropic
    """
    if provider is None:
        provider = os.environ.get("LLM_PROVIDER", "anthropic").lower().strip()

    candidates = (
        [AnthropicClient(), OpenAIClient()]
        if provider == "anthropic"
        else [OpenAIClient(), AnthropicClient()]
    )

    for client in candidates:
        if client.is_available():
            print(f"[LLM] Using provider: {client.provider_name}")
            return client

    raise RuntimeError(
        "No LLM API Key available. "
        "Please set ANTHROPIC_API_KEY or OPENAI_API_KEY in GitHub Secrets."
    )
