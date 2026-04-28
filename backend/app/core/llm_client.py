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
        if "generativelanguage.googleapis.com" in self.base_url:
            if not self.model.startswith("gemini-"):
                logger.warning(f"[LLMClient] Google AI model should start with 'gemini-'. Current: {self.model}")
        
        # Removed the restrictive DeepSeek Anthropic check to allow flexible provider endpoints

    def _normalize_url(self, endpoint: str) -> str:
        """Ensure base_url and endpoint are combined correctly with protocol-specific paths"""
        url = self.base_url.rstrip('/')
        
        # Avoid adding /v1 if it's already part of the base_url
        if self.api_type == "openai" and "/v1" not in url:
            url += "/v1"
        elif self.api_type == "anthropic" and "/v1" not in url:
            url += "/v1"
            
        return f"{url}/{endpoint.lstrip('/')}"

    async def get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            async with self._client_lock:
                if self._client is None:
                    # Google AI API uses ?key=API_KEY instead of Bearer token
                    headers = {"Content-Type": "application/json"}
                    if self.api_type != "google":
                        headers["Authorization"] = f"Bearer {self.api_key}"
                    
                    self._client = httpx.AsyncClient(
                        timeout=self.timeout,
                        headers=headers,
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
        elif self.api_type == "google":
            return await self.circuit_breaker.call(
                self._google_chat, messages, temperature, max_tokens
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

        logger.info(f"[LLMClient] {self.provider} (OpenAI) request: model={self.model}, messages={len(messages)}")

        try:
            client = await self.get_client()
            url = self._normalize_url("chat/completions")
            response = await client.post(url, json=payload)
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

    async def _google_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        # Google AI Studio format: /v1beta/models/{model}:generateContent?key={api_key}
        # Ensure the model name is prefixed with 'models/' if not already present
        model_name = self.model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
            
        url = f"{self.base_url.rstrip('/')}/v1beta/{model_name}:generateContent?key={self.api_key}"
        
        # Convert messages to Google format
        contents = []
        for msg in messages:
            if msg["role"] == "user":
                contents.append({"role": "user", "parts": [{"text": msg["content"]}]})
            elif msg["role"] == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg["content"]}]})
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            }
        }
        
        logger.info(f"[LLMClient] {self.provider} (Google) request: model={self.model}")
        try:
            client = await self.get_client()
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            
            # Extract content from Google response
            candidates = data.get("candidates", [])
            if not candidates:
                raise LLMConnectionError("Google API returned no candidates")
            
            content = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not content:
                raise LLMConnectionError("Google API returned empty content")
                
            # Google tokens are in usageMetadata
            usage = data.get("usageMetadata", {})
            return LLMResponse(
                content=content,
                input_tokens=usage.get("promptTokenCount", 0),
                output_tokens=usage.get("candidatesTokenCount", 0)
            )
        except Exception as e:
            raise LLMConnectionError(f"Google API Error: {str(e)}")

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

        # Anthropic requires specific headers
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        try:
            client = await self.get_client()
            # Use normalized URL for the endpoint
            url = self._normalize_url("messages")
            response = await client.post(url, json=payload, headers=headers)
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
