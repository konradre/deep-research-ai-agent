"""Report generation for research results."""

from datetime import datetime, timezone
from typing import Any

from .workflows import WorkflowResult
from .classifier import get_workflow_description, get_query_type_description


def generate_report(
    query: str,
    result: WorkflowResult,
    duration_seconds: float,
    actor_fee: float
) -> dict[str, Any]:
    """
    Generate a structured research report.

    Returns a dictionary suitable for Apify dataset storage.
    """
    # Extract key findings summary
    findings_summary = _extract_summary(result)

    # Extract structured source content for RAG/downstream use
    source_content = _extract_source_content(result.findings)

    return {
        "query": query,
        "workflow": result.workflow,
        "workflow_description": get_workflow_description(result.workflow),
        "query_type": result.query_type,
        "query_type_description": get_query_type_description(result.query_type),
        "duration_seconds": round(duration_seconds, 2),
        "source_count": result.sources_consulted,
        "successful_sources": result.successful_sources,
        "findings_summary": findings_summary,
        "synthesis": result.synthesis,
        "source_content": source_content,
        "urls_discovered": result.urls_discovered,
        "actor_fee": actor_fee,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "success": result.success,
        "error": result.error
    }


def generate_markdown_report(
    query: str,
    result: WorkflowResult,
    duration_seconds: float,
    actor_fee: float
) -> str:
    """
    Generate a human-readable markdown report.
    """
    lines = [
        "# Deep Research Report",
        "",
        f"**Query:** {query}",
        "",
        "## Metadata",
        "",
        f"- **Workflow:** {result.workflow} ({get_workflow_description(result.workflow)})",
        f"- **Query Type:** {result.query_type} ({get_query_type_description(result.query_type)})",
        f"- **Duration:** {duration_seconds:.1f} seconds",
        f"- **Sources Consulted:** {result.sources_consulted}",
        f"- **Successful Sources:** {result.successful_sources}",
        f"- **Actor Fee:** ${actor_fee:.2f}",
        f"- **Timestamp:** {datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')}",
        "",
    ]

    # Add synthesis if available
    if result.synthesis:
        lines.extend([
            "## Synthesis",
            "",
            result.synthesis,
            "",
        ])

    # Add findings summary
    lines.extend([
        "## Key Findings",
        "",
    ])

    for i, finding in enumerate(result.findings, 1):
        source = finding.get("source", "unknown")
        ftype = finding.get("type", "unknown")
        lines.append(f"### Source {i}: {source} ({ftype})")
        lines.append("")

        data = finding.get("data", {})
        summary = _summarize_finding(source, data)
        lines.append(summary)
        lines.append("")

    # Add discovered URLs
    if result.urls_discovered:
        lines.extend([
            "## Sources Consulted",
            "",
        ])
        for url in result.urls_discovered:
            lines.append(f"- {url}")
        lines.append("")

    return "\n".join(lines)


def _extract_summary(result: WorkflowResult) -> str:
    """Extract a brief summary from findings."""
    summaries = []

    # Prioritize synthesis
    if result.synthesis:
        # Take first paragraph or 500 chars
        synth = result.synthesis.split("\n\n")[0]
        return synth[:500] + "..." if len(synth) > 500 else synth

    # Otherwise summarize from findings
    for finding in result.findings[:3]:
        source = finding.get("source", "unknown")
        data = finding.get("data", {})
        summary = _summarize_finding(source, data, max_length=200)
        if summary and summary != "No content extracted.":
            summaries.append(f"[{source}] {summary}")

    return " | ".join(summaries) if summaries else "No findings extracted."


def _extract_source_content(findings: list[dict]) -> list[dict[str, Any]]:
    """
    Extract structured content from findings for RAG/downstream use.

    Returns array of source objects with:
    - source: API source name
    - type: content type (overview, documentation, code, url_content, etc.)
    - url: source URL if available
    - title: content title if available
    - content: full extracted text content
    - relevance: high/medium/low based on source type
    """
    sources = []

    for finding in findings:
        source_name = finding.get("source", "unknown")
        source_type = finding.get("type", "unknown")
        data = finding.get("data", {})
        url = finding.get("url", "")

        if source_name == "perplexity":
            # Perplexity overview - high relevance, LLM-synthesized
            choices = data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                if content:
                    sources.append({
                        "source": source_name,
                        "type": "overview",
                        "url": None,
                        "title": "AI-Generated Overview",
                        "content": content,
                        "relevance": "high"
                    })

        elif source_name == "jina_read":
            # Deep URL content - high relevance, fills knowledge gaps
            content = data.get("content", data.get("text", ""))
            title = data.get("title", "")
            if content:
                sources.append({
                    "source": source_name,
                    "type": "url_content",
                    "url": url or data.get("url", ""),
                    "title": title,
                    "content": content[:8000],  # Cap at 8K chars per source
                    "relevance": "high"
                })

        elif source_name in ("ref", "exa", "exa_code", "jina", "jina_arxiv"):
            # Search results - medium relevance, multiple items
            results = data.get("results", data.get("data", []))
            if isinstance(results, list):
                for r in results[:5]:  # Top 5 results per source
                    text = r.get("text", r.get("content", r.get("description", "")))
                    title = r.get("title", "")
                    result_url = r.get("url", r.get("link", ""))

                    if text:
                        relevance = "high" if source_name in ("exa_code", "jina_arxiv") else "medium"
                        sources.append({
                            "source": source_name,
                            "type": source_type,
                            "url": result_url,
                            "title": title,
                            "content": text[:4000],  # Cap at 4K chars per result
                            "relevance": relevance
                        })

    return sources


def _summarize_finding(source: str, data: dict, max_length: int = 500) -> str:
    """Summarize a single finding based on source type."""
    if source == "perplexity":
        choices = data.get("choices", [])
        if choices:
            content = choices[0].get("message", {}).get("content", "")
            if content:
                return content[:max_length] + "..." if len(content) > max_length else content

    elif source in ("ref", "exa", "jina", "jina_search"):
        results = data.get("results", data.get("data", []))
        if isinstance(results, list) and results:
            parts = []
            for r in results[:3]:
                title = r.get("title", "")
                text = r.get("text", r.get("content", r.get("description", "")))
                if title:
                    parts.append(f"**{title}**")
                if text:
                    snippet = text[:150] + "..." if len(text) > 150 else text
                    parts.append(snippet)
            return "\n\n".join(parts) if parts else "Results found but no text content."

    elif source == "jina_read":
        content = data.get("content", data.get("text", ""))
        if content:
            return content[:max_length] + "..." if len(content) > max_length else content

    return "No content extracted."
