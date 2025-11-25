"""Integration tests with real APIs.

These tests require actual API keys and make real network calls.
Run with: pytest tests/test_integration.py -m integration

Set environment variables:
- REF_API_KEY
- EXA_API_KEY
- JINA_API_KEY
- PERPLEXITY_API_KEY
"""

import os
import sys
import pytest

# Add actor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.clients import ResearchClient
from src.workflows import execute_direct, execute_exploratory, execute_synthesis
from src.report import generate_report, generate_markdown_report


def get_api_keys():
    """Get API keys from environment."""
    return {
        "ref_key": os.environ.get("REF_API_KEY", ""),
        "exa_key": os.environ.get("EXA_API_KEY", ""),
        "jina_key": os.environ.get("JINA_API_KEY", ""),
        "perplexity_key": os.environ.get("PERPLEXITY_API_KEY", ""),
    }


def has_all_keys():
    """Check if all API keys are available."""
    keys = get_api_keys()
    return all(keys.values())


# Skip all integration tests if keys not available
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not has_all_keys(),
        reason="API keys not configured. Set REF_API_KEY, EXA_API_KEY, JINA_API_KEY, PERPLEXITY_API_KEY"
    )
]


@pytest.fixture
async def real_client():
    """Create a real ResearchClient with actual API keys."""
    keys = get_api_keys()
    client = ResearchClient(**keys)
    yield client
    await client.close()


class TestRealRefAPI:
    """Integration tests for Ref API."""

    @pytest.mark.slow
    async def test_ref_search_real(self, real_client):
        """Test real Ref API search."""
        result = await real_client.ref_search("FastAPI dependency injection")

        assert result.source == "ref"
        # May succeed or fail depending on API status
        if result.success:
            assert result.data is not None
            print(f"Ref found {len(result.urls_found or [])} URLs")


class TestRealExaAPI:
    """Integration tests for Exa API."""

    @pytest.mark.slow
    async def test_exa_search_real(self, real_client):
        """Test real Exa API search."""
        result = await real_client.exa_search("Python async await tutorial", num_results=5)

        assert result.source == "exa"
        if result.success:
            assert result.data is not None
            assert "results" in result.data
            print(f"Exa found {len(result.urls_found or [])} URLs")

    @pytest.mark.slow
    async def test_exa_code_search_real(self, real_client):
        """Test real Exa code search."""
        result = await real_client.exa_code_search("React hooks useState example", num_results=5)

        assert result.source == "exa_code"
        if result.success:
            print(f"Exa code found {len(result.urls_found or [])} URLs")


class TestRealJinaAPI:
    """Integration tests for Jina API."""

    @pytest.mark.slow
    async def test_jina_search_real(self, real_client):
        """Test real Jina web search."""
        result = await real_client.jina_search("AI trends 2025", num_results=5)

        assert result.source == "jina"
        if result.success:
            assert result.data is not None
            print(f"Jina found {len(result.urls_found or [])} URLs")

    @pytest.mark.slow
    async def test_jina_arxiv_search_real(self, real_client):
        """Test real Jina arXiv search."""
        result = await real_client.jina_arxiv_search("transformer attention mechanism", num_results=5)

        assert result.source == "jina_arxiv"
        if result.success:
            print(f"arXiv found {len(result.urls_found or [])} papers")

    @pytest.mark.slow
    async def test_jina_read_url_real(self, real_client):
        """Test real Jina URL reading."""
        result = await real_client.jina_read_url("https://example.com")

        assert result.source == "jina_read"
        if result.success:
            assert result.data is not None
            print(f"Read URL content length: {len(str(result.data))}")


class TestRealPerplexityAPI:
    """Integration tests for Perplexity API."""

    @pytest.mark.slow
    async def test_perplexity_search_real(self, real_client):
        """Test real Perplexity search."""
        result = await real_client.perplexity_search("What is retrieval augmented generation?")

        assert result.source == "perplexity"
        if result.success:
            assert result.data is not None
            assert "choices" in result.data
            print(f"Perplexity found {len(result.urls_found or [])} citations")


