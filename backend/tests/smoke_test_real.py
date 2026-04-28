
import asyncio
import json5
import os
from app.core.llm_client import LLMClient

async def main():
    config_path = "/home/wsl_lexin/.config/NovelPolish/config.jsonc"
    if not os.path.exists(config_path):
        print(f"Config not found at {config_path}")
        return

    with open(config_path, 'r') as f:
        config = json5.load(f)
    
    llm_config = config.get("llm", {})
    providers = llm_config.get("providers", {})
    
    results = []
    for p_id, p_cfg in providers.items():
        api_key = p_cfg.get("api_key")
        if not api_key:
            continue
            
        print(f"Testing provider: {p_id} ({p_cfg.get('api')})...", end=" ", flush=True)
        try:
            client = LLMClient(
                provider=p_id,
                api_key=api_key,
                base_url=p_cfg.get("base_url", ""),
                model=p_cfg.get("active_model", ""),
                api_type=p_cfg.get("api")
            )
            res = await client.test_connection()
            print(f"✅ SUCCESS (Response: {res['response']})")
            results.append(True)
        except Exception as e:
            print(f"❌ FAILED ({str(e)})")
            results.append(False)

    if not results:
        print("No providers with API keys found to test.")
    elif all(results):
        print("\n🎉 ALL TESTED PROVIDERS VERIFIED!")
    else:
        print("\n⚠️ SOME PROVIDERS FAILED.")

if __name__ == '__main__':
    asyncio.run(main())
