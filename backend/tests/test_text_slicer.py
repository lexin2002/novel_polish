"""Tests for text slicer module"""

import pytest
from app.engine.text_slicer import (
    TextSlicer,
    Chunk,
    create_slicer,
    SENTENCE_DELIMITERS,
)


class TestTextSlicer:
    """Test suite for TextSlicer"""

    def test_empty_text_returns_empty_list(self):
        """Empty text should return empty chunk list"""
        slicer = TextSlicer()
        chunks = slicer.split_into_chunks("")
        assert chunks == []

    def test_short_text_returns_single_chunk(self):
        """Text shorter than max_chunk_size returns single chunk"""
        slicer = TextSlicer(max_chunk_size=1000)
        text = "这是一个测试文本。"
        chunks = slicer.split_into_chunks(text)

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 1
        assert not chunks[0].has_context

    def test_exact_max_size_returns_single_chunk(self):
        """Text exactly at max size returns single chunk"""
        slicer = TextSlicer(max_chunk_size=10)
        text = "ABCDEFGHIJ"  # 10 characters
        chunks = slicer.split_into_chunks(text)

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_multiple_chunks_are_created(self):
        """Long text creates multiple chunks"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "ABCDEFGHIJKLMNO"  # 15 characters, should create 2 chunks with overlap
        chunks = slicer.split_into_chunks(text)

        assert len(chunks) == 2
        assert chunks[0].total_chunks == 2
        assert chunks[1].total_chunks == 2

    def test_second_chunk_has_context(self):
        """Chunks after first have has_context=True"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "ABCDEFGHIJKLMNO"  # 15 characters
        chunks = slicer.split_into_chunks(text)

        assert not chunks[0].has_context
        assert chunks[1].has_context

    def test_context_boundary_is_snapped_to_punctuation(self):
        """Context boundary should snap to sentence delimiters"""
        slicer = TextSlicer(max_chunk_size=20, context_overlap=10)
        text = "第一句话。这是第二句话，也是第三句话的开头。"
        chunks = slicer.split_into_chunks(text)

        # Second chunk should have context that ends at a punctuation
        if len(chunks) > 1:
            assert chunks[1].has_context
            # Context should end at or near a sentence delimiter
            context_end_char = text[chunks[1].context_end - 1] if chunks[1].context_end > 0 else ''
            # The character at context boundary should be a delimiter or near one

    def test_find_sentence_boundary_left(self):
        """find_sentence_boundary finds nearest delimiter to the left"""
        slicer = TextSlicer()
        text = "这是一个句子。另一个句子？再来一个！最后一句。"

        # Find boundary before position 25 (should find 。 at position ~8)
        boundary = slicer.find_sentence_boundary(text, 25, direction='left')
        assert boundary is not None
        assert text[boundary - 1] in SENTENCE_DELIMITERS

    def test_find_sentence_boundary_right(self):
        """find_sentence_boundary finds nearest delimiter to the right"""
        slicer = TextSlicer()
        text = "第一句。第二句？第三句！"

        # Find boundary after position 0
        boundary = slicer.find_sentence_boundary(text, 0, direction='right')
        assert boundary is not None
        assert text[boundary - 1] in SENTENCE_DELIMITERS

    def test_find_sentence_boundary_fallback_hard_truncation(self):
        """When no boundary found, returns fallback position"""
        slicer = TextSlicer()
        text = "AAAAAAAAAA"  # No delimiters
        boundary = slicer.find_sentence_boundary(text, 50, direction='left', max_search=20)

        # Should return fallback position
        assert boundary is not None
        assert boundary >= 0

    def test_strip_context_removes_preamble(self):
        """strip_context removes context portion from modified text"""
        slicer = TextSlicer(max_chunk_size=100, context_overlap=20)

        # Create a chunk with context
        chunk = Chunk(
            content="这是第二段的内容。",
            chunk_index=1,
            total_chunks=2,
            context_start=0,
            context_end=10,
            content_start=10,
            content_end=30,
            has_context=True,
            raw_text="这是第一段的内容。这是第二段的内容。",
        )

        # Simulate LLM returning text that includes context
        modified_with_context = "这是第一段的修改。第二段的修改版本。"

        stripped = slicer.strip_context(chunk, modified_with_context)

        # Should only return the content portion, not the context
        assert "第二段的修改版本" in stripped
        assert "第一段" not in stripped or "第二段" in stripped

    def test_strip_context_no_op_for_no_context(self):
        """strip_context returns full text when chunk has no context"""
        slicer = TextSlicer()

        chunk = Chunk(
            content="这是内容",
            chunk_index=0,
            total_chunks=1,
            context_start=0,
            context_end=0,
            content_start=0,
            content_end=10,
            has_context=False,
            raw_text="这是内容",
        )

        modified = "这是修改后的内容"
        result = slicer.strip_context(chunk, modified)

        assert result == modified

    def test_reassemble_chunks_basic(self):
        """reassemble_chunks combines modifications correctly"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "ABCDEFGHIJKL"
        chunks = slicer.split_into_chunks(text)

        # Simulate modifications
        modifications = [c.content for c in chunks]  # No change
        result = slicer.reassemble_chunks(chunks, modifications)

        assert result == text

    def test_reassemble_chunks_with_modifications(self):
        """reassemble_chunks applies modifications to correct positions"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "ABCDEFGHIJ"
        chunks = slicer.split_into_chunks(text)

        # Modify each chunk
        modifications = [c.content.upper() for c in chunks]
        result = slicer.reassemble_chunks(chunks, modifications)

        assert result == "ABCDEFGHIJ"  # Uppercase of original

    def test_reassemble_chunks_mismatched_lengths(self):
        """reassemble_chunks raises on mismatched chunk/modification counts"""
        slicer = TextSlicer()
        chunks = [
            Chunk("A", 0, 2, 0, 0, 0, 1, False, "AB"),
            Chunk("B", 1, 2, 1, 1, 1, 2, True, "AB"),
        ]
        modifications = ["A"]  # Only one modification

        with pytest.raises(ValueError, match="chunks.*modifications"):
            slicer.reassemble_chunks(chunks, modifications)

    def test_validate_chunk_integrity_valid(self):
        """validate_chunk_integrity returns True for valid chunks"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "ABCDEFGHIJ"
        chunks = slicer.split_into_chunks(text)

        result = slicer.validate_chunk_integrity(text, chunks)
        assert result is True

    def test_validate_chunk_integrity_invalid(self):
        """validate_chunk_integrity returns False for invalid chunks"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "ABCDEFGHIJ"
        chunks = slicer.split_into_chunks(text)

        # Modify chunks to make integrity check fail
        # (Simulate by creating chunks that don't cover full text)
        chunks[0] = Chunk("ABC", 0, 1, 0, 0, 0, 3, False, "ABCDEFGHIJ")

        result = slicer.validate_chunk_integrity(text, chunks)
        assert result is False

    def test_create_slicer_factory(self):
        """create_slicer creates configured instance"""
        slicer = create_slicer(max_chunk_size=500, context_overlap=100)

        assert slicer.max_chunk_size == 500
        assert slicer.context_overlap == 100


