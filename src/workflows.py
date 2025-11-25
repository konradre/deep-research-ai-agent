"""Research workflow executors for each workflow type."""

import asyncio
from dataclasses import dataclass, field
from typing import Any

from .clients import ResearchClient, APIResult
from .classifier import classify_query_type, QueryType


@dataclass
class WorkflowResult:
    """Result from a workflow execution."""
    workflow: str
    success: bool
    query_type: str = "general"
    sources_consulted: int = 0
    successful_sources: int = 0
    findings: list[dict[str, Any]] = field(default_factory=list)
    synthesis: str | None = None
    urls_discovered: list[str] = field(default_factory=list)
    error: str | None = None


async def execute_direct(client: ResearchClient, query: str) -> WorkflowResult:
    """
    DIRECT workflow: Single authoritative source lookup.

    Best for: Specific technical queries with likely authoritative source.
    Duration: 30-60 seconds
    Cost: Lowest

    Strategy: Route to best source based on query type:
    - documentation → Ref primary
    - code → Exa code search primary
    - academic → Jina arXiv primary
    - general → Jina web + Exa fallback
    """
    findings = []
    urls = []
    sources_tried = 0
    successful = 0

    # Classify query type for source routing
    query_type = classify_query_type(query)

    if query_type == "documentation":
        # Primary: Ref (official docs)
        sources_tried += 1
        ref_result = await client.ref_search(query)
        if ref_result.success and ref_result.data:
            successful += 1
            findings.append({
                "source": "ref",
                "type": "documentation",
                "data": ref_result.data
            })
            if ref_result.urls_found:
                urls.extend(ref_result.urls_found)

        # Fallback: Exa if Ref insufficient
        if not findings or len(urls) < 3:
            sources_tried += 1
            exa_result = await client.exa_search(query, num_results=5)
            if exa_result.success and exa_result.data:
                successful += 1
                findings.append({
                    "source": "exa",
                    "type": "semantic_search",
                    "data": exa_result.data
                })
                if exa_result.urls_found:
                    urls.extend(exa_result.urls_found)

    elif query_type == "code":
        # Primary: Exa code search
        sources_tried += 1
        exa_result = await client.exa_code_search(query, num_results=10)
        if exa_result.success and exa_result.data:
            successful += 1
            findings.append({
                "source": "exa_code",
                "type": "code_examples",
                "data": exa_result.data
            })
            if exa_result.urls_found:
                urls.extend(exa_result.urls_found)

        # Secondary: Regular Exa for broader results
        if len(urls) < 5:
            sources_tried += 1
            exa_general = await client.exa_search(query, num_results=5)
            if exa_general.success and exa_general.data:
                successful += 1
                findings.append({
                    "source": "exa",
                    "type": "semantic_search",
                    "data": exa_general.data
                })
                if exa_general.urls_found:
                    urls.extend(exa_general.urls_found)

    elif query_type == "academic":
        # Primary: Jina arXiv search
        sources_tried += 1
        arxiv_result = await client.jina_arxiv_search(query, num_results=10)
        if arxiv_result.success and arxiv_result.data:
            successful += 1
            findings.append({
                "source": "jina_arxiv",
                "type": "academic_papers",
                "data": arxiv_result.data
            })
            if arxiv_result.urls_found:
                urls.extend(arxiv_result.urls_found)

        # Secondary: General Jina for related content
        if len(urls) < 5:
            sources_tried += 1
            jina_result = await client.jina_search(query, num_results=5)
            if jina_result.success and jina_result.data:
                successful += 1
                findings.append({
                    "source": "jina",
                    "type": "web_search",
                    "data": jina_result.data
                })
                if jina_result.urls_found:
                    urls.extend(jina_result.urls_found)

    else:  # general
        # Primary: Jina web search
        sources_tried += 1
        jina_result = await client.jina_search(query, num_results=10)
        if jina_result.success and jina_result.data:
            successful += 1
            findings.append({
                "source": "jina",
                "type": "web_search",
                "data": jina_result.data
            })
            if jina_result.urls_found:
                urls.extend(jina_result.urls_found)

        # Fallback: Exa for semantic enrichment
        if len(urls) < 5:
            sources_tried += 1
            exa_result = await client.exa_search(query, num_results=5)
            if exa_result.success and exa_result.data:
                successful += 1
                findings.append({
                    "source": "exa",
                    "type": "semantic_search",
                    "data": exa_result.data
                })
                if exa_result.urls_found:
                    urls.extend(exa_result.urls_found)

    return WorkflowResult(
        workflow="direct",
        query_type=query_type,
        success=bool(findings),
        sources_consulted=sources_tried,
        successful_sources=successful,
        findings=findings,
        urls_discovered=list(set(urls))
    )


