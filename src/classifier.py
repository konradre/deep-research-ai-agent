"""Query classification for workflow and source type selection."""

import re
from typing import Literal

WorkflowType = Literal["direct", "exploratory", "synthesis"]
QueryType = Literal["documentation", "code", "academic", "general"]

# Patterns indicating SYNTHESIS workflow (check first - highest specificity)
SYNTHESIS_PATTERNS = [
    r"\bcompare\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bbest practices\b",
    r"\brecommended\b",
    r"\bwhich is better\b",
    r"\bwhich should\b",
    r"\bpros and cons\b",
    r"\btrade-?offs?\b",
    r"\bdifferences? between\b",
    r"\badvantages?\b.*\bdisadvantages?\b",
    r"\bstrengths?\b.*\bweaknesses?\b",
]

# Patterns indicating DIRECT workflow (specific technical queries)
DIRECT_PATTERNS = [
    r"\bhow does [\w\s]+ work\b",
    r"\bexplain [\w\s]+\b",
    r"\bwhat is the [\w\s]+ (api|function|method|class)\b",
    r"\bdocumentation for\b",
    r"\bsyntax of\b",
    r"\bexample of\b",
    r"\bhow to use\b",
    # Specific technology names (likely have official docs)
    r"\b(asyncio|react|vue|angular|django|fastapi|flask|express|nextjs|nuxt)\b",
    r"\b(typescript|python|javascript|rust|go|java)\s+(api|docs|documentation)\b",
    r"\b(aws|azure|gcp|firebase|supabase)\s+\w+\b",
]

# Patterns indicating ACADEMIC query type (arXiv, papers)
ACADEMIC_PATTERNS = [
    r"\bresearch\s+paper\b",
    r"\bscientific\s+study\b",
    r"\bacademic\b",
    r"\barxiv\b",
    r"\bpublication\b",
    r"\bjournal\b",
    r"\bpeer[\s-]?review(ed)?\b",
    r"\bstate[\s-]?of[\s-]?the[\s-]?art\b",
    r"\bnovel\s+approach\b",
    r"\btheoretical\b",
    r"\bempirical\s+(study|analysis|evidence)\b",
    r"\bbenchmark\s+results\b",
    r"\bexperimental\s+results\b",
    r"\bmachine\s+learning\s+(model|algorithm|approach)\b",
    r"\bdeep\s+learning\b",
    r"\bneural\s+network\b",
    r"\btransformer\s+(model|architecture)\b",
    r"\blarge\s+language\s+model\b",
    r"\bLLM\b",
]

# Patterns indicating CODE query type
CODE_PATTERNS = [
    r"\bcode\s+example\b",
    r"\bimplementation\b",
    r"\bhow\s+to\s+implement\b",
    r"\bcode\s+snippet\b",
    r"\bsource\s+code\b",
    r"\bgithub\b",
    r"\brepository\b",
    r"\bfunction\s+to\b",
    r"\bclass\s+for\b",
    r"\bwrite\s+(a\s+)?(code|function|class|script)\b",
    r"\bboilerplate\b",
    r"\bstarter\s+(template|code)\b",
    r"\bworking\s+example\b",
]

# Patterns indicating DOCUMENTATION query type
DOCUMENTATION_PATTERNS = [
    r"\bdocumentation\b",
    r"\bdocs\b",
    r"\bapi\s+reference\b",
    r"\bofficial\s+(docs|guide)\b",
    r"\bmethod\s+signature\b",
    r"\bparameters?\s+(for|of)\b",
    r"\breturn\s+type\b",
    r"\btype\s+definition\b",
    r"\bconfiguration\s+options?\b",
    r"\bsettings?\s+for\b",
]


def classify_query(query: str) -> WorkflowType:
    """
    Classify a research query into the appropriate workflow type.

    Returns:
        - 'direct': Single authoritative source (30-60s)
        - 'exploratory': Perplexity-guided deep dive (1-2min)
        - 'synthesis': Triple Stack + cross-validation (3-5min)
    """
    query_lower = query.lower()

    # Check SYNTHESIS first (comparison/consensus queries)
    for pattern in SYNTHESIS_PATTERNS:
        if re.search(pattern, query_lower):
            return "synthesis"

    # Check DIRECT (specific technical queries with likely authoritative source)
    for pattern in DIRECT_PATTERNS:
        if re.search(pattern, query_lower):
            return "direct"

    # Default to EXPLORATORY (general questions, unfamiliar topics, cold start)
    return "exploratory"


def classify_query_type(query: str) -> QueryType:
    """
    Classify a query into content type for source routing.

    Returns:
        - 'documentation': API docs, official references → Ref primary
        - 'code': Code examples, implementations → Exa code search primary
        - 'academic': Research papers, studies → Jina arXiv primary
        - 'general': General web content → Jina web search
    """
    query_lower = query.lower()

    # Check ACADEMIC first (most specific)
    for pattern in ACADEMIC_PATTERNS:
        if re.search(pattern, query_lower):
            return "academic"

    # Check CODE
    for pattern in CODE_PATTERNS:
        if re.search(pattern, query_lower):
            return "code"

    # Check DOCUMENTATION
    for pattern in DOCUMENTATION_PATTERNS:
        if re.search(pattern, query_lower):
            return "documentation"

    # Default to GENERAL
    return "general"


def get_workflow_description(workflow: WorkflowType) -> str:
    """Get human-readable description of a workflow."""
    descriptions = {
        "direct": "Single authoritative source lookup",
        "exploratory": "Perplexity-guided deep dive with URL analysis",
        "synthesis": "Triple Stack cross-validation with synthesis",
    }
    return descriptions.get(workflow, "Unknown workflow")


def get_query_type_description(query_type: QueryType) -> str:
    """Get human-readable description of a query type."""
    descriptions = {
        "documentation": "Official documentation and API references",
        "code": "Code examples and implementations",
        "academic": "Research papers and academic literature",
        "general": "General web content and articles",
    }
    return descriptions.get(query_type, "Unknown query type")