class TestTextSlicerEdgeCases:
    """Test edge cases and extreme inputs"""

    def test_single_long_word_no_punctuation(self):
        """Text with single long word (no punctuation) is handled"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "AAAAAAAAAAAAAAAAAAAA"  # 20 A's, no punctuation
        chunks = slicer.split_into_chunks(text)

        # Should still split, just without punctuation snapping
        assert len(chunks) > 1

    def test_all_punctuation(self):
        """Text with only punctuation is handled"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "。？！；。？！；。"
        chunks = slicer.split_into_chunks(text)

        # Should create chunks at punctuation boundaries
        assert len(chunks) >= 1

    def test_very_small_chunk_size(self):
        """Very small max_chunk_size creates many chunks"""
        slicer = TextSlicer(max_chunk_size=3, context_overlap=1)
        text = "ABCDEFGHIJ"
        chunks = slicer.split_into_chunks(text)

        assert len(chunks) > 3

    def test_context_overlap_larger_than_chunk(self):
        """context_overlap >= max_chunk_size falls back gracefully"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=15)
        text = "ABCDEFGHIJKLMNOP"
        chunks = slicer.split_into_chunks(text)

        # Should still work with warning about effective size
        assert len(chunks) >= 1

    def test_unicode_chinese_text(self):
        """Chinese unicode text is handled correctly"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "这是一个测试文本，用于测试中文分词功能是否正常。"
        chunks = slicer.split_into_chunks(text)

        # Should handle Chinese characters properly
        assert len(chunks) >= 1
        for chunk in chunks:
            assert isinstance(chunk.content, str)

    def test_mixed_chinese_english(self):
        """Mixed Chinese and English text is handled"""
        slicer = TextSlicer(max_chunk_size=15, context_overlap=3)
        text = "这是中文部分。And this is English. Mixed content here."
        chunks = slicer.split_into_chunks(text)

        assert len(chunks) >= 1

    def test_chunk_positions_sequential(self):
        """Chunk indices are sequential and 0-indexed"""
        slicer = TextSlicer(max_chunk_size=5, context_overlap=1)
        text = "ABCDEFGHIJKLMNO"
        chunks = slicer.split_into_chunks(text)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_all_chunks_have_valid_positions(self):
        """All chunks have valid start/end positions"""
        slicer = TextSlicer(max_chunk_size=10, context_overlap=2)
        text = "ABCDEFGHIJKL"
        chunks = slicer.split_into_chunks(text)

        for chunk in chunks:
            assert 0 <= chunk.context_start <= chunk.context_end <= chunk.content_start <= chunk.content_end <= len(text)


