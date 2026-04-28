import asyncio
import pytest
from app.core.llm_client import LLMClient, LLMConnectionError

# Test Configurations
TEST_CONFIGS = [
    {
        "name": "DeepSeek (OpenAI Protocol)",
        "provider": "deepseek",
        "api_key": "sk-0cb7080799bf47f7905f1fa166ff3b26",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-v4-flash",
        "api_type": "openai"
    },
    {
        "name": "DeepSeek (Anthropic Protocol)",
        "provider": "deepseek",
        "api_key": "sk-0cb7080799bf47f7905f1fa166ff3b26",
        "base_url": "https://api.deepseek.com/anthropic",
        "model": "deepseek-v4-flash",
        "api_type": "anthropic"
    },
    {
        "name": "SiliconFlow (OpenAI Protocol)",
        "provider": "siliconflow",
        "api_key": "sk-tjomqqvjkmlijswvfpcfgeggzpbmdarqmskcpolnvjtfqccz",
        "base_url": "https://api.siliconflow.cn",
        "model": "deepseek-ai/DeepSeek-V4-Flash",
        "api_type": "openai"
    },
    {
        "name": "Google Gemma (Google Protocol)",
        "provider": "google",
        "api_key": "AIzaSyD2UjktyZ0dfmmG3oLuzQ96-5ucH8z1alY",
        "base_url": "https://generativelanguage.googleapis.com",
        "model": "gemini-1.5-flash",
        "api_type": "google"
    }
]

@pytest.mark.asyncio
async def test_llm_compatibility():
    messages = [{"role": "user", "content": "Hello, this is a compatibility test. Reply with 'OK'."}]
    
    for cfg in TEST_CONFIGS:
        print(f"\nTesting {cfg['name']}...")
        client = LLMClient(
            provider=cfg['provider'],
            api_key=cfg['api_key'],
            base_url=cfg['base_url'],
            model=cfg['model'],
            api_type=cfg['api_type']
        )
        
        try:
            # Test the high-level chatcompletion wrapper
            response = await client.chatcompletion(messages=messages, temperature=0.1)
            print(f"✅ SUCCESS: Received content: {response.content[:50]}...")
            print(f"Tokens: input={response.input_tokens}, output={response.output_tokens}")
            assert response.content is not None
        except LLMConnectionError as e:
            print(f"❌ FAILED: Connection Error: {e}")
            # We use pytest.fail to mark the test as failed
            pytest.fail(f"{cfg['name']} failed with ConnectionError: {e}")
        except Exception as e:
            print(f"❌ FAILED: Unexpected Error: {e}")
            pytest.fail(f"{cfg['name']} failed with unexpected error: {e}")
        finally:
            await client.close()

if __name__ == "__main__":
    asyncio.run(test_llm_compatibility())
