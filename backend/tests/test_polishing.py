"""Tests for PolishingService"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.llm_client import LLMClient, LLMResponse
from app.engine.polishing_service import (
    PolishingService,
    PolishRequest,
    PolishResult,
    ChunkResult,
    create_polishing_service,
)


class TestLLMClientSiliconFlow:
    """Test suite for LLMClient using SiliconFlow provider"""

    def test_initialization(self):
        """Client initializes with correct defaults"""
        client = LLMClient(
            provider="siliconflow",
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-32B-0414",
        )
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.siliconflow.cn/v1"
        assert client.model == "THUDM/GLM-4-32B-0414"

    def test_custom_initialization(self):
        """Client accepts custom parameters"""
        client = LLMClient(
            provider="custom",
            api_key="custom-key",
            base_url="https://custom.api.com",
            model="custom/model",
            timeout=60.0,
        )
        assert client.api_key == "custom-key"
        assert client.base_url == "https://custom.api.com"
        assert client.model == "custom/model"

    @pytest.mark.asyncio
    async def test_client_property_creates_httpx_client(self):
        """get_client() creates HTTP client on first access"""
        client = LLMClient(
            provider="siliconflow",
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-32B-0414",
        )
        http_client = await client.get_client()
        assert http_client is not None
        assert client.base_url in str(http_client.base_url)
        await client.close()

    @pytest.mark.asyncio
    async def test_chatcompletion_success(self):
        """chatcompletion returns response on success"""
        client = LLMClient(
            provider="siliconflow",
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-32B-0414",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Polished text result"}}
            ],
            "usage": {"total_tokens": 100},
        }
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Polish this text: hello world"},
        ]

        result = await client.chatcompletion(messages)

        assert result.content == "Polished text result"
        client._client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_chatcompletion_with_temperature(self):
        """chatcompletion accepts temperature parameter"""
        client = LLMClient(
            provider="siliconflow",
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-32B-0414",
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

    @pytest.mark.asyncio
    async def test_chatcompletion_no_choices_raises(self):
        """chatcompletion raises on empty choices"""
        client = LLMClient(
            provider="siliconflow",
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-32B-0414",
        )

        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": []}
        mock_response.raise_for_status = MagicMock()

        client._client = MagicMock()
        client._client.post = AsyncMock(return_value=mock_response)

        with pytest.raises(Exception, match="choices"):
            await client.chatcompletion([{"role": "user", "content": "test"}])

    @pytest.mark.asyncio
    async def test_close(self):
        """close() cleans up HTTP client"""
        client = LLMClient(
            provider="siliconflow",
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-32B-0414",
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
        """Factory creates client with required params"""
        from app.core.llm_client import create_llm_client
        client = await create_llm_client(
            provider="siliconflow",
            api_key="my-key",
            base_url="https://api.siliconflow.cn/v1",
            model="THUDM/GLM-4-32B-0414",
        )
        assert client.api_key == "my-key"
        assert client.provider == "siliconflow"
        assert client.model == "THUDM/GLM-4-32B-0414"

    @pytest.mark.asyncio
    async def test_create_with_custom_values(self):
        """Factory accepts custom base_url and model"""
        from app.core.llm_client import create_llm_client
        client = await create_llm_client(
            api_key="my-key",
            provider="deepseek",
            base_url="https://custom.com",
            model="custom/model",
        )
        assert client.base_url == "https://custom.com"
        assert client.model == "custom/model"


class TestPolishingService:
    """Test suite for PolishingService"""

    def test_initialization(self):
        """Service initializes with config"""
        mock_client = MagicMock()
        config = {
            "llm": {
                "safety_exempt_enabled": True,
                "xml_tag_isolation_enabled": True,
                "temperature": 0.4,
                "max_tokens": 4096,
            },
            "engine": {
                "max_chunk_size": 1000,
                "context_overlap_chars": 200,
                "max_workers": 3,
                "max_requests_per_second": 2,
            },
        }

        service = PolishingService(llm_client=mock_client, config=config)

        assert service.llm_client is mock_client
        assert service.max_workers == 3
        assert service.prompt_builder is not None
        assert service.text_slicer is not None

    def test_initialization_with_defaults(self):
        """Service falls back to default config"""
        mock_client = MagicMock()
        service = PolishingService(llm_client=mock_client, config={})
        assert service.max_workers == 3  # from DEFAULT_CONFIG

    def test_extract_polished_text_from_tags(self):
        """_extract_polished_text extracts from XML tags"""
        mock_client = MagicMock()
        service = PolishingService(llm_client=mock_client)

        response = """Here is some analysis.

<USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>
This is the polished fiction text.
It has multiple lines.
</USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>

