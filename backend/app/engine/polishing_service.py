"""Text polishing service combining PromptBuilder + TextSlicer + LLM"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.config_manager import get_config_manager
from app.core.rate_limiter import AsyncTokenBucket, CircuitBreaker
from app.engine.prompt_builder import create_prompt_builder
from app.engine.text_slicer import TextSlicer, Chunk, create_slicer
from app.engine.text_masker import create_text_masker

logger = logging.getLogger(__name__)


@dataclass
class PolishRequest:
    """Request to polish text"""
    text: str
    rules_state: Optional[Dict[str, Any]] = None
    enable_safety_exempt: bool = True
    enable_xml_isolation: bool = True


@dataclass
class PolishResult:
    """Result of text polishing"""
    original_text: str
    polished_text: str
    modifications: List[Dict[str, str]]
    chunks_processed: int
    total_tokens: int


@dataclass
class ChunkResult:
    """Result of processing a single chunk"""
    chunk_index: int
    polished_content: str
    modifications: List[Dict[str, str]]
    tokens_used: int
    failed: bool = False  # Track if chunk processing failed
    error_message: str = ""  # Error message if failed


class PolishingService:
    """Service for polishing fiction text using LLM"""

    def __init__(
        self,
        llm_client,  # LLMClient
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize polishing service.

        Args:
            llm_client: LLM API client (LLMClient)
            config: Optional config dict (reads from config manager if not provided)
        """
        self.llm_client = llm_client

        if config is None:
            config = get_config_manager().read_config()

        self.config = config
        self.llm_config = config.get("llm", {})
        self.engine_config = config.get("engine", {})

        # Get chunk timeout from config (default 60s)
        self.chunk_timeout = self.engine_config.get("chunk_timeout_seconds", 60)

        # Create rate limiter (capacity = 2x fill_rate for burst tolerance)
        rate_limit = self.engine_config.get("max_requests_per_second", 2)
        self.rate_limiter = AsyncTokenBucket(
            capacity=rate_limit * 2,
            fill_rate=rate_limit,
        )
        # Create prompt builder
        self.prompt_builder = create_prompt_builder(
            safety_exempt_enabled=self.llm_config.get("safety_exempt_enabled", True),
            xml_tag_isolation_enabled=self.llm_config.get("xml_tag_isolation_enabled", True),
        )
        # Create text slicer
        self.text_slicer = create_slicer(
            max_chunk_size=self.engine_config.get("chunk_size", 1000),
            context_overlap=self.engine_config.get("context_overlap_chars", 200),
        )
        # Create text masker for sensitive content
        self.masker = create_text_masker(
            sensitive_words=self.engine_config.get("sensitive_words", [])
        )
        # Max workers for parallel chunk processing
        self.max_workers = self.engine_config.get("max_workers", 3)
        
        # Circuit Breaker for API stability
        self.circuit_breaker = CircuitBreaker(
            threshold=self.engine_config.get("circuit_breaker_threshold", 3),
            recovery_timeout=30.0
        )

    async def polish_text(self, request: PolishRequest) -> PolishResult:
        """
        Polish fiction text using LLM with masking and isolation.
        """
        logger.info(f"!!! [DEBUG] polish_text entered. Text length: {len(request.text)}")
        
        # 1. Mask sensitive content
        masked_text, mask_map = self.masker.mask(request.text)
        if mask_map:
            logger.info(f"Masked {len(mask_map)} sensitive terms.")

        # 2. Slice masked text into chunks
        chunks = self.text_slicer.split_into_chunks(masked_text)
        logger.info(f"!!! [DEBUG] Slicing complete. Produced {len(chunks)} chunks.")
        
        if not chunks:
            logger.error("!!! [DEBUG] CRITICAL: TextSlicer produced ZERO chunks!")
            return PolishResult(
                original_text=request.text,
                polished_text=request.text,
                modifications=[],
                chunks_processed=0,
                total_tokens=0,
            )

        # 3. Process chunks
        chunk_results = await self._process_chunks_parallel(chunks, request)
        
        # 4. Reassemble and unmask
        polished_text = self.text_slicer.reassemble_chunks(chunks, [r.polished_content for r in chunk_results])
        final_text = self.masker.unmask(polished_text, mask_map)
        
        total_tokens = sum(r.tokens_used for r in chunk_results)
        all_modifications = []
        for r in chunk_results:
            all_modifications.extend(r.modifications)
        
        logger.info(f"Polishing complete: {len(chunks)} chunks, ~{total_tokens} tokens")
        
        return PolishResult(
            original_text=request.text,
            polished_text=final_text,
            modifications=all_modifications,
            chunks_processed=len(chunks),
            total_tokens=total_tokens,
        )

    async def _process_chunks_parallel(
        self,
        chunks: List[Chunk],
        request: PolishRequest,
    ) -> List[ChunkResult]:
        """
        Process chunks sequentially for debugging and stability.
        """
        logger.info(f"Starting chunk processing. Total chunks: {len(chunks)}")
        results = []
        
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i}/{len(chunks)-1}...")
            # Wait for rate limiter
            await self.rate_limiter.consume()

            # Process with timeout
            try:
                result = await asyncio.wait_for(
                    self._process_single_chunk(chunk, i, request),
                    timeout=self.chunk_timeout
                )
                results.append(result)
                logger.info(f"Chunk {i} completed successfully.")
            except asyncio.TimeoutError:
                logger.error(f"Chunk {i} processing timed out after {self.chunk_timeout}s")
                results.append(ChunkResult(
                    chunk_index=i,
                    polished_content=chunk.content,
                    modifications=[],
                    tokens_used=0,
                    failed=True,
                    error_message=f"Timeout after {self.chunk_timeout}s",
                ))
            except Exception as e:
                logger.error(f"Unexpected error in chunk {i}: {e}", exc_info=True)
                results.append(ChunkResult(
                    chunk_index=i,
                    polished_content=chunk.content,
                    modifications=[],
                    tokens_used=0,
                    failed=True,
                    error_message=str(e),
                ))

        logger.info(f"All chunks processed. Total results: {len(results)}")
        return results

    async def _process_single_chunk(
        self,
        chunk: Chunk,
        index: int,
        request: PolishRequest,
    ) -> ChunkResult:
        """
        Process a single text chunk using an iterative diagnose-and-repair loop.
        """
        content = chunk.content
        current_text = content
        iteration = 0
        max_iterations = self.engine_config.get("max_iterations", 3)
        total_tokens = 0
        all_mods = []

        logger.info(f"Chunk {index}: Entering iterative loop (max {max_iterations})")

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Chunk {index}: Iteration {iteration}/{max_iterations} - Diagnosing...")
            
            # 1. Precise Diagnosis
            diag_res, diag_tokens = await self._diagnose_chunk(current_text, request.rules_state)
            total_tokens += diag_tokens
            
            if not diag_res.get("errors"):
                logger.info(f"Chunk {index}: Zero defects found at iteration {iteration}.")
                break
            
            logger.info(f"Chunk {index}: Found {len(diag_res['errors'])} issues. Repairing...")
            
            # 2. Precise Repair
            repair_res, repair_tokens = await self._repair_chunk(current_text, diag_res["errors"])
            total_tokens += repair_tokens
            
            # 3. Invalid Modification Detection (Circuit Breaker)
            if self._is_text_unchanged(current_text, repair_res):
                logger.warning(f"Chunk {index}: No actual changes made by LLM. Breaking loop to avoid dead-lock.")
                break
                
            current_text = repair_res
            all_mods.extend([]) # In future, parse actual mods from LLM

        # Check if we stopped because of max iterations while errors still exist
        failed = False
        error_msg = ""
        if iteration >= max_iterations:
            final_diag, _ = await self._diagnose_chunk(current_text, request.rules_state)
            if final_diag.get("errors"):
                failed = True
                error_msg = f"Repair limit reached. {len(final_diag['errors'])} issues remain."
                logger.warning(f"Chunk {index}: {error_msg}")

        return ChunkResult(
            chunk_index=index,
            polished_content=current_text,
            modifications=all_mods,
            tokens_used=total_tokens,
            failed=failed,
            error_message=error_msg,
        )

    async def _diagnose_chunk(self, text: str, rules_state: Optional[Dict[str, Any]]) -> tuple[Dict[str, Any], int]:
        """
        Ask LLM to identify errors based on rules and return a JSON list.
        Includes a 3-try robust retry mechanism for JSON parsing.
        """
        rules_text = ""
        if rules_state and "main_categories" in rules_state:
            for cat in rules_state["main_categories"]:
                cat_name = cat.get("name", "Unknown")
                for sub in cat.get("sub_categories", []):
                    sub_name = sub.get("name", "Unknown")
                    for rule in sub.get("rules", []):
                        if rule.get("enabled", True):
                            rules_text += f"- [{cat_name} > {sub_name}] {rule.get('name')}: {rule.get('instruction')}\n"

        system_prompt = (
            "You are a professional fiction editor. Your task is to DIAGNOSE the text for errors based on the provided rules.\n"
            "You must output a VALID JSON object with a key 'errors' which is a list of objects:\n"
            "- rule_name: The name of the rule violated\n"
            "- location: The exact snippet of text that is problematic\n"
            "- suggestion: How to fix it precisely\n"
            "Example: {\"errors\": [{\"rule_name\": \"Wordiness\", \"location\": \"he walked very slowly\", \"suggestion\": \"he plodded\"}]}"
        )
        user_prompt = f"Rules:\n{rules_text}\n\nText to diagnose:\n{text}"
        
        total_tokens = 0
        for attempt in range(3):
            res = await self.llm_client.chatcompletion(
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=0.2,
            )
            total_tokens += res.total_tokens
            
            # Robust JSON extraction
            parsed_data = self._robust_json_parse(res.content)
            if parsed_data and "errors" in parsed_data and isinstance(parsed_data["errors"], list):
                return parsed_data, total_tokens
            
            logger.warning(f"Chunk diagnosis JSON parse failed (attempt {attempt+1}/3). Response: {res.content[:100]}...")

        # Fallback: return a generic error to avoid breaking the loop
        return {"errors": []}, total_tokens

    def _robust_json_parse(self, content: str) -> Optional[Dict[str, Any]]:
        """
        Extract and parse JSON from LLM response using regex and json5.
        """
        import re
        import json
        try:
            # 1. Try to find the outermost { ... }
            match = re.search(r'(\{.*\})', content, re.DOTALL)
            if not match:
                return None
            
            json_str = match.group(1)
            # 2. Try standard json first
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                # 3. Fallback to a simple cleanup for common LLM JSON errors
                cleaned = json_str.replace("\n", " ").replace("'", "\"")
                return json.loads(cleaned)
        except Exception as e:
            logger.debug(f"JSON parse error: {e}")
            return None

    async def _repair_chunk(self, text: str, errors: List[Dict[str, Any]]) -> tuple[str, int]:
        """
        Ask LLM to apply specific repairs based on a diagnosis report.
        """
        error_list = "\\n".join([f"- {e['rule_name']} | {e['location']} -> {e['suggestion']}" for e in errors])
        
        system_prompt = (
            "You are a professional fiction editor. Your task is to REPAIR the text based on the provided diagnosis report.\\n"
            "Modify ONLY the problematic parts. Preserve all other text exactly as is. "
            "Do not add any commentary. Output only the final polished text."
        )
        
        user_prompt = f"Diagnosis Report:\\n{error_list}\\n\\nOriginal Text:\\n{text}"
        
        res = await self.llm_client.chatcompletion(
            messages=[{"role": "system", "content": "Professional Editor - Repair Mode"}, {"role": "user", "content": user_prompt}],
            temperature=0.3,
        )
        
        return res.content.strip(), res.total_tokens

    def _is_text_unchanged(self, text1: str, text2: str) -> bool:
        """
        Check if two texts are substantively the same (ignore whitespace).
        """
        return "".join(text1.split()) == "".join(text2.split())

    def _extract_polished_text(self, llm_response: str) -> str:
        """
        Extract polished text from LLM response.
        """
        if "<USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>" in llm_response:
            start = llm_response.find("<USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>")
            start += len("<USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>")
            end = llm_response.find("</USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>")
            if end > start:
                return llm_response[start:end].strip()
        return llm_response.strip()

async def create_polishing_service(llm_client) -> PolishingService:
    """
    Factory function to create PolishingService.
    """
    config = get_config_manager().read_config()
    return PolishingService(llm_client=llm_client, config=config)
