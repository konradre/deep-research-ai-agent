"""Unit tests for API clients with HTTP mocking."""

import pytest
import respx
import httpx
import sys
import os

# Add actor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.clients import ResearchClient, APIResult, retry_request


class TestAPIResult:
    """Tests for APIResult dataclass."""

    def test_successful_result(self):
        """Successful result should have correct fields."""
        result = APIResult(
            source="test",
            success=True,
            data={"key": "value"},
            urls_found=["https://example.com"]
        )
        assert result.source == "test"
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.urls_found == ["https://example.com"]
        assert result.error is None

    def test_failed_result(self):
        """Failed result should have error field."""
        result = APIResult(
            source="test",
            success=False,
            error="Connection failed"
        )
        assert result.success is False
        assert result.error == "Connection failed"
        assert result.data is None


class TestRetryRequest:
    """Tests for retry_request helper."""

    async def test_successful_first_attempt(self):
        """Should return result on first successful attempt."""
        call_count = 0

        async def success_func():
            nonlocal call_count
            call_count += 1
            return {"success": True}

        result = await retry_request(success_func)
        assert result == {"success": True}
        assert call_count == 1

    async def test_retry_on_failure(self):
        """Should retry on transient failures."""
        call_count = 0

        async def fail_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.RequestError("Connection failed")
            return {"success": True}

        result = await retry_request(fail_then_succeed, max_retries=2, backoff_base=0.01)
        assert result == {"success": True}
        assert call_count == 2

    async def test_exhausted_retries(self):
        """Should raise after exhausting retries."""
        call_count = 0

        async def always_fail():
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")

        with pytest.raises(httpx.TimeoutException):
            await retry_request(always_fail, max_retries=2, backoff_base=0.01)

        assert call_count == 3  # Initial + 2 retries


class TestResearchClientInit:
    """Tests for ResearchClient initialization."""

    def test_client_initialization(self, mock_api_keys):
        """Client should initialize with all keys."""
        client = ResearchClient(**mock_api_keys)
        assert client.ref_key == "test-ref-key"
        assert client.exa_key == "test-exa-key"
        assert client.jina_key == "test-jina-key"
        assert client.perplexity_key == "test-perplexity-key"

    async def test_client_close(self, mock_api_keys):
        """Client should close HTTP client cleanly."""
        client = ResearchClient(**mock_api_keys)
        await client.close()
        # No exception means success


