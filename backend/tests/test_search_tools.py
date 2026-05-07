"""
Tests for CourseSearchTool.execute() in search_tools.py.

These tests use a mocked VectorStore, so no ChromaDB or real embedding model is needed.
All tests here pass both before and after the bug fixes — they test CourseSearchTool's
own logic, which is correct. The tests document the error-string propagation path that
occurs when VectorStore.search() fails (e.g. due to MAX_RESULTS=0).
"""
import pytest
from unittest.mock import MagicMock
from vector_store import SearchResults
from search_tools import CourseSearchTool


def _populated_results(doc="Content", course="Test Course", lesson=1, link="http://ex.com"):
    return SearchResults(
        documents=[doc],
        metadata=[{"course_title": course, "lesson_number": lesson, "lesson_link": link}],
        distances=[0.1],
        error=None,
    )


class TestCourseSearchToolErrorPropagation:
    """
    Verifies the path taken when VectorStore.search() fails.
    With MAX_RESULTS=0, ChromaDB raises TypeError for n_results=0.
    VectorStore catches it and returns SearchResults(error="Search error: ...").
    CourseSearchTool.execute() must return that error string — not raise.
    """

    def test_returns_error_string_when_store_errors(self, mock_vector_store):
        error_msg = "Search error: Number of requested results 0, cannot be negative, or zero."
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=error_msg
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is machine learning?")

        assert result == error_msg
        mock_vector_store.search.assert_called_once_with(
            query="What is machine learning?",
            course_name=None,
            lesson_number=None,
        )

    def test_last_sources_stays_empty_when_search_errors(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error="Search error"
        )
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        assert tool.last_sources == []


class TestCourseSearchToolEmptyResults:
    """Verifies behavior when search succeeds but finds no matching content."""

    def test_returns_no_content_found_message(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is machine learning?")

        assert result == "No relevant content found."

    def test_no_content_message_includes_course_filter(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", course_name="ML Fundamentals")

        assert "No relevant content found" in result
        assert "ML Fundamentals" in result

    def test_no_content_message_includes_lesson_filter(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="test", lesson_number=3)

        assert "No relevant content found" in result
        assert "lesson 3" in result


class TestCourseSearchToolHappyPath:
    """Verifies correct formatting and source tracking when search returns content."""

    def test_formats_documents_with_course_and_lesson_header(self, mock_vector_store):
        mock_vector_store.search.return_value = _populated_results(
            doc="Neural networks are...",
            course="ML Fundamentals",
            lesson=2,
            link="https://example.com/lesson2",
        )
        tool = CourseSearchTool(mock_vector_store)
        result = tool.execute(query="What is machine learning?")

        assert "[ML Fundamentals - Lesson 2]" in result
        assert "Neural networks are..." in result

    def test_last_sources_populated_with_label_and_url(self, mock_vector_store):
        mock_vector_store.search.return_value = _populated_results(
            course="ML Fundamentals", lesson=1, link="https://example.com/lesson1"
        )
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        assert len(tool.last_sources) == 1
        assert tool.last_sources[0]["label"] == "ML Fundamentals - Lesson 1"
        assert tool.last_sources[0]["url"] == "https://example.com/lesson1"

    def test_get_lesson_link_called_when_metadata_missing_lesson_link(self, mock_vector_store):
        """When lesson_link is absent from metadata, VectorStore.get_lesson_link() is called."""
        mock_vector_store.search.return_value = SearchResults(
            documents=["Content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 2}],
            distances=[0.1],
            error=None,
        )
        mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson2"
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test")

        mock_vector_store.get_lesson_link.assert_called_once_with("Test Course", 2)
        assert tool.last_sources[0]["url"] == "https://example.com/lesson2"


class TestCourseSearchToolParameterForwarding:
    """Verifies that search parameters are correctly forwarded to VectorStore.search()."""

    def test_course_name_forwarded_to_store(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test", course_name="ML Fundamentals")

        mock_vector_store.search.assert_called_once_with(
            query="test",
            course_name="ML Fundamentals",
            lesson_number=None,
        )

    def test_lesson_number_forwarded_to_store(self, mock_vector_store):
        mock_vector_store.search.return_value = SearchResults(
            documents=[], metadata=[], distances=[], error=None
        )
        tool = CourseSearchTool(mock_vector_store)
        tool.execute(query="test", lesson_number=3)

        mock_vector_store.search.assert_called_once_with(
            query="test",
            course_name=None,
            lesson_number=3,
        )