async def execute_exploratory(
    client: ResearchClient,
    query: str,
    max_urls: int = 5
) -> WorkflowResult:
    """
    EXPLORATORY workflow: Perplexity-guided deep dive with URL analysis.

    Best for: Unfamiliar topics, general concepts, emerging technology.
    Duration: 1-2 minutes
    Cost: Medium

    Strategy:
    1. Perplexity search for overview + citations
    2. Query-type-aware secondary search (arXiv for academic, code search for code, etc.)
    3. Deep read selected URLs with Jina
    """
    findings = []
    urls = []
    sources_tried = 0
    successful = 0

    # Classify query type for source routing
    query_type = classify_query_type(query)

    # Step 1: Perplexity for overview and URL discovery
    sources_tried += 1
    pplx_result = await client.perplexity_search(query)

    if pplx_result.success and pplx_result.data:
        successful += 1
        findings.append({
            "source": "perplexity",
            "type": "overview",
            "data": pplx_result.data
        })
        if pplx_result.urls_found:
            urls.extend(pplx_result.urls_found)

    # Step 2: Query-type-aware secondary search
    sources_tried += 1
    if query_type == "academic":
        secondary_result = await client.jina_arxiv_search(query, num_results=max_urls)
        secondary_type = "academic_papers"
    elif query_type == "code":
        secondary_result = await client.exa_code_search(query, num_results=max_urls)
        secondary_type = "code_examples"
    elif query_type == "documentation":
        secondary_result = await client.ref_search(query)
        secondary_type = "documentation"
    else:
        secondary_result = await client.jina_search(query, num_results=max_urls)
        secondary_type = "web_search"

    if secondary_result.success and secondary_result.data:
        successful += 1
        findings.append({
            "source": secondary_result.source,
            "type": secondary_type,
            "data": secondary_result.data
        })
        if secondary_result.urls_found:
            urls.extend(secondary_result.urls_found)

    # Step 3: Deep read top URLs (deduplicated, max 5)
    unique_urls = list(dict.fromkeys(urls))[:max_urls]

    if unique_urls:
        sources_tried += len(unique_urls)
        read_results = await client.jina_read_urls(unique_urls)

        for i, result in enumerate(read_results):
            if result.success and result.data:
                successful += 1
                findings.append({
                    "source": "jina_read",
                    "type": "url_content",
                    "url": unique_urls[i] if i < len(unique_urls) else "unknown",
                    "data": result.data
                })

    # Step 4: Synthesize findings for polished output
    synthesis_text = None
    if findings:
        context_parts = []
        for f in findings:
            source = f.get("source", "unknown")
            data = f.get("data", {})

            if source == "perplexity":
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    context_parts.append(f"[Perplexity Overview] {content[:2000]}")
            elif source in ("ref", "exa", "exa_code", "jina", "jina_arxiv"):
                results = data.get("results", data.get("data", []))
                if isinstance(results, list):
                    for r in results[:3]:
                        text = r.get("text", r.get("content", r.get("description", "")))
                        if text:
                            context_parts.append(f"[{source}] {text[:800]}")
            elif source == "jina_read":
                content = data.get("content", data.get("text", ""))
                if content:
                    url = f.get("url", "")
                    context_parts.append(f"[URL: {url}] {content[:1200]}")

        if context_parts:
            context = "\n\n---\n\n".join(context_parts)

            sources_tried += 1
            synth_result = await client.perplexity_synthesize(query, context)

            if synth_result.success and synth_result.data:
                successful += 1
                choices = synth_result.data.get("choices", [])
                if choices:
                    synthesis_text = choices[0].get("message", {}).get("content", "")

    return WorkflowResult(
        workflow="exploratory",
        query_type=query_type,
        success=bool(findings),
        sources_consulted=sources_tried,
        successful_sources=successful,
        findings=findings,
        synthesis=synthesis_text,
        urls_discovered=unique_urls
    )