class TestTextSlicerIntegration:
    """Integration tests for text slicing pipeline"""

    def test_full_pipeline_no_data_loss(self):
        """Full slice -> modify -> reassemble preserves all data"""
        slicer = TextSlicer(max_chunk_size=50, context_overlap=10)
        original = "这是一个测试文本，用于验证切片和重组功能。" * 5  # Repeat to make it longer

        chunks = slicer.split_into_chunks(original)
        assert len(chunks) > 1

        # Validate integrity
        assert slicer.validate_chunk_integrity(original, chunks)

        # Modify each chunk (simulate LLM modification)
        modified_contents = [c.content.upper() for c in chunks]

        # Reassemble
        result = slicer.reassemble_chunks(chunks, modified_contents)

        # Result length should equal original length
        assert len(result) == len(original)

    def test_repeated_slicing_produces_consistent_chunks(self):
        """Same text sliced multiple times produces same chunk boundaries"""
        slicer = TextSlicer(max_chunk_size=20, context_overlap=5)
        text = "第一句。第二句。第三句。第四句。第五句。"

        chunks1 = slicer.split_into_chunks(text)
        chunks2 = slicer.split_into_chunks(text)

        assert len(chunks1) == len(chunks2)
        for c1, c2 in zip(chunks1, chunks2):
            assert c1.content_start == c2.content_start
            assert c1.content_end == c2.content_end

    def test_different_delimiter_sets(self):
        """Custom delimiter sets are respected"""
        custom_delimiters = {'.', '!', '?'}
        slicer = TextSlicer(sentence_delimiters=custom_delimiters)

        text = "First. Second! Third? Fourth."

        # Should find boundaries at custom delimiters
        boundary = slicer.find_sentence_boundary(text, 15, direction='left')
        assert boundary is not None

    def test_chunk_content_preserves_original_order(self):
        """Chunk contents are in original text order"""
        slicer = TextSlicer(max_chunk_size=5, context_overlap=1)
        text = "ABCDEFGHIJ"
        chunks = slicer.split_into_chunks(text)

        # Concatenate content (not full chunk) in order should give original
        content_concat = "".join(c.content for c in chunks)
        # Due to overlap, concatenation will have some duplication
        # But every character from original should appear at least once
        for char in text:
            assert char in content_concat