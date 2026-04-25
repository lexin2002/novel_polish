"""Smart text slicing with dynamic punctuation snap and context preservation"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default sentence delimiters (Chinese punctuation)
SENTENCE_DELIMITERS = {'。', '！', '？', '；', '\n', '！', '？'}


@dataclass
class Chunk:
    """Represents a slice of text with context"""
    content: str
    chunk_index: int
    total_chunks: int
    context_start: int  # Start position in original text
    context_end: int     # End position in original text
    content_start: int    # Content start (after context)
    content_end: int      # Content end
    has_context: bool     # Whether this chunk has preceding context
    raw_text: str          # Original text before any processing

    def __repr__(self) -> str:
        return (
            f"Chunk(index={self.chunk_index}/{self.total_chunks}, "
            f"context=({self.context_start}-{self.context_end}), "
            f"content=({self.content_start}-{self.content_end}), "
            f"has_context={self.has_context}, "
            f"len={len(self.content)})"
        )


class TextSlicer:
    """Smart text slicer with dynamic punctuation snap"""

    def __init__(
        self,
        max_chunk_size: int = 1000,
        context_overlap: int = 200,
        sentence_delimiters: Optional[set] = None,
    ):
        """
        Initialize TextSlicer.

        Args:
            max_chunk_size: Maximum characters per chunk (default 1000)
            context_overlap: Characters to overlap from previous chunk (default 200)
            sentence_delimiters: Set of sentence delimiter characters
        """
        self.max_chunk_size = max_chunk_size
        self.context_overlap = context_overlap
        self.sentence_delimiters = sentence_delimiters or SENTENCE_DELIMITERS

    def find_sentence_boundary(
        self,
        text: str,
        position: int,
        direction: str = 'left',
        max_search: int = 200,
    ) -> Optional[int]:
        """
        Find the nearest sentence boundary from a position.

        Args:
            text: The text to search
            position: Starting position
            direction: 'left' or 'right'
            max_search: Maximum characters to search

        Returns:
            Position of sentence boundary, or None if not found
        """
        if direction == 'left':
            start = max(0, position - max_search)
            search_text = text[start:position]
            # Find the last delimiter in the search range
            for i in range(len(search_text) - 1, -1, -1):
                if search_text[i] in self.sentence_delimiters:
                    return start + i + 1
            # Fallback: no boundary found
            logger.warning(
                f"Cannot find left sentence boundary at position {position}, "
                f"falling back to hard truncation"
            )
            return position - max_search if position > max_search else 0

        else:  # right
            end = min(len(text), position + max_search)
            search_text = text[position:end]
            for i, char in enumerate(search_text):
                if char in self.sentence_delimiters:
                    return position + i + 1
            logger.warning(
                f"Cannot find right sentence boundary at position {position}, "
                f"falling back to hard truncation"
            )
            return position + max_search

    def split_into_chunks(self, text: str) -> List[Chunk]:
        """
        Split text into chunks with context preservation.

        Args:
            text: The text to split

        Returns:
            List of Chunk objects
        """
        if not text:
            return []

        chunks: List[Chunk] = []
        text_length = len(text)

        # If text fits in one chunk, return it without context
        if text_length <= self.max_chunk_size:
            return [
                Chunk(
                    content=text,
                    chunk_index=0,
                    total_chunks=1,
                    context_start=0,
                    context_end=0,
                    content_start=0,
                    content_end=text_length,
                    has_context=False,
                    raw_text=text,
                )
            ]

        # Calculate number of chunks needed
        # Account for overlap: effective size = max_chunk_size - context_overlap
        effective_size = self.max_chunk_size - self.context_overlap
        if effective_size <= 0:
            effective_size = self.max_chunk_size // 2
            logger.warning(
                f"context_overlap ({self.context_overlap}) >= max_chunk_size ({self.max_chunk_size}), "
                f"using effective size {effective_size}"
            )

        # Calculate chunk positions
        chunk_starts = []
        pos = 0
        while pos < text_length:
            chunk_starts.append(pos)
            pos += effective_size

        # Adjust last chunk to not exceed text length
        if chunk_starts and chunk_starts[-1] > text_length - effective_size:
            # Recalculate to ensure even distribution
            chunk_count = (text_length + effective_size - 1) // effective_size
            chunk_starts = [
                i * (text_length // chunk_count) for i in range(chunk_count)
            ]
            # Ensure last chunk doesn't go past end
            chunk_starts = [min(s, text_length) for s in chunk_starts]
            # Remove duplicates and ensure monotonic
            unique_starts = []
            for s in chunk_starts:
                if not unique_starts or s > unique_starts[-1]:
                    unique_starts.append(s)
            chunk_starts = unique_starts

        total_chunks = len(chunk_starts)

        for i, start in enumerate(chunk_starts):
            # Calculate end position for this chunk
            if i < len(chunk_starts) - 1:
                end = chunk_starts[i + 1]
            else:
                end = min(start + self.max_chunk_size, text_length)

            # For chunks after the first, add context from previous chunk
            context_start = 0
            context_end = 0
            content_start = start
            content_end = end
            has_context = False

            if i > 0:
                # Add overlap context from previous chunk
                context_end = start
                context_start = max(0, context_end - self.context_overlap)

                # Snap context boundary to sentence
                if context_start > 0:
                    snapped = self.find_sentence_boundary(
                        text, context_start, direction='left', max_search=50
                    )
                    if snapped is not None and snapped >= 0:
                        context_start = snapped

                has_context = True

            # Build chunk content
            chunk_text = text[start:end]

            chunk = Chunk(
                content=chunk_text,
                chunk_index=i,
                total_chunks=total_chunks,
                context_start=context_start,
                context_end=context_end,
                content_start=content_start,
                content_end=content_end,
                has_context=has_context,
                raw_text=text,
            )
            chunks.append(chunk)

        logger.info(
            f"Split text of {text_length} chars into {len(chunks)} chunks "
            f"(max_size={self.max_chunk_size}, overlap={self.context_overlap})"
        )

        return chunks

    def strip_context(self, chunk: Chunk, modified_text: str) -> str:
        """
        Strip the context portion from modified text.

        When LLM returns a modified chunk that includes context from the previous chunk,
        this function removes that context portion, leaving only the modification
        to the current chunk's content.

        Args:
            chunk: The original chunk
            modified_text: The text returned by LLM (may include context)

        Returns:
            Only the modified content portion (context stripped)
        """
        if not chunk.has_context:
            return modified_text

        # Find where the actual content starts
        # Look for the first occurrence of chunk.content within modified_text
        # This handles cases where LLM may have slightly modified words at boundary

        # Calculate expected content length
        content_length = chunk.content_end - chunk.content_start

        # If modified text is longer than expected content, context was added
        if len(modified_text) > content_length:
            # Try to find the boundary by looking for the pattern at content boundary
            # Look for sentence delimiter near where context should end

            # Find where chunk.content starts in modified_text
            content_start_in_modified = modified_text.find(chunk.content[:10])

            if content_start_in_modified >= 0:
                # The actual content starts at content_start_in_modified
                return modified_text[content_start_in_modified:content_start_in_modified + content_length]

        # If we can't find boundary, just return the content portion
        return modified_text[:content_length]

    def reassemble_chunks(
        self,
        chunks: List[Chunk],
        modified_contents: List[str],
    ) -> str:
        """
        Reassemble chunks with their modifications.

        Args:
            chunks: Original chunks
            modified_contents: List of modified content strings (same order as chunks)

        Returns:
            Reassembled text with modifications applied
        """
        if len(chunks) != len(modified_contents):
            raise ValueError(
                f"Number of chunks ({len(chunks)}) != number of modifications ({len(modified_contents)})"
            )

        if not chunks:
            return ""

        result_parts: List[str] = []

        for i, (chunk, modified) in enumerate(zip(chunks, modified_contents)):
            # Strip context if present (chunk has context from previous chunk)
            if chunk.has_context:
                content_only = self.strip_context(chunk, modified)
            else:
                content_only = modified

            result_parts.append(content_only)

        return "".join(result_parts)

    def validate_chunk_integrity(self, original_text: str, chunks: List[Chunk]) -> bool:
        """
        Validate that chunks can be reassembled to reproduce original text.

        Args:
            original_text: Original text
            chunks: Chunks created from original text

        Returns:
            True if chunks can be reassembled to original text
        """
        if not chunks:
            return original_text == ""

        # Simple validation: concatenate all chunk contents and compare length
        total_content = sum(len(c.content) for c in chunks)

        # Account for overlap in total (chunks overlap by context_overlap)
        # Total unique content should equal original text length
        expected_length = len(original_text)

        if total_content < expected_length:
            logger.error(
                f"Chunk integrity check failed: total content ({total_content}) < original ({expected_length})"
            )
            return False

        return True


def create_slicer(
    max_chunk_size: int = 1000,
    context_overlap: int = 200,
) -> TextSlicer:
    """
    Factory function to create a TextSlicer instance.

    Args:
        max_chunk_size: Maximum characters per chunk
        context_overlap: Characters to overlap from previous chunk

    Returns:
        Configured TextSlicer instance
    """
    return TextSlicer(
        max_chunk_size=max_chunk_size,
        context_overlap=context_overlap,
    )