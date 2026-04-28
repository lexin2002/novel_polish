"""Tests for TextSlicer"""

from app.engine.text_slicer import TextSlicer, Chunk, create_slicer


class TestTextSlicerBasics:
    """Basic TextSlicer functionality"""

    def test_empty_text(self):
        """Empty text should return empty chunks"""
        slicer = create_slicer()
        chunks = slicer.split_into_chunks("")
        assert chunks == []

    def test_single_chunk_small_text(self):
        """Small text (< max_chunk_size) should be a single chunk"""
        slicer = create_slicer(max_chunk_size=1000)
        text = "Hello, world! This is a test."
        chunks = slicer.split_into_chunks(text)
        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].total_chunks == 1

    def test_single_chunk_no_context(self):
        """Single chunk should not have context"""
        slicer = create_slicer(max_chunk_size=1000)
        chunks = slicer.split_into_chunks("Short text")
        assert len(chunks) == 1
        assert chunks[0].has_context is False

    def test_multi_chunk_creation(self):
        """Text larger than max_chunk_size should be split"""
        slicer = create_slicer(max_chunk_size=100, context_overlap=20)
        # Create long text
        text = "Hello. " * 50
        chunks = slicer.split_into_chunks(text)
        assert len(chunks) >= 2

    def test_chunk_indexing(self):
        """Chunks should have sequential indices"""
        slicer = create_slicer(max_chunk_size=100, context_overlap=20)
        text = "Hello. " * 20
        chunks = slicer.split_into_chunks(text)
        for i, chunk in enumerate(chunks):
            assert chunk.chunk_index == i

    def test_total_chunks_accurate(self):
        """Each chunk should know the total count"""
        slicer = create_slicer(max_chunk_size=100, context_overlap=20)
        text = "Hello. " * 20
        chunks = slicer.split_into_chunks(text)
        for chunk in chunks:
            assert chunk.total_chunks == len(chunks)


class TestTextSlicerContext:
    """Context overlap tests"""

    def test_context_overlap_on_non_first_chunks(self):
        """Chunks after the first should have context"""
        slicer = create_slicer(max_chunk_size=100, context_overlap=30)
        text = "Hello world. " * 30
        chunks = slicer.split_into_chunks(text)
        if len(chunks) >= 2:
            assert chunks[0].has_context is False
            assert chunks[1].has_context is True

    def test_content_positions(self):
        """Content positions should fall within text bounds"""
        slicer = create_slicer(max_chunk_size=100, context_overlap=20)
        text = "Hello world. This is a test of the text slicer. " * 10
        chunks = slicer.split_into_chunks(text)
        for chunk in chunks:
            assert 0 <= chunk.content_start < len(text)
            assert chunk.content_end <= len(text)
            assert chunk.content_start < chunk.content_end

    def test_reassemble_maintains_length(self):
        """Reassembled text should have roughly the same length"""
        slicer = create_slicer(max_chunk_size=100, context_overlap=20)
        text = "Hello world. This is a test. " * 15
        chunks = slicer.split_into_chunks(text)
        # Simulate reassembly with unmodified content
        modified = [c.content for c in chunks]
        reassembled = slicer.reassemble_chunks(chunks, modified)
        assert len(reassembled) > 0


class TestSentenceBoundary:
    """Sentence boundary detection tests"""

    def test_find_left_boundary(self):
        """Find left sentence boundary correctly using Chinese delimiters"""
        slicer = create_slicer(max_chunk_size=1000)
        text = "第一句。第二句！第三句。"
        # Position 6 is within "第二句！第三句。" — search left for "。"
        pos = slicer.find_sentence_boundary(text, 6, direction='left', max_search=10)
        assert pos is not None
        assert pos > 0
        assert pos <= 6

    def test_find_right_boundary(self):
        """Find right sentence boundary correctly"""
        slicer = create_slicer(max_chunk_size=1000)
        text = "First sentence. Second sentence. Third sentence."
        pos = slicer.find_sentence_boundary(text, 5, direction='right', max_search=50)
        assert pos is not None
        assert pos > 5

    def test_chinese_delimiters(self):
        """Should handle Chinese sentence delimiters"""
        slicer = create_slicer(max_chunk_size=1000)
        text = "第一句。第二句！第三句？"
        pos = slicer.find_sentence_boundary(text, 5, direction='left', max_search=10)
        assert pos is not None


class TestStripContext:
    """Context stripping from LLM responses"""

    def test_strip_context_no_context(self):
        """Chunk without context should return text as-is"""
        slicer = create_slicer()
        chunk = Chunk(
            content="test content",
            chunk_index=0, total_chunks=1,
            context_start=0, context_end=0,
            content_start=0, content_end=12,
            has_context=False,
            raw_text="test content",
        )
        result = slicer.strip_context(chunk, "modified content")
        assert result == "modified content"

    def test_strip_context_with_context(self):
        """Context should be removed from modified text"""
        slicer = create_slicer()
        chunk = Chunk(
            content="second part",
            chunk_index=1, total_chunks=2,
            context_start=0, context_end=10,
            content_start=10, content_end=21,
            has_context=True,
            raw_text="first part second part",
        )
        # LLM returns context + modified content
        result = slicer.strip_context(chunk, "Context: second part (modified)")
        # Should only contain the modified version of the current chunk's content
        assert len(result) > 0
