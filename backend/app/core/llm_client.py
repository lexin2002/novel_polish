"""Unified LLM API client - supports OpenAI-compatible and Anthropic-compatible APIs"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
from app.core.rate_limiter import AsyncTokenBucket, CircuitBreaker

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """LLM API response with content and token usage"""
    content: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class LLMClient:
    """
    Unified LLM client that works with OpenAI-compatible and Anthropic-compatible APIs.
    """

    SUPPORTED_API_TYPES = {"openai", "anthropic"}
    
    PROVIDER_MODEL_PATTERNS = {
        "deepseek": ["deepseek-chat", "deepseek-reasoner", "deepseek-coder"],
        "openai": ["gpt-", "o1-", "o3-"],
        "anthropic": ["claude-"],
        "google": ["gemini-"],
    }
    
    PROVIDER_BASE_URL_PATTERNS = {
        "deepseek": ["api.deepseek.com"],
        "openai": ["api.openai.com"],
        "anthropic": ["api.anthropic.com"],
        "google": ["generativelanguage.googleapis.com"],
    }

    def __init__(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
        api_type: str | None = None,
        timeout: float = 60.0,
    ):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url if base_url.endswith("/") else base_url + "/"
        self.model = model
        self.api_type = api_type or self._detect_api_type(self.base_url)
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()
        
        # Circuit Breaker to prevent API spamming during failures
        self.circuit_breaker = CircuitBreaker(threshold=3, recovery_timeout=30.0)

        self._validate_config()

    def _validate_config(self) -> None:
        if "deepseek.com" in self.base_url:
            if "/anthropic" in self.base_url or "/v1/messages" in self.base_url:
                logger.error(f"[LLMClient] DEEPSEEK MISCONFIGURATION DETECTED! base_url={self.base_url}")
            elif not any(p in self.base_url for p in ["/v1/", "/v1/chat"]):
                logger.warning(f"[LLMClient] DeepSeek base_url may be missing API path. Current: {self.base_url}")

        if "deepseek.com" in self.base_url:
            valid_models = self.PROVIDER_MODEL_PATTERNS.get("deepseek", [])
            if not any(m in self.model for m in valid_models):
                logger.error(f"[LLMClient] INVALID DEEPSEEK MODEL NAME! model={self.model}")

        if "generativelanguage.googleapis.com" in self.base_url:
            if not self.model.startswith("gemini-"):
                logger.warning(f"[LLMClient] Google AI model should start with 'gemini-'. Current: {self.model}")

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            async with self._client_lock:
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

    def _detect_api_type(self, base_url: str) -> str:
        if not base_url: return "openai"
        if "anthropic.com" in base_url: return "anthropic"
        return "openai"

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def chatcompletion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Send chat completion request wrapped in a circuit breaker.
        """
        if self.api_type == "anthropic":
            return await self.circuit_breaker.call(
                self._anthropic_chat, messages, temperature, max_tokens
            )
        else:
            return await self.circuit_breaker.call(
                self._openai_compatible_chat, messages, temperature, max_tokens
            )

    async def _openai_compatible_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"[LLMClient] {self.provider} request: model={self.model}, messages={len(messages)}")

        try:
            client = await self.get_client()
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            error_detail = ""
            try:
                error_json = e.response.json()
                error_detail = error_json.get("error", {}).get("message", e.response.text[:200])
            except Exception:
                error_detail = e.response.text[:200]

            if e.response.status_code == 401:
                raise LLMConnectionError(f"Auth failed (401): {error_detail}")
            elif e.response.status_code == 403:
                raise LLMConnectionError(f"Forbidden (403): {error_detail}")
            elif e.response.status_code == 404:
                raise LLMConnectionError(f"Model not found (404): {self.model}. {error_detail}")
            elif e.response.status_code == 429:
                raise LLMConnectionError(f"Rate limit exceeded (429): {error_detail}")
            else:
                raise LLMConnectionError(f"API Error ({e.response.status_code}): {error_detail}")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"Network failure: {str(e)}")

        data = response.json()
        # --- DEBUG: Simulate DeepSeek Reasoner (R1) response ---
        if "reasoner" in self.model:
            data["choices"][0]["message"]["content"] = None
            data["choices"][0]["message"]["reasoning_content"] = "Thinking..."
            data["choices"][0]["message"]["content"] = "Simulated Reasoned Result"
        # -------------------------------------------------------
        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)
        
        choices = data.get("choices", [])
        if not choices:
            raise LLMConnectionError("API returned no choices")
        
        message = choices[0].get("message", {})
        content = message.get("content")
        if content is None:
            content = message.get("reasoning_content")
        if not content:
            raise LLMConnectionError("API returned empty content")
            
        return LLMResponse(content=content, input_tokens=input_tokens, output_tokens=output_tokens)

    async def _anthropic_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        system_msg = ""
        anthropic_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                anthropic_messages.append({"role": msg["role"], "content": msg["content"]})

        payload = {"model": self.model, "messages": anthropic_messages, "temperature": temperature, "max_tokens": max_tokens}
        if system_msg: payload["system"] = system_msg

        headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01", "content-type": "application/json"}

        try:
            client = await self.get_client()
            response = await client.post("/messages", json=payload, headers=headers)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMConnectionError(f"Anthropic API Error ({e.response.status_code}): {e.response.text[:200]}")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"Anthropic Network failure: {str(e)}")

        data = response.json()
        usage = data.get("usage", {})
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        
        content = data.get("content", [])
        text_content = ""
        if content and isinstance(content, list):
            for item in content:
                if item.get("type") == "text" or (item.get("type") is None and "text" in item):
                    text_content = item.get("text", "")
                    break
        if not text_content:
            if "text" in data: text_content = data["text"]
            elif "message" in data and isinstance(data["message"], dict) and "content" in data["message"]:
                text_content = data["message"]["content"]
        
        if not text_content:
            raise LLMConnectionError(f"Anthropic response format unknown")
            
        return LLMResponse(content=text_content, input_tokens=input_tokens, output_tokens=output_tokens)

    async def test_connection(self) -> dict:
        test_messages = [{"role": "user", "content": "Hello, reply with just the word 'OK'."}]
        try:
            result = await self.chatcompletion(messages=test_messages, temperature=0.1, max_tokens=200)
            if not result or not result.content or len(result.content.strip()) == 0:
                raise LLMConnectionError("Empty response")
            return {"ok": True, "model": self.model, "response": result.content.strip()[:100]}
        except LLMConnectionError:
            raise
        except Exception as e:
            raise LLMConnectionError(f"Connection test failed: {str(e)}")

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
    return LLMClient(provider=provider, api_key=api_key, base_url=base_url, model=model, api_type=api_type, timeout=timeout)
