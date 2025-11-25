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
