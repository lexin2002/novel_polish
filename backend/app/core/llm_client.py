"""Unified LLM API client - supports OpenAI-compatible and Anthropic-compatible APIs"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client that works with OpenAI-compatible and Anthropic-compatible APIs.

    api_type determines which API protocol to use:
    - "openai": OpenAI-compatible (/v1/chat/completions) - works with OpenAI, DeepSeek, Qwen, etc.
    - "anthropic": Anthropic API (/v1/messages) - works with Anthropic
    """

    SUPPORTED_API_TYPES = {"openai", "anthropic"}

    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
        api_type: str = "openai",
        timeout: float = 60.0,
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_type = api_type  # "openai" or "anthropic" - user-configured
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chatcompletion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """
        Send chat completion request using api_type.
        - "openai": OpenAI-compatible API (/v1/chat/completions)
        - "anthropic": Anthropic API (/v1/messages)
        """
        if self.api_type == "anthropic":
            return await self._anthropic_chat(messages, temperature, max_tokens)
        else:
            return await self._openai_compatible_chat(messages, temperature, max_tokens)

    async def _openai_compatible_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """OpenAI-compatible chat completions API (/v1/chat/completions)"""
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(
            f"[LLMClient] {self.provider} request: model={self.model}, "
            f"messages={len(messages)}, base_url={self.base_url}"
        )

        try:
            response = await self.client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMConnectionError(f"认证失败: API Key 无效或已过期 (401)")
            elif e.response.status_code == 403:
                raise LLMConnectionError(f"访问被拒绝: 权限不足 (403)")
            elif e.response.status_code == 404:
                raise LLMConnectionError(f"模型不存在或端点错误: {self.model} (404)")
            elif e.response.status_code == 429:
                raise LLMConnectionError(f"请求频率超限，请稍后重试 (429)")
            else:
                raise LLMConnectionError(f"API 请求失败 ({e.response.status_code}): {e.response.text[:200]}")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"网络连接失败: {str(e)}")

        data = response.json()
        usage = data.get("usage", {})
        logger.info(
            f"[LLMClient] {self.provider} response: "
            f"tokens={usage.get('total_tokens', 'N/A')}"
        )

        choices = data.get("choices", [])
        if not choices:
            raise LLMConnectionError("API 返回格式错误: 缺少 choices 字段")

        return choices[0]["message"]["content"]

    async def _anthropic_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Anthropic API (/v1/messages)"""
        # Convert OpenAI messages format to Anthropic format
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        payload = {
            "model": self.model,
            "messages": anthropic_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if system_msg:
            payload["system"] = system_msg

        logger.info(
            f"[LLMClient] anthropic request: model={self.model}, "
            f"messages={len(anthropic_messages)}, base_url={self.base_url}"
        )

        # Anthropic uses x-api-key header
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

        try:
            response = await self.client.post(
                "/messages",
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise LLMConnectionError(f"认证失败: API Key 无效或已过期 (401)")
            elif e.response.status_code == 403:
                raise LLMConnectionError(f"访问被拒绝: 权限不足 (403)")
            elif e.response.status_code == 404:
                raise LLMConnectionError(f"模型不存在: {self.model} (404)")
            elif e.response.status_code == 429:
                raise LLMConnectionError(f"请求频率超限，请稍后重试 (429)")
            else:
                raise LLMConnectionError(f"API 请求失败 ({e.response.status_code}): {e.response.text[:200]}")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"网络连接失败: {str(e)}")

        data = response.json()
        logger.info(
            f"[LLMClient] anthropic response: tokens={data.get('usage', {}).get('input_tokens', 0) + data.get('usage', {}).get('output_tokens', 0)}"
        )

        return data["content"][0]["text"]

    async def test_connection(self) -> dict:
        """
        Test the connection with current credentials.
        Returns {"ok": True, "model": "..."} on success.
        Raises LLMConnectionError on failure.
        """
        test_messages = [
            {"role": "user", "content": "Hello, reply with just the word 'OK'."}
        ]
        try:
            result = await self.chatcompletion(
                messages=test_messages,
                temperature=0.1,
                max_tokens=20,
            )
            # Verify response is meaningful
            if not result or len(result.strip()) == 0:
                raise LLMConnectionError("API 返回为空响应")
            return {"ok": True, "model": self.model, "response": result.strip()[:100]}
        except LLMConnectionError:
            raise
        except Exception as e:
            raise LLMConnectionError(f"连接测试失败: {str(e)}")


class LLMConnectionError(Exception):
    """Raised when LLM API connection/test fails"""
    pass


async def create_llm_client(
    provider: str,
    api_key: str,
    base_url: str,
    model: str,
    api_type: str = "openai",
    timeout: float = 60.0,
) -> LLMClient:
    """Factory to create an LLM client."""
    return LLMClient(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        api_type=api_type,
        timeout=timeout,
    )
