# Deep Research AI Agent

**Multi-source research agent that gathers, cross-validates, and synthesizes information from 4 specialized AI APIs.**

AI-powered deep research for RAG pipelines, AI agents, content research, technical documentation, academic discovery, and automated fact-checking. Automatically classifies queries and selects optimal research workflows.

## Key Features

- **Multi-Source Cross-Validation** - Triangulates findings across Ref, Exa, Jina, and Perplexity
- **Intelligent Query Classification** - Auto-routes to documentation, code, academic, or general search
- **3 Research Workflows** - Direct (fast lookup), Exploratory (deep dive), Synthesis (cross-validation)
- **BYOK Model** - Bring your own API keys for full cost transparency
- **Structured Output** - Clean JSON reports with citations, source URLs, and markdown synthesis

## How It Works

1. **Submit your query** - Ask any research question
2. **Auto-classification** - Agent detects query type (docs, code, academic, general)
3. **Workflow selection** - Picks optimal depth or use your manual override
4. **Multi-source gathering** - Queries relevant APIs in parallel
5. **Cross-validation & synthesis** - AI synthesizes findings with citations

## Research Workflows

| Workflow | Time | Best For | Price (FREE tier) |
|----------|------|----------|-------------------|
| **Direct** | 30-60s | Specific lookups, documentation, code examples | $0.10 |
| **Exploratory** | 1-2min | Learning new topics, discovery, deep dives | $0.20 |
| **Synthesis** | 3-5min | Comparisons, best practices, cross-validation | $0.30 |

### Tiered Pricing Discounts

| Tier | Discount | Direct | Exploratory | Synthesis |
|------|----------|--------|-------------|-----------|
| FREE | — | $0.10 | $0.20 | $0.30 |
| BRONZE (Starter) | 10% off | $0.09 | $0.18 | $0.27 |
| SILVER (Scale) | 20% off | $0.08 | $0.16 | $0.24 |
| GOLD (Business) | 35% off | $0.065 | $0.13 | $0.195 |

## Smart Source Routing

The agent automatically routes queries to the best sources:

| Query Type | Primary Source | Fallback | Example Queries |
|------------|----------------|----------|-----------------|
| **Documentation** | Ref | Exa | "FastAPI WebSocket docs", "React hooks API" |
| **Code** | Exa Code | Jina | "Python async implementation", "sorting algorithm" |
| **Academic** | Jina arXiv | Perplexity | "transformer architecture paper", "LLM research" |
| **General** | Jina Web | Exa | "AI trends 2025", "best practices microservices" |

## Use Cases

- **RAG Pipeline Enrichment** - Feed high-quality, cross-validated context to LLMs
- **AI Agent Research** - Give your agents comprehensive research capabilities
- **Technical Documentation** - Find official docs, API references, code examples
- **Academic Research** - Discover papers, studies, and literature
- **Competitive Analysis** - Compare technologies, frameworks, approaches
- **Fact Verification** - Cross-validate claims across multiple sources
- **Content Research** - Gather comprehensive topic coverage for writing

## BYOK Model (Bring Your Own Keys)

You provide API keys, you pay providers directly. No markup on API costs.

**Required API Keys:**

| Provider | Purpose | Get Key |
|----------|---------|---------|
| **Ref** | Documentation & API references | [ref.dev](https://ref.dev) |
| **Exa** | Semantic search & code examples | [exa.ai](https://exa.ai) |
| **Jina** | Web search, URL reading, arXiv | [jina.ai](https://jina.ai) |
| **Perplexity** | AI synthesis & exploration | [perplexity.ai](https://perplexity.ai) |

**Why BYOK?**
- Full cost transparency - see exactly what each API costs
- Use your existing quotas and credits
- No vendor lock-in
- Control your own API spend

## Total Cost Estimate

**Actor fee + API costs:**

| Workflow | Actor Fee | Est. API Cost | Total |
|----------|-----------|---------------|-------|
| Direct | $0.10 | $0.01-0.05 | ~$0.11-0.15 |
| Exploratory | $0.20 | $0.05-0.15 | ~$0.25-0.35 |
| Synthesis | $0.30 | $0.10-0.30 | ~$0.40-0.60 |

*API costs vary by query complexity and number of sources consulted.*

## Output Format

**Dataset (JSON):**
```json
{
  "query": "Compare FastAPI vs Flask",
  "workflow": "synthesis",
  "query_type": "general",
  "duration_seconds": 187.5,
  "source_count": 5,
  "successful_sources": 4,
  "findings_summary": "Key differences...",
  "synthesis": "Based on cross-validation across multiple sources...",
  "urls_discovered": ["https://...", "https://..."],
  "actor_fee": 0.30,
  "timestamp": "2025-01-15T10:30:00Z",
  "success": true
}
```

**Key-Value Store:** `report.md` - Human-readable markdown report with full synthesis

## Example Queries

**Direct Workflow (specific lookups):**
- "FastAPI dependency injection documentation"
- "TypeScript generics syntax"
- "Python asyncio API reference"

**Exploratory Workflow (discovery):**
- "What is retrieval augmented generation?"
- "How do vector databases work?"
- "Latest developments in AI agents"

**Synthesis Workflow (cross-validation):**
- "Compare LangChain vs LlamaIndex for RAG"
- "Best practices for microservices authentication"
- "FastAPI vs Flask vs Django for REST APIs"

## Input Schema

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Your research question |
| `workflow` | enum | No | `auto`, `direct`, `exploratory`, `synthesis` (default: auto) |
| `ref_api_key` | string | Yes | Ref API key |
| `exa_api_key` | string | Yes | Exa API key |
| `jina_api_key` | string | Yes | Jina API key |
| `perplexity_api_key` | string | Yes | Perplexity API key |

## FAQ

**Q: Why 4 different APIs?**
Each API specializes in different content types. Ref excels at documentation, Exa at code and semantic search, Jina at web content and academic papers, Perplexity at AI synthesis. Together they provide comprehensive, cross-validated coverage.

**Q: Can I use fewer APIs?**
Not currently. All 4 are required for the research pipeline to function properly. Each plays a specific role in the workflow.

**Q: How accurate is auto-classification?**
The classifier uses pattern matching to detect query intent. It correctly routes 90%+ of queries. You can always override with manual workflow selection.

**Q: What if an API fails?**
The agent continues with available sources and notes failures. Partial results are returned with error details. The synthesis workflow is resilient to individual API failures.

**Q: Is my data stored?**
Results are stored in your Apify dataset. API calls go directly to providers using your keys. We don't store or log your API keys.

**Q: How does tiered pricing work?**
Higher Apify subscription tiers get volume discounts. GOLD (Business) tier users pay 35% less per research than FREE tier users.

## Technical Architecture

```
Query → Classifier → Workflow Selection
                          ↓
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
      DIRECT         EXPLORATORY      SYNTHESIS
    (1 source)      (Perplexity +    (Triple Stack:
                     URL reads)    Ref + Exa + Jina)
         ↓                ↓                ↓
      Results          Results       Perplexity
                                     Synthesis
         ↓                ↓                ↓
         └────────────────┼────────────────┘
                          ↓
                   Structured Report
```

## Support

- **Issues:** Open an issue on the Actor page
- **Documentation:** This README and input schema tooltips

## License

MIT
