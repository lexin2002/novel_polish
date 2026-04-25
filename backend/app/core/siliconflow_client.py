"""SiliconFlow API client for LLM text polishing"""

import logging
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class SiliconFlowClient:
    """Client for SiliconFlow API (THUDM/GLM-4-32B-0414)"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.siliconflow.cn",
        model: str = "THUDM/GLM-4-32B-0414",
        timeout: float = 120.0,
    ):
        """
        Initialize SiliconFlow client.

        Args:
            api_key: SiliconFlow API key
            base_url: API base URL
            model: Model name
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
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
        """Close the HTTP client"""
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
        Send chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text response

        Raises:
            httpx.HTTPStatusError: On API error
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        logger.info(f"SiliconFlow request: model={self.model}, messages={len(messages)}")
        logger.debug(f"Request payload: {payload}")

        response = await self.client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()

        data = response.json()
        logger.info(f"SiliconFlow response: tokens={data.get('usage', {}).get('total_tokens', 'N/A')}")

        # Extract response content
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("No choices in SiliconFlow response")

        return choices[0]["message"]["content"]


async def create_siliconflow_client(
    api_key: str,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> SiliconFlowClient:
    """
    Factory function to create SiliconFlow client.

    Args:
        api_key: SiliconFlow API key
        base_url: Optional custom base URL
        model: Optional custom model

    Returns:
        Configured SiliconFlowClient instance
    """
    return SiliconFlowClient(
        api_key=api_key,
        base_url=base_url or "https://api.siliconflow.cn",
        model=model or "THUDM/GLM-4-32B-0414",
    )