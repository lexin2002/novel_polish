"""Tests for REST API endpoints"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch, MagicMock

from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test GET /api/health returns correct status"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_content_type():
    """Test health endpoint returns JSON content type"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/health")
        assert response.headers["content-type"] == "application/json"


@pytest.mark.asyncio
async def test_test_connection_missing_api_key():
    """Test POST /api/config/test-connection returns error when API key is empty"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/config/test-connection",
            json={
                "active_provider": "openai",
                "providers": {
                    "openai": {
                        "api": "openai",
                        "api_key": "",
                        "base_url": "https://api.openai.com/v1",
                        "active_model": "gpt-4o",
                    }
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "API Key" in data["error"]


@pytest.mark.asyncio
async def test_test_connection_missing_base_url():
    """Test POST /api/config/test-connection returns error when Base URL is empty"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/config/test-connection",
            json={
                "active_provider": "openai",
                "providers": {
                    "openai": {
                        "api": "openai",
                        "api_key": "sk-test",
                        "base_url": "",
                        "active_model": "gpt-4o",
                    }
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "Base URL" in data["error"]


@pytest.mark.asyncio
async def test_test_connection_missing_model():
    """Test POST /api/config/test-connection returns error when model is not selected"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/config/test-connection",
            json={
                "active_provider": "openai",
                "providers": {
                    "openai": {
                        "api": "openai",
                        "api_key": "sk-test",
                        "base_url": "https://api.openai.com/v1",
                        "active_model": "",
                    }
                },
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "模型" in data["error"]


@pytest.mark.asyncio
async def test_test_connection_success_openai():
    """Test POST /api/config/test-connection returns ok=True for valid OpenAI config"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.core.llm_client.LLMClient.test_connection") as mock_test:
            mock_test.return_value = {"ok": True, "model": "gpt-4o", "response": "OK"}
            with patch("app.core.llm_client.LLMClient.close", new_callable=AsyncMock):
                response = await client.post(
                    "/api/config/test-connection",
                    json={
                        "active_provider": "openai",
                        "providers": {
                            "openai": {
                                "api": "openai",
                                "api_key": "sk-valid-key",
                                "base_url": "https://api.openai.com/v1",
                                "active_model": "gpt-4o",
                            }
                        },
                    },
                )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["model"] == "gpt-4o"


@pytest.mark.asyncio
async def test_test_connection_success_anthropic():
    """Test POST /api/config/test-connection returns ok=True for valid Anthropic config"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.core.llm_client.LLMClient.test_connection") as mock_test:
            mock_test.return_value = {
                "ok": True,
                "model": "claude-3-5-sonnet-latest",
                "response": "OK",
            }
            with patch("app.core.llm_client.LLMClient.close", new_callable=AsyncMock):
                response = await client.post(
                    "/api/config/test-connection",
                    json={
                        "active_provider": "anthropic",
                        "providers": {
                            "anthropic": {
                                "api": "anthropic",
                                "api_key": "sk-ant-valid-key",
                                "base_url": "https://api.anthropic.com/v1",
                                "active_model": "claude-3-5-sonnet-latest",
                            }
                        },
                    },
                )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["model"] == "claude-3-5-sonnet-latest"


@pytest.mark.asyncio
async def test_test_connection_network_failure():
    """Test POST /api/config/test-connection handles network errors"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with patch("app.core.llm_client.LLMClient.test_connection") as mock_test:
            from app.core.llm_client import LLMConnectionError

            mock_test.side_effect = LLMConnectionError("Connection refused")
            with patch("app.core.llm_client.LLMClient.close", new_callable=AsyncMock):
                response = await client.post(
                    "/api/config/test-connection",
                    json={
                        "active_provider": "openai",
                        "providers": {
                            "openai": {
                                "api": "openai",
                                "api_key": "sk-test",
                                "base_url": "https://api.openai.com/v1",
                                "active_model": "gpt-4o",
                            }
                        },
                    },
                )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "Connection refused" in data["error"]
