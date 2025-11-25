"""Unit tests for report generation."""

import pytest
from datetime import datetime
import sys
import os

# Add actor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.workflows import WorkflowResult
from src.report import (
    generate_report,
    generate_markdown_report,
    _extract_summary,
    _summarize_finding,
)


class TestGenerateReport:
    """Tests for structured report generation."""

    def test_basic_report_structure(self, sample_workflow_result):
        """Report should have all required fields."""
        report = generate_report(
            query="test query",
            result=sample_workflow_result,
            duration_seconds=10.5,
            actor_fee=0.20
        )

        assert report["query"] == "test query"
        assert report["workflow"] == "synthesis"
        assert report["query_type"] == "documentation"
        assert report["duration_seconds"] == 10.5
        assert report["source_count"] == 5
        assert report["successful_sources"] == 4
        assert report["actor_fee"] == 0.20
        assert report["success"] is True
        assert "timestamp" in report
        assert report["timestamp"].endswith("Z")

    def test_report_includes_descriptions(self, sample_workflow_result):
        """Report should include human-readable descriptions."""
        report = generate_report(
            query="test",
            result=sample_workflow_result,
            duration_seconds=5.0,
            actor_fee=0.10
        )

        assert "workflow_description" in report
        assert "query_type_description" in report
        assert len(report["workflow_description"]) > 0
        assert len(report["query_type_description"]) > 0

    def test_report_includes_synthesis(self, sample_workflow_result):
        """Report should include synthesis when available."""
        report = generate_report(
            query="test",
            result=sample_workflow_result,
            duration_seconds=5.0,
            actor_fee=0.30
        )

        assert report["synthesis"] == sample_workflow_result.synthesis

    def test_report_includes_urls(self, sample_workflow_result):
        """Report should include discovered URLs."""
        report = generate_report(
            query="test",
            result=sample_workflow_result,
            duration_seconds=5.0,
            actor_fee=0.20
        )

        assert report["urls_discovered"] == sample_workflow_result.urls_discovered

    def test_report_without_synthesis(self):
        """Report should handle missing synthesis."""
        result = WorkflowResult(
            workflow="direct",
            success=True,
            query_type="general",
            findings=[],
            synthesis=None
        )
        report = generate_report(
            query="test",
            result=result,
            duration_seconds=5.0,
            actor_fee=0.10
        )

        assert report["synthesis"] is None

    def test_report_with_error(self):
        """Report should include error when present."""
        result = WorkflowResult(
            workflow="direct",
            success=False,
            error="API timeout"
        )
        report = generate_report(
            query="test",
            result=result,
            duration_seconds=5.0,
            actor_fee=0.10
        )

        assert report["success"] is False
        assert report["error"] == "API timeout"


class TestGenerateMarkdownReport:
    """Tests for markdown report generation."""

    def test_markdown_header(self, sample_workflow_result):
        """Markdown should have proper header."""
        md = generate_markdown_report(
            query="test query",
            result=sample_workflow_result,
            duration_seconds=10.0,
            actor_fee=0.20
        )

        assert md.startswith("# Deep Research Report")
        assert "**Query:** test query" in md

    def test_markdown_metadata_section(self, sample_workflow_result):
        """Markdown should include metadata section."""
        md = generate_markdown_report(
            query="test",
            result=sample_workflow_result,
            duration_seconds=10.5,
            actor_fee=0.25
        )

        assert "## Metadata" in md
        assert "**Workflow:**" in md
        assert "**Query Type:**" in md
        assert "**Duration:** 10.5 seconds" in md
        assert "**Sources Consulted:** 5" in md
        assert "**Successful Sources:** 4" in md
        assert "**Actor Fee:** $0.25" in md

    def test_markdown_synthesis_section(self, sample_workflow_result):
        """Markdown should include synthesis when available."""
        md = generate_markdown_report(
            query="test",
            result=sample_workflow_result,
            duration_seconds=5.0,
            actor_fee=0.30
        )

        assert "## Synthesis" in md
        assert sample_workflow_result.synthesis in md

    def test_markdown_findings_section(self, sample_workflow_result):
        """Markdown should include key findings."""
        md = generate_markdown_report(
            query="test",
            result=sample_workflow_result,
            duration_seconds=5.0,
            actor_fee=0.20
        )

        assert "## Key Findings" in md
        assert "### Source 1:" in md

    def test_markdown_sources_section(self, sample_workflow_result):
        """Markdown should include consulted sources."""
        md = generate_markdown_report(
            query="test",
            result=sample_workflow_result,
            duration_seconds=5.0,
            actor_fee=0.20
        )

        assert "## Sources Consulted" in md
        for url in sample_workflow_result.urls_discovered:
            assert url in md

    def test_markdown_no_urls(self):
        """Markdown should handle no URLs gracefully."""
        result = WorkflowResult(
            workflow="direct",
            success=True,
            findings=[],
            urls_discovered=[]
        )
        md = generate_markdown_report(
            query="test",
            result=result,
            duration_seconds=5.0,
            actor_fee=0.10
        )

        # Should not have Sources Consulted section
        assert "## Sources Consulted" not in md