class TestRealDirectWorkflow:
    """Integration tests for DIRECT workflow."""

    @pytest.mark.slow
    async def test_direct_documentation_query(self, real_client):
        """Test direct workflow with documentation query."""
        result = await execute_direct(real_client, "FastAPI documentation for WebSockets")

        assert result.workflow == "direct"
        assert result.query_type == "documentation"
        print(f"Direct workflow: {result.sources_consulted} sources, {result.successful_sources} successful")
        print(f"Found {len(result.urls_discovered)} URLs")

    @pytest.mark.slow
    async def test_direct_code_query(self, real_client):
        """Test direct workflow with code query."""
        result = await execute_direct(real_client, "Code example for Python async context manager")

        assert result.workflow == "direct"
        assert result.query_type == "code"
        print(f"Direct (code): {result.successful_sources} successful sources")


class TestRealExploratoryWorkflow:
    """Integration tests for EXPLORATORY workflow."""

    @pytest.mark.slow
    async def test_exploratory_general_query(self, real_client):
        """Test exploratory workflow with general query."""
        result = await execute_exploratory(
            real_client,
            "What is vector database and how does it work?",
            max_urls=3
        )

        assert result.workflow == "exploratory"
        print(f"Exploratory: {result.sources_consulted} sources, {result.successful_sources} successful")
        print(f"Findings: {len(result.findings)}, URLs: {len(result.urls_discovered)}")

    @pytest.mark.slow
    async def test_exploratory_academic_query(self, real_client):
        """Test exploratory workflow with academic query."""
        result = await execute_exploratory(
            real_client,
            "Research paper on attention mechanisms in neural networks",
            max_urls=3
        )

        assert result.workflow == "exploratory"
        assert result.query_type == "academic"
        print(f"Exploratory (academic): {result.successful_sources} successful sources")


class TestRealSynthesisWorkflow:
    """Integration tests for SYNTHESIS workflow."""

    @pytest.mark.slow
    async def test_synthesis_comparison_query(self, real_client):
        """Test synthesis workflow with comparison query."""
        result = await execute_synthesis(
            real_client,
            "Compare FastAPI vs Flask for REST API development",
            max_sources=5
        )

        assert result.workflow == "synthesis"
        print(f"Synthesis: {result.sources_consulted} sources, {result.successful_sources} successful")
        print(f"Findings: {len(result.findings)}")
        if result.synthesis:
            print(f"Synthesis length: {len(result.synthesis)} chars")
            print(f"Synthesis preview: {result.synthesis[:200]}...")

    @pytest.mark.slow
    async def test_synthesis_best_practices_query(self, real_client):
        """Test synthesis workflow with best practices query."""
        result = await execute_synthesis(
            real_client,
            "What are the best practices for microservices authentication?",
            max_sources=5
        )

        assert result.workflow == "synthesis"
        assert result.synthesis is not None or result.successful_sources > 0
        print(f"Best practices synthesis completed")


class TestRealEndToEnd:
    """End-to-end integration tests."""

    @pytest.mark.slow
    async def test_full_research_with_report(self, real_client):
        """Test full research workflow with report generation."""
        # Execute synthesis workflow
        result = await execute_synthesis(
            real_client,
            "Compare Python type hints vs TypeScript types",
            max_sources=5
        )

        # Generate reports
        report = generate_report(
            query="Compare Python type hints vs TypeScript types",
            result=result,
            duration_seconds=60.0,
            actor_fee=0.30
        )

        markdown = generate_markdown_report(
            query="Compare Python type hints vs TypeScript types",
            result=result,
            duration_seconds=60.0,
            actor_fee=0.30
        )

        # Validate report
        assert report["query"] == "Compare Python type hints vs TypeScript types"
        assert report["workflow"] == "synthesis"
        assert report["actor_fee"] == 0.30
        assert "timestamp" in report

        # Validate markdown
        assert "# Deep Research Report" in markdown
        assert "## Metadata" in markdown

        print(f"Report generated successfully")
        print(f"Markdown length: {len(markdown)} chars")


class TestAPIErrorRecovery:
    """Tests for API error recovery."""

    @pytest.mark.slow
    async def test_workflow_continues_on_partial_failure(self, real_client):
        """Workflow should continue even if some APIs fail."""
        # Use a complex query that exercises multiple sources
        result = await execute_synthesis(
            real_client,
            "Compare different approaches to building RAG applications",
            max_sources=5
        )

        # Even with potential failures, should have some results
        assert result.sources_consulted > 0
        print(f"Sources tried: {result.sources_consulted}, Successful: {result.successful_sources}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])
