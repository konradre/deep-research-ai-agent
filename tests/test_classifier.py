"""Unit tests for query classification."""

import pytest
import sys
import os

# Add actor directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.classifier import (
    classify_query,
    classify_query_type,
    get_workflow_description,
    get_query_type_description,
)


class TestWorkflowClassification:
    """Tests for workflow type classification."""

    # SYNTHESIS queries - comparison, best practices
    @pytest.mark.parametrize("query", [
        "Compare FastAPI vs Flask",
        "FastAPI versus Django for REST APIs",
        "What are the best practices for microservices",
        "Which is better: React or Vue",
        "Pros and cons of serverless architecture",
        "What are the tradeoffs between SQL and NoSQL",
        "Differences between REST and GraphQL",
        "What are the advantages and disadvantages of TypeScript",
        "Strengths and weaknesses of different testing frameworks",
        "Which should I use for authentication: JWT or sessions",
        "What is the recommended approach for state management",
    ])
    def test_synthesis_classification(self, query):
        """Synthesis queries should be classified as synthesis."""
        assert classify_query(query) == "synthesis"

    # DIRECT queries - specific technical lookups
    @pytest.mark.parametrize("query", [
        "How does React useEffect work",
        "Explain Python async await",
        "Documentation for FastAPI WebSockets",
        "What is the asyncio API",
        "Syntax of TypeScript generics",
        "Example of Python decorator",
        "How to use React hooks",
        "FastAPI dependency injection",
        "Django REST framework authentication",
        "AWS Lambda configuration",
        "TypeScript API docs",
    ])
    def test_direct_classification(self, query):
        """Direct queries should be classified as direct."""
        assert classify_query(query) == "direct"

    # EXPLORATORY queries - general, unfamiliar topics
    @pytest.mark.parametrize("query", [
        "What is machine learning",
        "How do databases store data",
        "Tell me about cloud computing",
        "What are web frameworks",
        "What is containerization",  # "Explain X" matches DIRECT pattern
        "What is CI/CD",
        "How do APIs work",
        "Latest trends in AI",
    ])
    def test_exploratory_classification(self, query):
        """Exploratory queries should be classified as exploratory."""
        assert classify_query(query) == "exploratory"


class TestQueryTypeClassification:
    """Tests for query content type classification."""

    # ACADEMIC queries
    @pytest.mark.parametrize("query", [
        "Research paper on transformer architecture",
        "Scientific study on neural networks",
        "arXiv papers about LLMs",
        "Academic publication on deep learning",
        "Peer-reviewed study on machine learning",
        "State-of-the-art approaches to NLP",
        "Empirical study on model performance",
        "Benchmark results for language models",
        "Novel approach to attention mechanisms",
        "Large language model training techniques",
    ])
    def test_academic_classification(self, query):
        """Academic queries should route to arXiv."""
        assert classify_query_type(query) == "academic"

    # CODE queries
    @pytest.mark.parametrize("query", [
        "Code example for React hooks",
        "Implementation of binary search",
        "How to implement authentication",
        "Code snippet for API calls",
        "Source code for sorting algorithm",
        "GitHub repository for web scraping",
        "Function to validate email",
        "Class for database connection",
        "Write a function for pagination",
        "Boilerplate for Express app",
        "Working example of WebSocket",
    ])
    def test_code_classification(self, query):
        """Code queries should route to Exa code search."""
        assert classify_query_type(query) == "code"

    # DOCUMENTATION queries
    @pytest.mark.parametrize("query", [
        "FastAPI documentation",
        "React docs for useState",
        "API reference for httpx",
        "Official guide for Django",
        "Method signature for fetch",
        "Parameters for axios request",
        "Return type of async function",
        "Type definition for Response",
        "Configuration options for webpack",
        "Settings for ESLint",
    ])
    def test_documentation_classification(self, query):
        """Documentation queries should route to Ref."""
        assert classify_query_type(query) == "documentation"

    # GENERAL queries
    @pytest.mark.parametrize("query", [
        "What is Python",
        "How do websites work",
        "Latest technology news",
        "Popular programming languages",
        "Web development trends",
        "Software engineering career",
    ])
    def test_general_classification(self, query):
        """General queries should route to Jina web search."""
        assert classify_query_type(query) == "general"


class TestDescriptionHelpers:
    """Tests for description helper functions."""

    def test_workflow_descriptions(self):
        """Workflow descriptions should be correct."""
        assert "authoritative" in get_workflow_description("direct").lower()
        assert "perplexity" in get_workflow_description("exploratory").lower()
        assert "triple" in get_workflow_description("synthesis").lower() or "cross" in get_workflow_description("synthesis").lower()
        assert "unknown" in get_workflow_description("invalid").lower()

    def test_query_type_descriptions(self):
        """Query type descriptions should be correct."""
        assert "documentation" in get_query_type_description("documentation").lower()
        assert "code" in get_query_type_description("code").lower()
        assert "academic" in get_query_type_description("academic").lower() or "research" in get_query_type_description("academic").lower()
        assert "web" in get_query_type_description("general").lower() or "general" in get_query_type_description("general").lower()
        assert "unknown" in get_query_type_description("invalid").lower()


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_query(self):
        """Empty query should default to exploratory/general."""
        assert classify_query("") == "exploratory"
        assert classify_query_type("") == "general"

    def test_case_insensitivity(self):
        """Classification should be case insensitive."""
        assert classify_query("COMPARE FastAPI VS Flask") == "synthesis"
        assert classify_query("compare fastapi vs flask") == "synthesis"
        assert classify_query_type("DOCUMENTATION for React") == "documentation"
        assert classify_query_type("documentation for react") == "documentation"

    def test_mixed_signals(self):
        """Query with multiple signals should use priority order."""
        # Synthesis patterns checked first
        query = "Compare code examples for React documentation"
        assert classify_query(query) == "synthesis"

        # Academic checked first for query type
        query_type = "Research paper with code implementation"
        assert classify_query_type(query_type) == "academic"

    def test_partial_matches(self):
        """Partial word matches should not trigger classification."""
        # "compress" contains "compare" but shouldn't match
        # This tests regex word boundaries
        assert classify_query("compress files in Python") == "exploratory"

    def test_special_characters(self):
        """Queries with special characters should be handled."""
        assert classify_query("FastAPI vs. Flask (2025)") == "synthesis"
        assert classify_query_type("C++ documentation & API reference") == "documentation"