async def execute_synthesis(
    client: ResearchClient,
    query: str,
    max_sources: int = 10
) -> WorkflowResult:
    """
    SYNTHESIS workflow: Triple Stack cross-validation with synthesis.

    Best for: Comparisons, best practices, consensus-seeking queries.
    Duration: 3-5 minutes
    Cost: Highest

    Strategy:
    1. Query-type-aware Triple Stack in parallel:
       - academic: arXiv + Ref + Exa
       - code: Exa code + Exa general + Jina
       - documentation: Ref + Exa + Jina
       - general: Ref + Exa + Jina
    2. Collect and deduplicate URLs
    3. Deep read top URLs
    4. Perplexity synthesis of all findings
    """
    findings = []
    urls = []
    sources_tried = 0
    successful = 0

    # Classify query type for source routing
    query_type = classify_query_type(query)

    # Step 1: Query-type-aware Triple Stack - parallel execution
    sources_tried += 3

    if query_type == "academic":
        # Academic: arXiv + Ref + Exa
        task1 = client.jina_arxiv_search(query, num_results=max_sources)
        task2 = client.ref_search(query)
        task3 = client.exa_search(query, num_results=max_sources)
        types = ["academic_papers", "documentation", "semantic_search"]
    elif query_type == "code":
        # Code: Exa code + Exa general + Jina
        task1 = client.exa_code_search(query, num_results=max_sources)
        task2 = client.exa_search(query, num_results=max_sources)
        task3 = client.jina_search(query, num_results=max_sources)
        types = ["code_examples", "semantic_search", "web_search"]
    else:
        # documentation or general: Ref + Exa + Jina
        task1 = client.ref_search(query)
        task2 = client.exa_search(query, num_results=max_sources)
        task3 = client.jina_search(query, num_results=max_sources)
        types = ["documentation", "semantic_search", "web_search"]

    result1, result2, result3 = await asyncio.gather(
        task1, task2, task3,
        return_exceptions=True
    )

    # Process results
    for result, result_type in zip([result1, result2, result3], types):
        if isinstance(result, APIResult) and result.success:
            successful += 1
            findings.append({
                "source": result.source,
                "type": result_type,
                "data": result.data
            })
            if result.urls_found:
                urls.extend(result.urls_found)

    # Step 2: Deep read top URLs
    unique_urls = list(dict.fromkeys(urls))[:7]  # Max 7 parallel reads

    if unique_urls:
        sources_tried += len(unique_urls)
        read_results = await client.jina_read_urls(unique_urls)

        for i, result in enumerate(read_results):
            if result.success and result.data:
                successful += 1
                findings.append({
                    "source": "jina_read",
                    "type": "url_content",
                    "url": unique_urls[i] if i < len(unique_urls) else "unknown",
                    "data": result.data
                })

    # Step 3: Synthesize all findings with Perplexity
    synthesis_text = None
    if findings:
        # Prepare context for synthesis
        context_parts = []
        for f in findings:
            source = f.get("source", "unknown")
            data = f.get("data", {})

            # Extract text content based on source type
            if source == "perplexity":
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    context_parts.append(f"[Perplexity] {content[:2000]}")
            elif source in ("ref", "exa", "exa_code", "jina", "jina_arxiv"):
                results = data.get("results", data.get("data", []))
                if isinstance(results, list):
                    for r in results[:3]:
                        text = r.get("text", r.get("content", r.get("description", "")))
                        if text:
                            context_parts.append(f"[{source}] {text[:1000]}")
            elif source == "jina_read":
                content = data.get("content", data.get("text", ""))
                if content:
                    url = f.get("url", "")
                    context_parts.append(f"[URL: {url}] {content[:1500]}")

        context = "\n\n---\n\n".join(context_parts)

        sources_tried += 1
        synth_result = await client.perplexity_synthesize(query, context)

        if synth_result.success and synth_result.data:
            successful += 1
            choices = synth_result.data.get("choices", [])
            if choices:
                synthesis_text = choices[0].get("message", {}).get("content", "")

    return WorkflowResult(
        workflow="synthesis",
        query_type=query_type,
        success=bool(findings),
        sources_consulted=sources_tried,
        successful_sources=successful,
        findings=findings,
        synthesis=synthesis_text,
        urls_discovered=unique_urls
    )
