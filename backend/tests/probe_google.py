
import asyncio
import httpx

async def probe(url, key):
    print(f"Trying: {url}")
    try:
        async with httpx.AsyncClient() as client:
            # Use a very simple prompt to test connectivity
            payload = {
                "contents": [{"parts": [{"text": "OK"}]}]
            }
            response = await client.post(f"{url}?key={key}", json=payload)
            print(f"Result: {response.status_code} - {response.text[:100]}")
            return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

async def main():
    key = "AIzaSyD2UjktyZ0dfmmG3oLuzQ96-5ucH8z1alY"
    model = "gemma-4-31b-it"
    base = "https://generativelanguage.googleapis.com"
    
    # Test matrix: (API version, Model prefix)
    matrix = [
        ("v1beta", "models/"),
        ("v1", "models/"),
        ("v1beta", ""),
        ("v1", ""),
    ]
    
    for version, prefix in matrix:
        url = f"{base}/{version}/{prefix}{model}:generateContent"
        if await probe(url, key):
            print(f"\n🎉 FOUND WORKING URL: {url}")
            return
    
    print("\n❌ All probed URLs failed.")

if __name__ == '__main__':
    asyncio.run(main())
