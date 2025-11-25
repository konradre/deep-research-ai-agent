"""
Deep Research Agent - Main Entry Point

Professional-grade research with automatic workflow classification.
BYOK model - users provide their own API keys.
"""

import asyncio
import time
from apify import Actor

from .clients import ResearchClient
from .classifier import classify_query, classify_query_type, get_workflow_description, get_query_type_description
from .workflows import execute_direct, execute_exploratory, execute_synthesis
from .report import generate_report, generate_markdown_report


# Pricing per workflow (USD)
WORKFLOW_PRICING = {
    "direct": 0.10,
    "exploratory": 0.20,
    "synthesis": 0.30,
}


async def main() -> None:
    """Main actor entry point."""
    async with Actor:
        # Get input
        actor_input = await Actor.get_input() or {}

        query = actor_input.get("query", "").strip()
        workflow_type = actor_input.get("workflow_type", "auto")
        max_sources = actor_input.get("max_sources", 10)

        # API keys (required)
        ref_key = actor_input.get("ref_api_key", "")
        exa_key = actor_input.get("exa_api_key", "")
        jina_key = actor_input.get("jina_api_key", "")
        perplexity_key = actor_input.get("perplexity_api_key", "")

        # Validate required inputs
        if not query:
            raise ValueError("Query is required")

        missing_keys = []
        if not ref_key:
            missing_keys.append("ref_api_key")
        if not exa_key:
            missing_keys.append("exa_api_key")
        if not jina_key:
            missing_keys.append("jina_api_key")
        if not perplexity_key:
            missing_keys.append("perplexity_api_key")

        if missing_keys:
            raise ValueError(f"Missing required API keys: {', '.join(missing_keys)}")

        # Determine workflow
        if workflow_type == "auto":
            workflow = classify_query(query)
            Actor.log.info(f"Auto-classified query as: {workflow}")
        else:
            workflow = workflow_type
            Actor.log.info(f"Using manual workflow selection: {workflow}")

        # Also classify query type for logging
        query_type = classify_query_type(query)

        Actor.log.info(f"Query: {query}")
        Actor.log.info(f"Workflow: {workflow} ({get_workflow_description(workflow)})")
        Actor.log.info(f"Query Type: {query_type} ({get_query_type_description(query_type)})")
        Actor.log.info(f"Max sources: {max_sources}")

        # Initialize client
        client = ResearchClient(
            ref_key=ref_key,
            exa_key=exa_key,
            jina_key=jina_key,
            perplexity_key=perplexity_key
        )

        try:
            # Execute workflow
            start_time = time.time()

            if workflow == "direct":
                result = await execute_direct(client, query)
            elif workflow == "exploratory":
                result = await execute_exploratory(client, query, max_urls=min(max_sources, 5))
            elif workflow == "synthesis":
                result = await execute_synthesis(client, query, max_sources=max_sources)
            else:
                raise ValueError(f"Unknown workflow type: {workflow}")

            duration = time.time() - start_time
            Actor.log.info(f"Workflow completed in {duration:.1f}s")
            Actor.log.info(f"Sources: {result.successful_sources}/{result.sources_consulted} successful")

            # Get pricing
            actor_fee = WORKFLOW_PRICING.get(workflow, 0.20)

            # Charge for the workflow (Pay Per Event)
            event_name = f"research-{workflow}"
            await Actor.charge(event_name=event_name, count=1)
            Actor.log.info(f"Charged event: {event_name} (${actor_fee})")

            # Generate reports
            structured_report = generate_report(query, result, duration, actor_fee)
            markdown_report = generate_markdown_report(query, result, duration, actor_fee)

            # Push to dataset
            await Actor.push_data(structured_report)

            # Store markdown in key-value store
            default_store = await Actor.open_key_value_store()
            await default_store.set_value("report.md", markdown_report, content_type="text/markdown")

            # Set output
            await Actor.set_value("OUTPUT", {
                "success": result.success,
                "workflow": workflow,
                "query_type": result.query_type,
                "duration_seconds": round(duration, 2),
                "sources_consulted": result.sources_consulted,
                "successful_sources": result.successful_sources,
                "findings_count": len(result.findings),
                "urls_discovered": len(result.urls_discovered),
                "actor_fee": actor_fee,
                "report_available": True
            })

            Actor.log.info("Research completed successfully!")

        finally:
            await client.close()