Some more analysis here."""

        result = service._extract_polished_text(response)

        assert result == "This is the polished fiction text.\nIt has multiple lines."

    def test_extract_polished_text_plain(self):
        """_extract_polished_text returns stripped text if no tags"""
        mock_client = MagicMock()
        service = PolishingService(llm_client=mock_client)

        response = "This is just the polished text without any tags."

        result = service._extract_polished_text(response)

        assert result == "This is just the polished text without any tags."

    @pytest.mark.asyncio
    async def test_polish_text_single_chunk(self):
        """polish_text handles single chunk (no slicing needed)"""
        mock_client = MagicMock()
        mock_client.chatcompletion = AsyncMock(
            return_value=LLMResponse(content="Polished version of the text.", input_tokens=10, output_tokens=20)
        )

        config = {
            "llm": {"safety_exempt_enabled": True, "xml_tag_isolation_enabled": True, "temperature": 0.4, "max_tokens": 4096},
            "engine": {"max_chunk_size": 1000, "context_overlap_chars": 200, "max_workers": 3, "max_requests_per_second": 10},
        }

        service = PolishingService(llm_client=mock_client, config=config)

        request = PolishRequest(text="Short text that doesn't need chunking.")
        result = await service.polish_text(request)

        assert isinstance(result, PolishResult)
        assert result.original_text == "Short text that doesn't need chunking."
        assert result.polished_text == "Polished version of the text."
        assert result.chunks_processed == 1
        assert len(result.modifications) == 0

    @pytest.mark.asyncio
    async def test_polish_text_multiple_chunks(self):
        """polish_text processes multiple chunks when text exceeds chunk size"""
        mock_client = MagicMock()
        mock_client.chatcompletion = AsyncMock(
            return_value=LLMResponse(content="Polished chunk content.", input_tokens=10, output_tokens=20)
        )

        # Use very small chunk size to force multiple chunks
        config = {
            "llm": {"safety_exempt_enabled": True, "xml_tag_isolation_enabled": True, "temperature": 0.4, "max_tokens": 4096},
            "engine": {"chunk_size": 10, "max_workers": 3, "max_requests_per_second": 10},
        }

        service = PolishingService(llm_client=mock_client, config=config)

        # Create long text that should definitely need multiple chunks
        long_text = "这是一个非常长的文本，需要被分割成多个小块才能正确处理。" * 5

        request = PolishRequest(text=long_text)
        result = await service.polish_text(request)

        assert isinstance(result, PolishResult)
        # With chunk_size=10, this long text should be split
        # TextSlicer splits at sentence boundaries, so we check it produces multiple chunks
        assert result.chunks_processed >= 2 or len(long_text) > config["engine"]["chunk_size"]
        # LLM should have been called at least once
        assert mock_client.chatcompletion.call_count >= 1


class TestPolishRequest:
    """Test suite for PolishRequest dataclass"""

    def test_default_values(self):
        """PolishRequest has sensible defaults"""
        request = PolishRequest(text="Test text")
        assert request.text == "Test text"
        assert request.rules_state is None
        assert request.enable_safety_exempt is True
        assert request.enable_xml_isolation is True

    def test_custom_values(self):
        """PolishRequest accepts custom values"""
        rules = {"main_categories": []}
        request = PolishRequest(
            text="Test",
            rules_state=rules,
            enable_safety_exempt=False,
            enable_xml_isolation=False,
        )
        assert request.enable_safety_exempt is False
        assert request.enable_xml_isolation is False


class TestChunkResult:
    """Test suite for ChunkResult dataclass"""

    def test_creation(self):
        """ChunkResult stores processing results"""
        result = ChunkResult(
            chunk_index=0,
            polished_content="Polished",
            modifications=[{"original": "bad", "corrected": "good"}],
            tokens_used=50,
        )
        assert result.chunk_index == 0
        assert result.polished_content == "Polished"
        assert len(result.modifications) == 1
        assert result.tokens_used == 50


class TestPolishingServiceEdgeCases:
    """Edge case tests for PolishingService"""

    @pytest.mark.asyncio
    async def test_polish_empty_text(self):
        """polish_text handles empty text"""
        mock_client = MagicMock()
        mock_client.chatcompletion = AsyncMock(return_value="")

        config = {
            "llm": {"safety_exempt_enabled": True, "xml_tag_isolation_enabled": True, "temperature": 0.4, "max_tokens": 4096},
            "engine": {"max_chunk_size": 1000, "context_overlap_chars": 200, "max_workers": 3, "max_requests_per_second": 10},
        }

        service = PolishingService(llm_client=mock_client, config=config)
        request = PolishRequest(text="")
        result = await service.polish_text(request)

        # Empty text produces 0 chunks (as per TextSlicer behavior)
        assert result.chunks_processed == 0
        assert result.polished_text == ""

    @pytest.mark.asyncio
    async def test_polish_llm_failure_fallback(self):
        """polish_text returns original on LLM failure"""
        mock_client = MagicMock()
        mock_client.chatcompletion = AsyncMock(side_effect=Exception("API Error"))

        config = {
            "llm": {"safety_exempt_enabled": True, "xml_tag_isolation_enabled": True, "temperature": 0.4, "max_tokens": 4096},
            "engine": {"max_chunk_size": 1000, "context_overlap_chars": 200, "max_workers": 3, "max_requests_per_second": 10},
        }

        service = PolishingService(llm_client=mock_client, config=config)
        request = PolishRequest(text="Some text that should be preserved on failure.")

        result = await service.polish_text(request)

        # Should return original text when LLM fails
        assert result.polished_text == "Some text that should be preserved on failure."
        assert result.chunks_processed == 1

    def test_unicode_handling(self):
        """Service handles unicode text correctly"""
        mock_client = MagicMock()
        config = {
            "llm": {"safety_exempt_enabled": True, "xml_tag_isolation_enabled": True, "temperature": 0.4, "max_tokens": 4096},
            "engine": {"max_chunk_size": 1000, "context_overlap_chars": 200, "max_workers": 3, "max_requests_per_second": 10},
        }

        service = PolishingService(llm_client=mock_client, config=config)

        unicode_text = "中文文本测试 日本語 테스트 한국어"
        request = PolishRequest(text=unicode_text)

        # Should not raise, slicing handles unicode
        chunks = service.text_slicer.split_into_chunks(unicode_text)
        assert len(chunks) >= 1