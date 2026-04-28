"""Smart text slicing with dynamic punctuation snap and context preservation"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default sentence delimiters (Chinese punctuation)
SENTENCE_DELIMITERS = {'。', '！', '？', '；', '\n'}

@dataclass
class Chunk:
    """Represents a slice of text with context"""
    content: str
    chunk_index: int
    total_chunks: int
    context_text: str      # The actual text used as preceding context
    content_start: int    # Start position of content in original text
    content_end: int      # End position of content in original text
    has_context: bool     # Whether this chunk has preceding context
    raw_text: str          # Original text before any processing

    def __repr__(self) -> str:
        return (
            f"Chunk(index={self.chunk_index}/{self.total_chunks}, "
            f"has_context={self.has_context}, len={len(self.content)})"
        )

class TextSlicer:
    """Smart text slicer that preserves paragraph integrity and snaps to sentence boundaries."""

    def __init__(
        self,
        max_chunk_size: int = 1000,
        context_overlap: int = 200,
        sentence_delimiters: Optional[set] = None,
    ):
        self.max_chunk_size = max_chunk_size
        self.context_overlap = context_overlap
        self.sentence_delimiters = sentence_delimiters or SENTENCE_DELIMITERS

    def _snap_left(self, text: str, position: int) -> int:
        """Find the nearest sentence boundary to the left of position."""
        if position <= 0: return 0
        
        start = max(0, position - self.context_overlap * 2)
        search_text = text[start:position]
        
        for i in range(len(search_text) - 1, -1, -1):
            if search_text[i] in self.sentence_delimiters:
                return start + i + 1
        return start

    def split_into_chunks(self, text: str) -> List[Chunk]:
        """
        Split text into chunks using paragraph-first logic and semantic snapping.
        """
        if not text: return []

        paragraphs = text.split('\n')
        chunks_data = []
        current_chunk_text = []
        current_len = 0
        
        for p in paragraphs:
            if len(p) > self.max_chunk_size:
                if current_chunk_text:
                    chunks_data.append("\n".join(current_chunk_text))
                    current_chunk_text = []
                    current_len = 0
                
                p_pos = 0
                while p_pos < len(p):
                    end = p_pos + self.max_chunk_size
                    if end >= len(p):
                        chunks_data.append(p[p_pos:])
                        p_pos = len(p)
                    else:
                        search_area = p[p_pos:end]
                        last_punc = -1
                        for i in range(len(search_area)-1, -1, -1):
                            if search_area[i] in self.sentence_delimiters:
                                last_punc = i
                                break
                        
                        if last_punc != -1:
                            chunks_data.append(p[p_pos : p_pos + last_punc + 1])
                            p_pos += last_punc + 1
                        else:
                            chunks_data.append(p[p_pos:end])
                            p_pos = end
            else:
                if current_len + len(p) + 1 > self.max_chunk_size:
                    chunks_data.append("\n".join(current_chunk_text))
                    current_chunk_text = [p]
                    current_len = len(p)
                else:
                    current_chunk_text.append(p)
                    current_len += len(p) + 1
        
        if current_chunk_text:
            chunks_data.append("\n".join(current_chunk_text))

        chunks: List[Chunk] = []
        total_chunks = len(chunks_data)
        global_pos = 0
        
        for i, content in enumerate(chunks_data):
            content_start = global_pos
            content_end = global_pos + len(content)
            
            context_text = ""
            has_context = False
            if i > 0:
                raw_context_start = max(0, content_start - self.context_overlap)
                snapped_start = self._snap_left(text, raw_context_start)
                context_text = text[snapped_start : content_start]
                has_context = True
            
            chunks.append(Chunk(
                content=content,
                chunk_index=i,
                total_chunks=total_chunks,
                context_text=context_text,
                content_start=content_start,
                content_end=content_end,
                has_context=has_context,
                raw_text=text,
            ))
            global_pos = content_end + 1
            
        return chunks

    def reassemble_chunks(self, chunks: List[Chunk], modified_contents: List[str]) -> str:
        return "\n".join(modified_contents)

    def create_prompt_with_context(self, chunk: Chunk) -> Tuple[str, str]:
        context_part = f"<preceding_context>\n{chunk.context_text}\n</preceding_context>" if chunk.has_context else ""
        content_part = f"<novel_text>\n{chunk.content}\n</novel_text>"
        return context_part, content_part

def create_slicer(max_chunk_size: int = 1000, context_overlap: int = 200) -> TextSlicer:
    return TextSlicer(max_chunk_size=max_chunk_size, context_overlap=context_overlap)
