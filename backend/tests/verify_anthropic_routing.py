
import asyncio
import logging
from app.core.llm_client import LLMClient, LLMConnectionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test():
    # Mocking a DeepSeek Anthropic config
    config = {
        "provider": "deepseek",
        "api_key": "sk-test-key",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_type": "anthropic"
    }
    
    client = LLMClient(**config)
    
    # Verify URL normalization for anthropic
    url = client._normalize_url("messages")
    print(f"Normalized URL: {url}")
    assert url == "https://api.deepseek.com/v1/messages"
    
    # Verify that it doesn't double /v1 if already present
    client_v1 = LLMClient(
        provider="deepseek", 
        api_key="sk-test", 
        base_url="https://api.deepseek.com/v1", 
        model="deepseek-chat", 
        api_type="anthropic"
    )
    url_v1 = client_v1._normalize_url("messages")
    print(f"Normalized URL (with v1): {url_v1}")
    assert url_v1 == "https://api.deepseek.com/v1/messages"
    
    print("✅ URL normalization tests passed!")

if __name__ == '__main__':
    asyncio.run(test())
