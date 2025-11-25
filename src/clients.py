"""API clients for research services (BYOK model)."""

import httpx
import asyncio
from typing import Any
from dataclasses import dataclass


@dataclass
class APIResult:
    """Standardized result from any API call."""
    source: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None
    urls_found: list[str] | None = None


async def retry_request(
    func,
    max_retries: int = 2,
    backoff_base: float = 1.0
) -> Any:
    """
    Retry a request with exponential backoff.

    Learning #39: Fallback systems provide silent resilience.
    """
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            return await func()
        except (httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException) as e:
            last_error = e
            if attempt < max_retries:
                wait_time = backoff_base * (2 ** attempt)
                await asyncio.sleep(wait_time)
            continue
    raise last_error


class ResearchClient:
    """
    Unified client for all research APIs.

    BYOK (Bring Your Own Key) model - user provides all API keys.
    """

    def __init__(
        self,
        ref_key: str,
        exa_key: str,
        jina_key: str,
        perplexity_key: str,
        timeout: float = 60.0
    ):
        self.ref_key = ref_key
        self.exa_key = exa_key
        self.jina_key = jina_key
        self.perplexity_key = perplexity_key
        self.http = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.http.aclose()

    # ========== REF API ==========

    async def ref_search(self, query: str) -> APIResult:
        """
        Search documentation via Ref API.
        Best for: Official docs, API references, library documentation.
        """
        async def make_request():
            response = await self.http.post(
                "https://api.ref.dev/v1/search",
                headers={
                    "Authorization": f"Bearer {self.ref_key}",
                    "Content-Type": "application/json"
                },
                json={"query": query, "limit": 10}
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(
                source="ref",
                success=True,
                data=data,
                urls_found=[r.get("url") for r in data.get("results", []) if r.get("url")]
            )
        except httpx.HTTPStatusError as e:
            return APIResult(source="ref", success=False, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResult(source="ref", success=False, error=str(e))

    # ========== EXA API ==========

    async def exa_search(self, query: str, num_results: int = 10) -> APIResult:
        """
        Semantic/code search via Exa API.
        Best for: Code examples, implementation patterns, technical blogs.
        """
        async def make_request():
            response = await self.http.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": self.exa_key,
                    "Content-Type": "application/json"
                },
                json={
                    "query": f"{query} 2025",
                    "numResults": num_results,
                    "type": "auto",
                    "contents": {
                        "text": {"maxCharacters": 3000}
                    }
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(
                source="exa",
                success=True,
                data=data,
                urls_found=[r.get("url") for r in data.get("results", []) if r.get("url")]
            )
        except httpx.HTTPStatusError as e:
            return APIResult(source="exa", success=False, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResult(source="exa", success=False, error=str(e))

    async def exa_find_similar(self, url: str, num_results: int = 5) -> APIResult:
        """Find similar content to a given URL."""
        async def make_request():
            response = await self.http.post(
                "https://api.exa.ai/findSimilar",
                headers={
                    "x-api-key": self.exa_key,
                    "Content-Type": "application/json"
                },
                json={
                    "url": url,
                    "numResults": num_results,
                    "contents": {"text": {"maxCharacters": 2000}}
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(source="exa_similar", success=True, data=data)
        except Exception as e:
            return APIResult(source="exa_similar", success=False, error=str(e))

    async def exa_code_search(self, query: str, num_results: int = 10) -> APIResult:
        """
        Code-focused search via Exa API.
        Best for: Code examples, implementation patterns, GitHub repos.
        """
        async def make_request():
            response = await self.http.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": self.exa_key,
                    "Content-Type": "application/json"
                },
                json={
                    "query": f"{query} code example implementation",
                    "numResults": num_results,
                    "type": "auto",
                    "includeDomains": [
                        "github.com",
                        "stackoverflow.com",
                        "dev.to",
                        "medium.com",
                        "hashnode.dev"
                    ],
                    "contents": {
                        "text": {"maxCharacters": 5000}
                    }
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(
                source="exa_code",
                success=True,
                data=data,
                urls_found=[r.get("url") for r in data.get("results", []) if r.get("url")]
            )
        except httpx.HTTPStatusError as e:
            return APIResult(source="exa_code", success=False, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResult(source="exa_code", success=False, error=str(e))

    # ========== JINA API ==========

    async def jina_search(self, query: str, num_results: int = 10) -> APIResult:
        """
        Web search via Jina API.
        Best for: General web content, news, recent information.
        """
        async def make_request():
            response = await self.http.post(
                "https://s.jina.ai/",
                headers={
                    "Authorization": f"Bearer {self.jina_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "q": f"{query} 2025 latest",
                    "count": num_results
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(
                source="jina",
                success=True,
                data=data,
                urls_found=[r.get("url") for r in data.get("data", []) if r.get("url")]
            )
        except httpx.HTTPStatusError as e:
            return APIResult(source="jina", success=False, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResult(source="jina", success=False, error=str(e))

    async def jina_read_url(self, url: str) -> APIResult:
        """Read a single URL and extract content."""
        async def make_request():
            response = await self.http.get(
                f"https://r.jina.ai/{url}",
                headers={
                    "Authorization": f"Bearer {self.jina_key}",
                    "Accept": "application/json"
                },
                timeout=45.0
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(source="jina_read", success=True, data=data)
        except Exception as e:
            return APIResult(source="jina_read", success=False, error=str(e))

    async def jina_read_urls(self, urls: list[str]) -> list[APIResult]:
        """Read multiple URLs in parallel."""
        import asyncio
        tasks = [self.jina_read_url(url) for url in urls[:7]]  # Max 7 parallel
        return await asyncio.gather(*tasks)

    async def jina_arxiv_search(self, query: str, num_results: int = 10) -> APIResult:
        """
        Search academic papers via Jina arXiv endpoint.
        Best for: Research papers, scientific studies, academic literature.
        """
        async def make_request():
            response = await self.http.post(
                "https://s.jina.ai/",
                headers={
                    "Authorization": f"Bearer {self.jina_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "q": f"site:arxiv.org {query}",
                    "count": num_results
                }
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(
                source="jina_arxiv",
                success=True,
                data=data,
                urls_found=[r.get("url") for r in data.get("data", []) if r.get("url")]
            )
        except httpx.HTTPStatusError as e:
            return APIResult(source="jina_arxiv", success=False, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResult(source="jina_arxiv", success=False, error=str(e))

    # ========== PERPLEXITY API ==========

    async def perplexity_search(self, query: str) -> APIResult:
        """
        Search via Perplexity API.
        Best for: Getting overview with citations, exploratory research.
        """
        async def make_request():
            response = await self.http.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a research assistant. Provide comprehensive, well-cited answers."
                        },
                        {
                            "role": "user",
                            "content": f"{query} (focus on 2024-2025 information)"
                        }
                    ],
                    "search_recency_filter": "month"
                },
                timeout=90.0
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)

            # Extract citations if available
            citations = data.get("citations", [])

            return APIResult(
                source="perplexity",
                success=True,
                data=data,
                urls_found=citations
            )
        except httpx.HTTPStatusError as e:
            return APIResult(source="perplexity", success=False, error=f"HTTP {e.response.status_code}")
        except Exception as e:
            return APIResult(source="perplexity", success=False, error=str(e))

    async def perplexity_synthesize(self, query: str, context: str) -> APIResult:
        """
        Synthesize research findings via Perplexity.
        Used in SYNTHESIS workflow after Triple Stack.
        """
        prompt = f"""Synthesize these research findings into a comprehensive analysis:

RESEARCH QUERY: {query}

COLLECTED FINDINGS:
{context[:12000]}

Provide:
1. **Consensus** - What all sources agree on
2. **Conflicts** - Where sources disagree (with resolution if possible)
3. **Key Insights** - Most important findings
4. **Gaps** - What information is still missing
5. **Conclusion** - Final synthesis with confidence level (high/medium/low)

Be specific and cite which sources support each point."""

        async def make_request():
            response = await self.http.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.perplexity_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are an expert research analyst. Synthesize findings objectively."
                        },
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=120.0
            )
            response.raise_for_status()
            return response.json()

        try:
            data = await retry_request(make_request)
            return APIResult(source="perplexity_synthesis", success=True, data=data)
        except Exception as e:
            return APIResult(source="perplexity_synthesis", success=False, error=str(e))
