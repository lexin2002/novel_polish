import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.engine.polishing_service import PolishingService, PolishRequest
from app.engine.text_slicer import TextSlicer, Chunk
from app.core.llm_client import LLMClient, LLMResponse

@pytest.mark.asyncio
async def test_full_pipeline_simulation():
    # 1. Setup Mock LLM Client
    mock_client = AsyncMock(spec=LLMClient)
    import json
    
    diagnosis_res = LLMResponse(
        content=json.dumps({"errors": [{"rule_name": "test", "location": "abc", "suggestion": "def"}]}),
        input_tokens=10, output_tokens=10
    )
    repair_res = LLMResponse(
        content=json.dumps({"revised_text": "SIMULATED_POLISHED_CONTENT", "modifications": []}),
        input_tokens=10, output_tokens=10
    )
    
    call_count = 0
    async def mock_chat(*args, **kwargs):
        nonlocal call_count
        res = [diagnosis_res, repair_res][call_count % 2]
        call_count += 1
        return res
        
    mock_client.chatcompletion.side_effect = mock_chat
    
    # 2. Setup Service
    service = PolishingService(mock_client)
    
    # 3. Test Input: Mixed content
    input_text = "这是一段文字。这里有禁忌之语，还有 <attack>注入攻击</attack>。希望能被润色。"
    service.masker.sensitive_words = ["禁忌之语"]
    
    request = PolishRequest(
        text=input_text,
        enable_safety_exempt=True,
        enable_xml_isolation=True
    )
    
    # 4. Run Pipeline
    result = await service.polish_text(request)
    
    # 5. Verifications
    assert result.polished_text is not None
    assert "SIMULATED_POLISHED" in result.polished_text
    
    # Verify Masking was applied in prompt
    # Access the first call to chatcompletion and get the prompt content
    first_call_args = mock_client.chatcompletion.call_args_list[0]
    # call_args is a tuple of (args, kwargs). 
    # Since it's called as chatcompletion(messages=..., ...), messages is in kwargs.
    called_prompt = first_call_args[1]['messages'][0]['content']
    
    assert "SIMULATED" not in called_prompt # Should be the original text or masked text
    assert "TOKEN_" in called_prompt
    
    # Verify XML Isolation was applied
    assert "<attack>" not in called_prompt
    assert "&lt;attack&gt;" in called_prompt

@pytest.mark.asyncio
async def test_semantic_slicing_simulation():
    slicer = TextSlicer(max_chunk_size=20)
    text = "第一段：这是一段比较长的文字，用来测试切片逻辑是否正确。这里应该足够长，足以触发切分逻辑。"
    chunks = slicer.split_into_chunks(text)
    
    assert len(chunks) >= 2
    # Check content of first chunk
    assert chunks[0].content.startswith("第一段")
