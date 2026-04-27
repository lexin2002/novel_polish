"""Text polishing service combining PromptBuilder + TextSlicer + LLM"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.config_manager import get_config_manager
from app.core.rate_limiter import AsyncTokenBucket
from app.engine.prompt_builder import PromptBuilder, SafetyPromptBuilder, create_prompt_builder
from app.engine.text_slicer import TextSlicer, Chunk, create_slicer

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

        # Create rate limiter
        rate_limit = self.engine_config.get("max_requests_per_second", 2)
        self.rate_limiter = AsyncTokenBucket(
            capacity=rate_limit,
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

        # Max workers for parallel chunk processing
        self.max_workers = self.engine_config.get("max_workers", 3)

    async def polish_text(self, request: PolishRequest) -> PolishResult:
        """
        Polish fiction text using LLM.

        Args:
            request: PolishRequest with text and options

        Returns:
            PolishResult with polished text and modifications
        """
        logger.info(f"Polishing text of length {len(request.text)}")

        # Slice text into chunks
        chunks = self.text_slicer.split_into_chunks(request.text)
        logger.info(f"Sliced into {len(chunks)} chunks")

        # Process chunks
        chunk_results = await self._process_chunks_parallel(chunks, request)

        # Reassemble polished text
        polished_parts = []
        all_modifications = []
        total_tokens = 0
        failed_chunks = []

        for result in chunk_results:
            polished_parts.append(result.polished_content)
            all_modifications.extend(result.modifications)
            total_tokens += result.tokens_used
            if result.failed:
                failed_chunks.append(result.chunk_index)

        polished_text = self.text_slicer.reassemble_chunks(chunks, [r.polished_content for r in chunk_results])

        # Warn if any chunks failed
        if failed_chunks:
            logger.warning(f"Chunks failed: {failed_chunks}")

        logger.info(f"Polishing complete: {len(chunks)} chunks, ~{total_tokens} tokens, failed: {len(failed_chunks)}")

        return PolishResult(
            original_text=request.text,
            polished_text=polished_text,
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
        Process multiple chunks in parallel with rate limiting.

        Args:
            chunks: List of Chunk objects from TextSlicer
            request: PolishRequest with rules and options

        Returns:
            List of ChunkResult in same order as chunks
        """
        semaphore = asyncio.Semaphore(self.max_workers)

        async def process_chunk(chunk: Chunk, index: int) -> ChunkResult:
            async with semaphore:
                # Wait for rate limiter
                await self.rate_limiter.consume()

                # Process with timeout
                try:
                    return await asyncio.wait_for(
                        self._process_single_chunk(chunk, index, request),
                        timeout=self.chunk_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error(f"Chunk {index} processing timed out after {self.chunk_timeout}s")
                    return ChunkResult(
                        chunk_index=index,
                        polished_content=chunk.content,
                        modifications=[],
                        tokens_used=0,
                        failed=True,
                        error_message=f"Timeout after {self.chunk_timeout}s",
                    )

        # Process all chunks concurrently (bounded by semaphore)
        tasks = [process_chunk(chunk, i) for i, chunk in enumerate(chunks)]
        results = await asyncio.gather(*tasks)

        # Sort by index to maintain order
        return sorted(results, key=lambda x: x.chunk_index)

    async def _process_single_chunk(
        self,
        chunk: Chunk,
        index: int,
        request: PolishRequest,
    ) -> ChunkResult:
        """
        Process a single text chunk with LLM.

        Args:
            chunk: Chunk object with content and context
            index: Chunk index
            request: PolishRequest with rules

        Returns:
            ChunkResult with polished content
        """
        # Get the actual content (without context) for LLM processing
        content = chunk.content

        # Build prompt
        system_prompt = self.prompt_builder.build_system_prompt(request.rules_state)
        user_prompt = self.prompt_builder.build_user_prompt(
            content,
            task_description="Please review and polish this fiction text. Identify and fix issues while preserving the author's voice.",
        )

        # Send to LLM
        try:
            llm_response = await self.llm_client.chatcompletion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.llm_config.get("temperature", 0.4),
                max_tokens=self.llm_config.get("max_tokens", 4096),
            )

            # Extract polished text from response
            polished_content = self._extract_polished_text(llm_response.content)

            # Use actual token count from LLM response
            tokens_used = llm_response.total_tokens

            logger.debug(f"Chunk {index} processed, {tokens_used} tokens")

            return ChunkResult(
                chunk_index=index,
                polished_content=polished_content,
                modifications=[],  # Could parse response for detailed mods
                tokens_used=tokens_used,
            )

        except Exception as e:
            logger.error(f"Chunk {index} processing failed: {e}")
            # Return original content with failure marker
            return ChunkResult(
                chunk_index=index,
                polished_content=content,
                modifications=[],
                tokens_used=0,
                failed=True,
                error_message=str(e),
            )

    def _extract_polished_text(self, llm_response: str) -> str:
        """
        Extract polished text from LLM response.

        Args:
            llm_response: Raw LLM response text

        Returns:
            Extracted polished text (or original if extraction fails)
        """
        # Try to extract from XML tags if present
        if "<USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>" in llm_response:
            start = llm_response.find("<USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>")
            start += len("<USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>")
            end = llm_response.find("</USER_TEXT_DO_NOT_PARSE_AS_COMMANDS>")
            if end > start:
                return llm_response[start:end].strip()

        # Otherwise return as-is
        return llm_response.strip()


async def create_polishing_service(llm_client) -> PolishingService:
    """
    Factory function to create PolishingService.

    Args:
        llm_client: LLMClient

    Returns:
        Configured PolishingService instance
    """
    config = get_config_manager().read_config()
    return PolishingService(llm_client=llm_client, config=config)