class TestExtractSummary:
    """Tests for summary extraction."""

    def test_synthesis_priority(self):
        """Should prioritize synthesis for summary."""
        result = WorkflowResult(
            workflow="synthesis",
            success=True,
            synthesis="This is the main synthesis. It contains key findings.",
            findings=[{"source": "ref", "data": {"results": [{"text": "Other content"}]}}]
        )
        summary = _extract_summary(result)

        assert "synthesis" in summary.lower() or "main" in summary.lower()

    def test_truncates_long_synthesis(self):
        """Should truncate long synthesis."""
        long_synthesis = "A" * 600
        result = WorkflowResult(
            workflow="synthesis",
            success=True,
            synthesis=long_synthesis
        )
        summary = _extract_summary(result)

        assert len(summary) <= 503  # 500 + "..."
        assert summary.endswith("...")

    def test_falls_back_to_findings(self):
        """Should fall back to findings when no synthesis."""
        result = WorkflowResult(
            workflow="direct",
            success=True,
            synthesis=None,
            findings=[
                {
                    "source": "ref",
                    "data": {
                        "results": [{"text": "Finding from ref source"}]
                    }
                }
            ]
        )
        summary = _extract_summary(result)

        assert "[ref]" in summary.lower()

    def test_no_findings(self):
        """Should handle no findings."""
        result = WorkflowResult(
            workflow="direct",
            success=True,
            synthesis=None,
            findings=[]
        )
        summary = _extract_summary(result)

        assert "no findings" in summary.lower()


class TestSummarizeFinding:
    """Tests for individual finding summarization."""

    def test_perplexity_finding(self):
        """Should extract content from Perplexity response."""
        data = {
            "choices": [
                {"message": {"content": "Perplexity analysis content here"}}
            ]
        }
        summary = _summarize_finding("perplexity", data)

        assert "Perplexity analysis content here" in summary

    def test_ref_finding(self):
        """Should extract content from Ref response."""
        data = {
            "results": [
                {"title": "Doc Title", "text": "Documentation content"}
            ]
        }
        summary = _summarize_finding("ref", data)

        assert "Doc Title" in summary or "Documentation content" in summary

    def test_exa_finding(self):
        """Should extract content from Exa response."""
        data = {
            "results": [
                {"title": "Code Example", "text": "function example() {}"}
            ]
        }
        summary = _summarize_finding("exa", data)

        assert "Code Example" in summary or "function" in summary

    def test_jina_finding(self):
        """Should extract content from Jina response."""
        data = {
            "data": [
                {"title": "Web Article", "content": "Article content here"}
            ]
        }
        summary = _summarize_finding("jina", data)

        assert "Web Article" in summary or "Article content" in summary

    def test_jina_read_finding(self):
        """Should extract content from Jina read response."""
        data = {"content": "Full page content extracted from URL"}
        summary = _summarize_finding("jina_read", data)

        assert "Full page content" in summary

    def test_truncates_long_content(self):
        """Should truncate long content."""
        data = {
            "choices": [
                {"message": {"content": "A" * 1000}}
            ]
        }
        summary = _summarize_finding("perplexity", data, max_length=100)

        assert len(summary) <= 103  # 100 + "..."
        assert summary.endswith("...")

    def test_empty_data(self):
        """Should handle empty data gracefully."""
        summary = _summarize_finding("ref", {})
        assert "no content" in summary.lower()

    def test_unknown_source(self):
        """Should handle unknown source type."""
        summary = _summarize_finding("unknown_source", {"data": "test"})
        assert "no content" in summary.lower()


class TestReportEdgeCases:
    """Tests for edge cases in report generation."""

    def test_special_characters_in_query(self):
        """Should handle special characters in query."""
        result = WorkflowResult(workflow="direct", success=True)
        report = generate_report(
            query="Compare React <18> vs Vue (3.0) & Angular",
            result=result,
            duration_seconds=5.0,
            actor_fee=0.10
        )

        assert report["query"] == "Compare React <18> vs Vue (3.0) & Angular"

    def test_unicode_in_findings(self):
        """Should handle unicode in findings."""
        result = WorkflowResult(
            workflow="direct",
            success=True,
            findings=[
                {
                    "source": "ref",
                    "data": {
                        "results": [{"text": "Unicode: \u2022 \u2713 \u2717 \ud83d\ude80"}]
                    }
                }
            ]
        )
        md = generate_markdown_report(
            query="test",
            result=result,
            duration_seconds=5.0,
            actor_fee=0.10
        )

        assert "\u2022" in md or "\u2713" in md

    def test_very_long_findings(self):
        """Should handle very long findings."""
        result = WorkflowResult(
            workflow="synthesis",
            success=True,
            findings=[
                {
                    "source": "perplexity",
                    "data": {
                        "choices": [{"message": {"content": "A" * 10000}}]
                    }
                }
            ] * 10  # 10 findings with long content
        )
        md = generate_markdown_report(
            query="test",
            result=result,
            duration_seconds=5.0,
            actor_fee=0.30
        )

        # Should complete without error
        assert "## Key Findings" in md

    def test_zero_duration(self):
        """Should handle zero duration."""
        result = WorkflowResult(workflow="direct", success=True)
        report = generate_report(
            query="test",
            result=result,
            duration_seconds=0.0,
            actor_fee=0.10
        )

        assert report["duration_seconds"] == 0.0