class TestRefSearch:
    """Tests for Ref API search."""

    @respx.mock
    async def test_successful_search(self, mock_api_keys):
        """Should return results on successful search."""
        respx.post("https://api.ref.dev/v1/search").mock(
            return_value=httpx.Response(200, json={
                "results": [
                    {"title": "Test", "url": "https://example.com", "content": "Test content"}
                ]
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.ref_search("test query")
        await client.close()

        assert result.success is True
        assert result.source == "ref"
        assert len(result.data["results"]) == 1
        assert "https://example.com" in result.urls_found

    @respx.mock
    async def test_http_error(self, mock_api_keys):
        """Should handle HTTP errors gracefully."""
        respx.post("https://api.ref.dev/v1/search").mock(
            return_value=httpx.Response(500)
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.ref_search("test query")
        await client.close()

        assert result.success is False
        assert "500" in result.error

    @respx.mock
    async def test_network_error(self, mock_api_keys):
        """Should handle network errors gracefully."""
        respx.post("https://api.ref.dev/v1/search").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.ref_search("test query")
        await client.close()

        assert result.success is False
        assert result.error is not None


class TestExaSearch:
    """Tests for Exa API search."""

    @respx.mock
    async def test_successful_search(self, mock_api_keys):
        """Should return results on successful search."""
        respx.post("https://api.exa.ai/search").mock(
            return_value=httpx.Response(200, json={
                "results": [
                    {"title": "Code Example", "url": "https://github.com/test", "text": "Example code"}
                ]
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.exa_search("test query")
        await client.close()

        assert result.success is True
        assert result.source == "exa"
        assert "https://github.com/test" in result.urls_found

    @respx.mock
    async def test_code_search(self, mock_api_keys):
        """Should use code-specific domains for code search."""
        route = respx.post("https://api.exa.ai/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        client = ResearchClient(**mock_api_keys)
        await client.exa_code_search("test query")
        await client.close()

        # Check request included code domains
        request_body = route.calls[0].request.content.decode()
        assert "github.com" in request_body
        assert "stackoverflow.com" in request_body

    @respx.mock
    async def test_find_similar(self, mock_api_keys):
        """Should find similar content."""
        respx.post("https://api.exa.ai/findSimilar").mock(
            return_value=httpx.Response(200, json={
                "results": [{"url": "https://similar.com"}]
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.exa_find_similar("https://example.com")
        await client.close()

        assert result.success is True
        assert result.source == "exa_similar"


class TestJinaSearch:
    """Tests for Jina API search."""

    @respx.mock
    async def test_web_search(self, mock_api_keys):
        """Should perform web search."""
        respx.post("https://s.jina.ai/").mock(
            return_value=httpx.Response(200, json={
                "data": [
                    {"title": "Article", "url": "https://news.com/article", "content": "News content"}
                ]
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.jina_search("test query")
        await client.close()

        assert result.success is True
        assert result.source == "jina"
        assert "https://news.com/article" in result.urls_found

    @respx.mock
    async def test_arxiv_search(self, mock_api_keys):
        """Should search arXiv."""
        route = respx.post("https://s.jina.ai/").mock(
            return_value=httpx.Response(200, json={
                "data": [{"url": "https://arxiv.org/abs/2301.00001"}]
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.jina_arxiv_search("transformer models")
        await client.close()

        assert result.success is True
        assert result.source == "jina_arxiv"
        # Check request included site:arxiv.org
        request_body = route.calls[0].request.content.decode()
        assert "arxiv.org" in request_body

    @respx.mock
    async def test_read_url(self, mock_api_keys):
        """Should read URL content."""
        respx.get("https://r.jina.ai/https://example.com").mock(
            return_value=httpx.Response(200, json={
                "content": "Page content here",
                "title": "Example Page"
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.jina_read_url("https://example.com")
        await client.close()

        assert result.success is True
        assert result.source == "jina_read"
        assert result.data["content"] == "Page content here"

    @respx.mock
    async def test_read_urls_parallel(self, mock_api_keys):
        """Should read multiple URLs in parallel."""
        respx.get(url__regex=r"https://r\.jina\.ai/.*").mock(
            return_value=httpx.Response(200, json={"content": "Content"})
        )

        client = ResearchClient(**mock_api_keys)
        results = await client.jina_read_urls([
            "https://example.com/1",
            "https://example.com/2",
            "https://example.com/3"
        ])
        await client.close()

        assert len(results) == 3
        assert all(r.success for r in results)


class TestPerplexitySearch:
    """Tests for Perplexity API."""

    @respx.mock
    async def test_search(self, mock_api_keys):
        """Should perform Perplexity search."""
        respx.post("https://api.perplexity.ai/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [
                    {"message": {"content": "Research findings..."}}
                ],
                "citations": ["https://source1.com", "https://source2.com"]
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.perplexity_search("test query")
        await client.close()

        assert result.success is True
        assert result.source == "perplexity"
        assert len(result.urls_found) == 2

    @respx.mock
    async def test_synthesize(self, mock_api_keys):
        """Should synthesize research findings."""
        route = respx.post("https://api.perplexity.ai/chat/completions").mock(
            return_value=httpx.Response(200, json={
                "choices": [
                    {"message": {"content": "Synthesis: Key findings..."}}
                ]
            })
        )

        client = ResearchClient(**mock_api_keys)
        result = await client.perplexity_synthesize(
            query="compare X vs Y",
            context="Finding 1: ... Finding 2: ..."
        )
        await client.close()

        assert result.success is True
        assert result.source == "perplexity_synthesis"
        # Check using sonar-pro model
        request_body = route.calls[0].request.content.decode()
        assert "sonar-pro" in request_body


class TestRetryBehavior:
    """Tests for retry behavior in API calls."""

    @respx.mock
    async def test_exa_search_retries(self, mock_api_keys):
        """Exa search should retry on failure."""
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return httpx.Response(503)
            return httpx.Response(200, json={"results": []})

        respx.post("https://api.exa.ai/search").mock(side_effect=side_effect)

        client = ResearchClient(**mock_api_keys)
        result = await client.exa_search("test")
        await client.close()

        assert result.success is True
        assert call_count >= 2

    @respx.mock
    async def test_jina_search_retries(self, mock_api_keys):
        """Jina search should retry on timeout."""
        call_count = 0

        def side_effect(request):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Timeout")
            return httpx.Response(200, json={"data": []})

        respx.post("https://s.jina.ai/").mock(side_effect=side_effect)

        client = ResearchClient(**mock_api_keys)
        result = await client.jina_search("test")
        await client.close()

        assert result.success is True
        assert call_count >= 2
