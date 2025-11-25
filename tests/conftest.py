"""Shared test fixtures and configuration."""

import pytest
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add actor directory to path so we can import src as a package
actor_dir = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, actor_dir)

from src.clients import ResearchClient, APIResult
from src.workflows import WorkflowResult


@pytest.fixture
def mock_api_keys():
    """Fake API keys for testing."""
    return {
        "ref_key": "test-ref-key",
        "exa_key": "test-exa-key",
        "jina_key": "test-jina-key",
        "perplexity_key": "test-perplexity-key",
    }


@pytest.fixture
def mock_client(mock_api_keys):
    """Create a ResearchClient with mocked HTTP."""
    client = ResearchClient(**mock_api_keys)
    return client


@pytest.fixture
def successful_ref_result():
    """Mock successful Ref API result."""
    return APIResult(
        source="ref",
        success=True,
        data={
            "results": [
                {
                    "title": "FastAPI Documentation",
                    "url": "https://fastapi.tiangolo.com/tutorial/",
                    "content": "FastAPI is a modern, fast web framework..."
                },
                {
                    "title": "FastAPI Dependencies",
                    "url": "https://fastapi.tiangolo.com/tutorial/dependencies/",
                    "content": "Dependency injection in FastAPI..."
                }
            ]
        },
        urls_found=[
            "https://fastapi.tiangolo.com/tutorial/",
            "https://fastapi.tiangolo.com/tutorial/dependencies/"
        ]
    )


@pytest.fixture
def successful_exa_result():
    """Mock successful Exa API result."""
    return APIResult(
        source="exa",
        success=True,
        data={
            "results": [
                {
                    "title": "Building APIs with FastAPI",
                    "url": "https://example.com/fastapi-guide",
                    "text": "A comprehensive guide to building REST APIs..."
                }
            ]
        },
        urls_found=["https://example.com/fastapi-guide"]
    )


@pytest.fixture
def successful_jina_result():
    """Mock successful Jina API result."""
    return APIResult(
        source="jina",
        success=True,
        data={
            "data": [
                {
                    "title": "FastAPI vs Flask 2025",
                    "url": "https://example.com/fastapi-vs-flask",
                    "content": "Comparing FastAPI and Flask in 2025..."
                }
            ]
        },
        urls_found=["https://example.com/fastapi-vs-flask"]
    )


@pytest.fixture
def successful_perplexity_result():
    """Mock successful Perplexity API result."""
    return APIResult(
        source="perplexity",
        success=True,
        data={
            "choices": [
                {
                    "message": {
                        "content": "FastAPI is a modern Python framework that provides high performance..."
                    }
                }
            ],
            "citations": [
                "https://fastapi.tiangolo.com",
                "https://python.org"
            ]
        },
        urls_found=["https://fastapi.tiangolo.com", "https://python.org"]
    )


@pytest.fixture
def failed_api_result():
    """Mock failed API result."""
    return APIResult(
        source="ref",
        success=False,
        error="HTTP 500"
    )


@pytest.fixture
def sample_workflow_result():
    """Sample WorkflowResult for report tests."""
    return WorkflowResult(
        workflow="synthesis",
        query_type="documentation",
        success=True,
        sources_consulted=5,
        successful_sources=4,
        findings=[
            {
                "source": "ref",
                "type": "documentation",
                "data": {
                    "results": [
                        {"title": "Doc 1", "text": "Content 1"}
                    ]
                }
            },
            {
                "source": "perplexity",
                "type": "overview",
                "data": {
                    "choices": [
                        {"message": {"content": "Overview content here..."}}
                    ]
                }
            }
        ],
        synthesis="This is the synthesis of all findings. Key insights: ...",
        urls_discovered=["https://example.com/1", "https://example.com/2"]
    )
