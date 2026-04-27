"""Tests for unified LLM client (OpenAI-compatible and Anthropic APIs)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm_client import (
    LLMClient,
    LLMConnectionError,
    create_llm_client,
)


class TestLLMClientInitialization:
    """Test suite for LLMClient initialization"""

    def test_initialization_with_defaults(self):
        """Client initializes with correct defaults"""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
        )
        assert client.provider == "openai"
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.openai.com/v1"
        assert client.model == "gpt-4o"
        assert client.api_type == "openai"
        assert client.timeout == 60.0

    def test_initialization_with_custom_values(self):
        """Client accepts custom parameters"""
        client = LLMClient(
            provider="anthropic",
            api_key="sk-ant-test",
            base_url="https://api.anthropic.com/v1",
            model="claude-3-5-sonnet-latest",
            api_type="anthropic",
            timeout=30.0,
        )
        assert client.provider == "anthropic"
        assert client.api_key == "sk-ant-test"
        assert client.base_url == "https://api.anthropic.com/v1"
        assert client.model == "claude-3-5-sonnet-latest"
        assert client.api_type == "anthropic"
        assert client.timeout == 30.0

    def test_base_url_strips_trailing_slash(self):
        """Base URL trailing slash is stripped"""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1/",
            model="gpt-4o",
        )
        assert client.base_url == "https://api.openai.com/v1"


class TestLLMClientOpenAICompatible:
    """Test suite for OpenAI-compatible API (api_type='openai')"""

    @pytest.mark.asyncio
    async def test_chatcompletion_openai_success(self):
        """chatcompletion returns response on success for OpenAI-compatible API"""
        client = LLMClient(
            provider="deepseek",
            api_key="test-key",
            base_url="https://api.deepseek.com/v1",
            model="deepseek-chat",
            api_type="openai",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Polished text result"}}],
            "usage": {"total_tokens": 100},
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Polish this text"},
        ]

        result = await client.chatcompletion(messages)

        assert result == "Polished text result"
        client._client.post.assert_called_once()
        # Verify /chat/completions endpoint is called
        call_args = client._client.post.call_args
        assert "/chat/completions" in str(call_args)

    @pytest.mark.asyncio
    async def test_chatcompletion_openai_with_temperature(self):
        """chatcompletion sends correct parameters for OpenAI"""
        client = LLMClient(
            provider="qwen",
            api_key="test-key",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-turbo",
            api_type="openai",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Result"}}],
            "usage": {"total_tokens": 50},
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        await client.chatcompletion(
            messages=[{"role": "user", "content": "test"}],
            temperature=0.5,
            max_tokens=2048,
        )

        call_args = client._client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 2048
        assert payload["model"] == "qwen-turbo"

    @pytest.mark.asyncio
    async def test_chatcompletion_openai_auth_failure(self):
        """chatcompletion raises LLMConnectionError on 401 for OpenAI"""
        client = LLMClient(
            provider="openai",
            api_key="invalid-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            api_type="openai",
        )

        from httpx import HTTPStatusError, Response

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "401",
                request=MagicMock(),
                response=mock_response,
            )
        )

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMConnectionError, match="认证失败"):
            await client.chatcompletion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chatcompletion_openai_404_error(self):
        """chatcompletion raises LLMConnectionError on 404 for OpenAI"""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="nonexistent-model",
            api_type="openai",
        )

        from httpx import HTTPStatusError, Response

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Model not found"
        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "404",
                request=MagicMock(),
                response=mock_response,
            )
        )

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMConnectionError, match="模型不存在"):
            await client.chatcompletion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chatcompletion_openai_rate_limit(self):
        """chatcompletion raises LLMConnectionError on 429 for OpenAI"""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            api_type="openai",
        )

        from httpx import HTTPStatusError, Response

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Rate limit exceeded"
        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "429",
                request=MagicMock(),
                response=mock_response,
            )
        )

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMConnectionError, match="请求频率超限"):
            await client.chatcompletion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chatcompletion_openai_network_error(self):
        """chatcompletion raises LLMConnectionError on network failure"""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            api_type="openai",
        )

        import httpx

        client._client = MagicMock()
        client._client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )

        with pytest.raises(LLMConnectionError, match="网络连接失败"):
            await client.chatcompletion([{"role": "user", "content": "test"}])


class TestLLMClientAnthropic:
    """Test suite for Anthropic API (api_type='anthropic')"""

    @pytest.mark.asyncio
    async def test_chatcompletion_anthropic_success(self):
        """chatcompletion returns response on success for Anthropic API"""
        client = LLMClient(
            provider="anthropic",
            api_key="sk-ant-test",
            base_url="https://api.anthropic.com/v1",
            model="claude-3-5-sonnet-latest",
            api_type="anthropic",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"text": "Polished text result"}],
            "usage": {"input_tokens": 50, "output_tokens": 50},
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        messages = [
            {"role": "user", "content": "Polish this text"},
        ]

        result = await client.chatcompletion(messages)

        assert result == "Polished text result"
        client._client.post.assert_called_once()
        # Verify /messages endpoint is called
        call_args = client._client.post.call_args
        assert "/messages" in str(call_args)

    @pytest.mark.asyncio
    async def test_chatcompletion_anthropic_with_system_message(self):
        """chatcompletion sends system message as 'system' param for Anthropic"""
        client = LLMClient(
            provider="anthropic",
            api_key="sk-ant-test",
            base_url="https://api.anthropic.com/v1",
            model="claude-3-5-sonnet-latest",
            api_type="anthropic",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"text": "Result"}],
            "usage": {"input_tokens": 50, "output_tokens": 50},
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Polish this"},
        ]

        await client.chatcompletion(messages, temperature=0.5, max_tokens=1000)

        call_args = client._client.post.call_args
        payload = call_args.kwargs.get("json") or call_args[1].get("json")
        # System message should be in 'system' field
        assert payload.get("system") == "You are a helpful assistant."
        # Regular messages should be in 'messages' field
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_chatcompletion_anthropic_auth_failure(self):
        """chatcompletion raises LLMConnectionError on 401 for Anthropic"""
        client = LLMClient(
            provider="anthropic",
            api_key="invalid-key",
            base_url="https://api.anthropic.com/v1",
            model="claude-3-5-sonnet-latest",
            api_type="anthropic",
        )

        from httpx import HTTPStatusError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Invalid API key"
        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "401",
                request=MagicMock(),
                response=mock_response,
            )
        )

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMConnectionError, match="认证失败"):
            await client.chatcompletion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_chatcompletion_anthropic_403_error(self):
        """chatcompletion raises LLMConnectionError on 403 for Anthropic"""
        client = LLMClient(
            provider="anthropic",
            api_key="test-key",
            base_url="https://api.anthropic.com/v1",
            model="claude-3-5-sonnet-latest",
            api_type="anthropic",
        )

        from httpx import HTTPStatusError

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Permission denied"
        mock_response.raise_for_status = MagicMock(
            side_effect=HTTPStatusError(
                "403",
                request=MagicMock(),
                response=mock_response,
            )
        )

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMConnectionError, match="访问被拒绝"):
            await client.chatcompletion([{"role": "user", "content": "test"}])


class TestLLMClientTestConnection:
    """Test suite for LLMClient.test_connection()"""

    @pytest.mark.asyncio
    async def test_test_connection_openai_success(self):
        """test_connection returns ok=True on successful OpenAI connection"""
        client = LLMClient(
            provider="openai",
            api_key="valid-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            api_type="openai",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"total_tokens": 10},
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.test_connection()

        assert result["ok"] is True
        assert result["model"] == "gpt-4o"
        assert "OK" in result["response"]

    @pytest.mark.asyncio
    async def test_test_connection_anthropic_success(self):
        """test_connection returns ok=True on successful Anthropic connection"""
        client = LLMClient(
            provider="anthropic",
            api_key="valid-key",
            base_url="https://api.anthropic.com/v1",
            model="claude-3-5-sonnet-latest",
            api_type="anthropic",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "content": [{"text": "OK"}],
            "usage": {"input_tokens": 5, "output_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        result = await client.test_connection()

        assert result["ok"] is True
        assert result["model"] == "claude-3-5-sonnet-latest"

    @pytest.mark.asyncio
    async def test_test_connection_empty_response(self):
        """test_connection raises error on empty response"""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            api_type="openai",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": ""}}],
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(LLMConnectionError, match="返回内容为空"):
            await client.test_connection()


class TestLLMClientClose:
    """Test suite for LLMClient.close()"""

    @pytest.mark.asyncio
    async def test_close_cleans_up_client(self):
        """close() cleans up HTTP client"""
        client = LLMClient(
            provider="openai",
            api_key="test-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
        )
        mock_client = MagicMock()
        mock_client.aclose = AsyncMock()
        client._client = mock_client

        await client.close()

        assert client._client is None
        mock_client.aclose.assert_called_once()


class TestCreateLLMClient:
    """Test suite for create_llm_client factory"""

    @pytest.mark.asyncio
    async def test_create_with_defaults(self):
        """Factory creates client with default api_type='openai'"""
        client = await create_llm_client(
            provider="openai",
            api_key="my-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
        )
        assert client.api_key == "my-key"
        assert client.api_type == "openai"

    @pytest.mark.asyncio
    async def test_create_with_anthropic(self):
        """Factory creates client with api_type='anthropic'"""
        client = await create_llm_client(
            provider="anthropic",
            api_key="sk-ant-key",
            base_url="https://api.anthropic.com/v1",
            model="claude-3-5-sonnet-latest",
            api_type="anthropic",
        )
        assert client.api_type == "anthropic"
        assert client.model == "claude-3-5-sonnet-latest"

    @pytest.mark.asyncio
    async def test_create_with_custom_timeout(self):
        """Factory accepts custom timeout"""
        client = await create_llm_client(
            provider="openai",
            api_key="my-key",
            base_url="https://api.openai.com/v1",
            model="gpt-4o",
            timeout=120.0,
        )
        assert client.timeout == 120.0
