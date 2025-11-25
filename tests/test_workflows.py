"""Unit tests for workflow executors."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

# Add actor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.clients import APIResult
from src.workflows import (
    execute_direct,
    execute_exploratory,
    execute_synthesis,
    WorkflowResult,
)


def make_mock_client(
    ref_result=None,
    exa_result=None,
    exa_code_result=None,
    jina_result=None,
    jina_arxiv_result=None,
    jina_read_results=None,
    perplexity_result=None,
    perplexity_synth_result=None,
):
    """Create a mock ResearchClient with configurable results."""
    client = MagicMock()

    # Default successful results
    default_result = APIResult(source="test", success=True, data={}, urls_found=[])

    client.ref_search = AsyncMock(return_value=ref_result or default_result)
    client.exa_search = AsyncMock(return_value=exa_result or default_result)
    client.exa_code_search = AsyncMock(return_value=exa_code_result or default_result)
    client.jina_search = AsyncMock(return_value=jina_result or default_result)
    client.jina_arxiv_search = AsyncMock(return_value=jina_arxiv_result or default_result)
    client.jina_read_url = AsyncMock(return_value=default_result)
    client.jina_read_urls = AsyncMock(return_value=jina_read_results or [default_result])
    client.perplexity_search = AsyncMock(return_value=perplexity_result or default_result)
    client.perplexity_synthesize = AsyncMock(return_value=perplexity_synth_result or default_result)

    return client


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_default_values(self):
        """WorkflowResult should have sensible defaults."""
        result = WorkflowResult(workflow="test", success=True)
        assert result.workflow == "test"
        assert result.success is True
        assert result.query_type == "general"
        assert result.sources_consulted == 0
        assert result.successful_sources == 0
        assert result.findings == []
        assert result.synthesis is None
        assert result.urls_discovered == []
        assert result.error is None

    def test_full_result(self):
        """WorkflowResult should store all fields."""
        result = WorkflowResult(
            workflow="synthesis",
            success=True,
            query_type="code",
            sources_consulted=5,
            successful_sources=4,
            findings=[{"source": "test"}],
            synthesis="Key findings...",
            urls_discovered=["https://example.com"],
            error=None
        )
        assert result.sources_consulted == 5
        assert result.synthesis == "Key findings..."


class TestDirectWorkflow:
    """Tests for DIRECT workflow execution."""

    async def test_documentation_query_routes_to_ref(self):
        """Documentation queries should use Ref as primary source."""
        ref_result = APIResult(
            source="ref",
            success=True,
            data={"results": [{"title": "Docs", "url": "https://docs.example.com"}]},
            urls_found=["https://docs.example.com"]
        )
        client = make_mock_client(ref_result=ref_result)

        result = await execute_direct(client, "FastAPI documentation for WebSockets")

        assert result.workflow == "direct"
        assert result.query_type == "documentation"
        assert result.success is True
        client.ref_search.assert_called()

    async def test_code_query_routes_to_exa_code(self):
        """Code queries should use Exa code search as primary source."""
        exa_code_result = APIResult(
            source="exa_code",
            success=True,
            data={"results": [{"url": "https://github.com/example"}]},
            urls_found=["https://github.com/example"]
        )
        client = make_mock_client(exa_code_result=exa_code_result)

        result = await execute_direct(client, "Code example for React hooks implementation")

        assert result.query_type == "code"
        assert result.success is True
        client.exa_code_search.assert_called()

    async def test_academic_query_routes_to_arxiv(self):
        """Academic queries should use Jina arXiv as primary source."""
        arxiv_result = APIResult(
            source="jina_arxiv",
            success=True,
            data={"data": [{"url": "https://arxiv.org/abs/2301.00001"}]},
            urls_found=["https://arxiv.org/abs/2301.00001"]
        )
        client = make_mock_client(jina_arxiv_result=arxiv_result)

        result = await execute_direct(client, "Research paper on transformer architecture")

        assert result.query_type == "academic"
        assert result.success is True
        client.jina_arxiv_search.assert_called()

    async def test_general_query_routes_to_jina(self):
        """General queries should use Jina web search as primary source."""
        jina_result = APIResult(
            source="jina",
            success=True,
            data={"data": [{"url": "https://example.com"}]},
            urls_found=["https://example.com"]
        )
        client = make_mock_client(jina_result=jina_result)

        result = await execute_direct(client, "What is Python programming")

        assert result.query_type == "general"
        assert result.success is True
        client.jina_search.assert_called()

    async def test_fallback_on_insufficient_results(self):
        """Should fallback to secondary source if primary returns few URLs."""
        ref_result = APIResult(
            source="ref",
            success=True,
            data={"results": [{"url": "https://single.url"}]},
            urls_found=["https://single.url"]  # Only 1 URL
        )
        exa_result = APIResult(
            source="exa",
            success=True,
            data={"results": []},
            urls_found=["https://more.com/1", "https://more.com/2"]
        )
        client = make_mock_client(ref_result=ref_result, exa_result=exa_result)

        result = await execute_direct(client, "FastAPI docs")

        # Should have called both Ref and Exa
        client.ref_search.assert_called()
        client.exa_search.assert_called()

    async def test_handles_api_failure(self):
        """Should handle API failures gracefully."""
        failed_result = APIResult(source="ref", success=False, error="HTTP 500")
        client = make_mock_client(ref_result=failed_result)

        result = await execute_direct(client, "FastAPI documentation")

        assert result.success is False or len(result.findings) == 0


class TestExploratoryWorkflow:
    """Tests for EXPLORATORY workflow execution."""

    async def test_starts_with_perplexity(self):
        """Exploratory workflow should start with Perplexity."""
        perplexity_result = APIResult(
            source="perplexity",
            success=True,
            data={
                "choices": [{"message": {"content": "Overview..."}}],
                "citations": ["https://source1.com"]
            },
            urls_found=["https://source1.com"]
        )
        client = make_mock_client(perplexity_result=perplexity_result)

        result = await execute_exploratory(client, "What is machine learning")

        assert result.workflow == "exploratory"
        client.perplexity_search.assert_called()

    async def test_secondary_search_based_on_query_type(self):
        """Should perform query-type-aware secondary search."""
        perplexity_result = APIResult(
            source="perplexity", success=True, data={}, urls_found=[]
        )
        arxiv_result = APIResult(
            source="jina_arxiv", success=True,
            data={"data": []}, urls_found=[]
        )
        client = make_mock_client(
            perplexity_result=perplexity_result,
            jina_arxiv_result=arxiv_result
        )

        result = await execute_exploratory(client, "Research paper on neural networks")

        assert result.query_type == "academic"
        client.jina_arxiv_search.assert_called()

    async def test_deep_reads_urls(self):
        """Should deep read discovered URLs."""
        perplexity_result = APIResult(
            source="perplexity", success=True, data={},
            urls_found=["https://url1.com", "https://url2.com"]
        )
        # Also need secondary search result with URLs
        jina_result = APIResult(
            source="jina", success=True, data={"data": []},
            urls_found=["https://url3.com"]
        )
        jina_read_results = [
            APIResult(source="jina_read", success=True, data={"content": "Content 1"}),
            APIResult(source="jina_read", success=True, data={"content": "Content 2"}),
        ]
        client = make_mock_client(
            perplexity_result=perplexity_result,
            jina_result=jina_result,
            jina_read_results=jina_read_results
        )

        result = await execute_exploratory(client, "test query", max_urls=3)

        client.jina_read_urls.assert_called()
        # Should have findings from URL reads
        url_findings = [f for f in result.findings if f.get("type") == "url_content"]
        assert len(url_findings) > 0

    async def test_respects_max_urls(self):
        """Should respect max_urls parameter."""
        perplexity_result = APIResult(
            source="perplexity", success=True, data={},
            urls_found=["https://url1.com", "https://url2.com", "https://url3.com"]
        )
        client = make_mock_client(perplexity_result=perplexity_result)

        await execute_exploratory(client, "test", max_urls=2)

        # Check that jina_read_urls was called with max 2 URLs
        call_args = client.jina_read_urls.call_args
        if call_args:
            urls_arg = call_args[0][0]
            assert len(urls_arg) <= 2


class TestSynthesisWorkflow:
    """Tests for SYNTHESIS workflow execution."""

    async def test_triple_stack_parallel_execution(self):
        """Synthesis should run Triple Stack in parallel."""
        ref_result = APIResult(
            source="ref", success=True,
            data={"results": []}, urls_found=["https://ref.com"]
        )
        exa_result = APIResult(
            source="exa", success=True,
            data={"results": []}, urls_found=["https://exa.com"]
        )
        jina_result = APIResult(
            source="jina", success=True,
            data={"data": []}, urls_found=["https://jina.com"]
        )
        client = make_mock_client(
            ref_result=ref_result,
            exa_result=exa_result,
            jina_result=jina_result
        )

        result = await execute_synthesis(client, "Compare FastAPI vs Flask")

        assert result.workflow == "synthesis"
        # All three should have been called
        client.ref_search.assert_called()
        client.exa_search.assert_called()
        client.jina_search.assert_called()

    async def test_academic_triple_stack(self):
        """Academic queries should use arXiv in Triple Stack."""
        arxiv_result = APIResult(
            source="jina_arxiv", success=True,
            data={"data": []}, urls_found=[]
        )
        client = make_mock_client(jina_arxiv_result=arxiv_result)

        result = await execute_synthesis(client, "Research paper on transformer vs RNN")

        assert result.query_type == "academic"
        client.jina_arxiv_search.assert_called()

    async def test_code_triple_stack(self):
        """Code queries should use Exa code search in Triple Stack."""
        exa_code_result = APIResult(
            source="exa_code", success=True,
            data={"results": []}, urls_found=[]
        )
        client = make_mock_client(exa_code_result=exa_code_result)

        result = await execute_synthesis(client, "Compare code implementation of sorting algorithms")

        assert result.query_type == "code"
        client.exa_code_search.assert_called()

    async def test_perplexity_synthesis(self):
        """Should synthesize findings with Perplexity."""
        ref_result = APIResult(
            source="ref", success=True,
            data={"results": [{"text": "Ref content"}]},
            urls_found=[]
        )
        synth_result = APIResult(
            source="perplexity_synthesis", success=True,
            data={
                "choices": [{"message": {"content": "Synthesis: ..."}}]
            }
        )
        client = make_mock_client(
            ref_result=ref_result,
            perplexity_synth_result=synth_result
        )

        result = await execute_synthesis(client, "Compare X vs Y")

        client.perplexity_synthesize.assert_called()
        assert result.synthesis is not None

    async def test_synthesis_with_url_content(self):
        """Synthesis should include URL content in context."""
        ref_result = APIResult(
            source="ref", success=True,
            data={"results": []},
            urls_found=["https://example.com"]
        )
        jina_read_results = [
            APIResult(
                source="jina_read", success=True,
                data={"content": "Important content from URL"}
            )
        ]
        synth_result = APIResult(
            source="perplexity_synthesis", success=True,
            data={"choices": [{"message": {"content": "Final synthesis"}}]}
        )
        client = make_mock_client(
            ref_result=ref_result,
            jina_read_results=jina_read_results,
            perplexity_synth_result=synth_result
        )

        result = await execute_synthesis(client, "Compare X vs Y")

        # Check that URL content was included
        url_findings = [f for f in result.findings if f.get("type") == "url_content"]
        assert len(url_findings) > 0

    async def test_handles_partial_failures(self):
        """Should handle partial API failures gracefully."""
        ref_result = APIResult(source="ref", success=False, error="HTTP 500")
        exa_result = APIResult(
            source="exa", success=True,
            data={"results": [{"text": "Working"}]},
            urls_found=[]
        )
        jina_result = APIResult(source="jina", success=False, error="Timeout")

        client = make_mock_client(
            ref_result=ref_result,
            exa_result=exa_result,
            jina_result=jina_result
        )

        result = await execute_synthesis(client, "Compare X vs Y")

        # Should still succeed with partial results
        assert result.sources_consulted > 0
        assert result.successful_sources > 0
        assert len(result.findings) > 0


class TestWorkflowEdgeCases:
    """Tests for edge cases in workflows."""

    async def test_empty_urls_discovered(self):
        """Should handle case with no URLs discovered."""
        empty_result = APIResult(
            source="ref", success=True,
            data={"results": []},
            urls_found=[]
        )
        client = make_mock_client(ref_result=empty_result)

        result = await execute_direct(client, "test docs")

        assert result.urls_discovered == []

    async def test_duplicate_url_deduplication(self):
        """Should deduplicate discovered URLs."""
        result_with_dupes = APIResult(
            source="perplexity", success=True,
            data={},
            urls_found=[
                "https://example.com",
                "https://example.com",  # Duplicate
                "https://other.com"
            ]
        )
        client = make_mock_client(perplexity_result=result_with_dupes)

        result = await execute_exploratory(client, "test", max_urls=5)

        # URLs should be deduplicated
        assert len(result.urls_discovered) == len(set(result.urls_discovered))

    async def test_all_apis_fail(self):
        """Should handle case where all APIs fail."""
        failed = APIResult(source="test", success=False, error="Failed")
        client = make_mock_client(
            ref_result=failed,
            exa_result=failed,
            jina_result=failed,
            perplexity_result=failed
        )

        result = await execute_synthesis(client, "test")

        assert result.successful_sources == 0
        assert len(result.findings) == 0
