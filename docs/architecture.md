# Vermont Signal V2 - Architecture

## Overview

Vermont Signal is a production-grade fact extraction pipeline that processes Vermont local news using a multi-model LLM ensemble with NLP validation.

**Stack:**
- **Backend:** Python 3.13, FastAPI
- **Database:** PostgreSQL
- **Frontend:** Next.js 15, TypeScript, Tailwind CSS
- **ML Models:** Claude Sonnet 4, Gemini 2.5 Flash, GPT-4o-mini
- **NLP:** spaCy (transformer), BERTopic
- **Deployment:** Docker Compose on Hetzner Cloud

---

## 4-Tier Processing Pipeline

### Tier 1: Ingestion & LLM Extraction

**Input:** Raw article text, URL, or file

**Process:**
1. Text cleaning (remove HTML, normalize)
2. Sentence-aligned chunking (200 tokens, 50 overlap)
3. Parallel extraction:
   - **Claude Sonnet 4** (~$0.018/article)
   - **Gemini 2.5 Flash** (~$0.0004/article)

**Output:** Two independent extraction results with entities, confidence scores, summaries

**Modules:**
- `vermont_news_analyzer/modules/ingestion.py`
- `vermont_news_analyzer/modules/llm_extraction.py`

---

### Tier 2: Cross-Validation

**Process:**
1. **Semantic similarity** - Compare summaries (sentence transformers)
2. **Entity merging** - Combine entities from both models
3. **Conflict detection** - Flag discrepancies
4. **Arbitration** - GPT-4o-mini resolves conflicts if needed (~$0.00075/article)
5. **Confidence boosting** - Facts found by both models get higher confidence

**Output:** Consensus extraction with validated facts

**Modules:**
- `vermont_news_analyzer/modules/validation.py`

---

### Tier 3: NLP Validation

**Process:**
1. **spaCy NER** - Extract entities independently (ground truth)
2. **Comparison** - Calculate precision, recall, F1 vs LLM extraction
3. **BERTopic** - Identify corpus-level topics (batch mode only)

**Output:** Validation metrics, LLM vs spaCy comparison

**Modules:**
- `vermont_news_analyzer/modules/nlp_tools.py`

**Why both LLMs and spaCy?**
- spaCy: Deterministic, high precision, fast
- LLMs: Context-aware, handles complex entities, extracts relationships
- Together: Best of both worlds with validation

---

### Tier 4: Enrichment & Fusion

**Process:**
1. **Wikidata linking** - Link entities to knowledge base
2. **Entity disambiguation** - Resolve ambiguous entities
3. **Metadata addition** - Add structured properties
4. **Relationship extraction** - Co-occurrence analysis

**Output:** Final structured JSON with enriched entities

**Modules:**
- `vermont_news_analyzer/modules/enrichment.py`
- `vermont_news_analyzer/modules/wikidata_cache.py`
- `vermont_news_analyzer/modules/database.py`

---

## Database Schema

### Core Tables

**articles**
- Raw article content, metadata
- Processing status tracking
- URL deduplication (hash-based)

**extraction_results**
- Consensus summaries
- Model-specific summaries (audit trail)
- Validation metrics
- Conflict flags

**facts**
- Extracted entities with type, confidence
- Event descriptions
- Source models (which LLMs found this fact)
- Wikidata enrichment (ID, label, description, properties)

**entity_relationships**
- Entity pairs (entity_a, entity_b)
- Relationship type & description
- Confidence scores
- Article context

**api_costs**
- Token usage tracking
- Cost per API call
- Provider breakdown (Anthropic, Google, OpenAI)
- Monthly/daily aggregation

**corpus_topics** & **article_topics**
- BERTopic results
- Topic keywords, representative docs
- Article-topic associations

---

## API Design

**REST API** (FastAPI with rate limiting)

### Public Endpoints
- `GET /api/health` - Health check
- `GET /api/articles` - List articles (paginated)
- `GET /api/articles/{id}` - Get article details
- `GET /api/entities/network` - Full entity network
- `GET /api/entities/network/entity/{name}` - Entity-centric view
- `GET /api/entities/network/article/{id}` - Article-specific network
- `GET /api/stats` - System statistics
- `GET /api/sources` - News source breakdown

### Admin Endpoints (Bearer token required)
- `POST /api/admin/init-db` - Initialize database
- `POST /api/admin/import-article` - Import article
- `POST /api/admin/process-batch` - Process pending articles
- `POST /api/admin/generate-relationships` - Build entity network
- `GET /api/admin/db-status` - Database status

**Rate Limits:**
- Public: 100 req/min
- Expensive queries: 50 req/min
- Admin: 5-20 req/hour

---

## Frontend Architecture

**Next.js 15** (App Router, TypeScript)

**Key Features:**
- **Article Intelligence** - Browse processed articles
- **Entity Network** - Interactive D3 force-directed graph
- **Power User Builder** - Search entities, filter by time
- **Topics & Trends** - BERTopic visualization (planned)
- **Model Comparison** - Compare LLM outputs (planned)

**Components:**
- `EntityNetworkD3.tsx` - D3 force simulation
- `ArticleLibrary.tsx` - Article list with search
- `ArticleDetailsPanel.tsx` - Slide-out article view
- `EntityDetailsPanel.tsx` - Entity information panel

**Design:**
- Financial Times-inspired layout
- Playfair Display (headings) + Work Sans (body)
- Navy (#0f1c3f) and Gold (#d4a574) color scheme
- Responsive, mobile-optimized

---

## Data Flow

```
1. Article URL → Ingestion → Text cleaning
                             ↓
2. Chunking → Parallel LLM extraction (Claude + Gemini)
                             ↓
3. Cross-validation → Conflict detection → Arbitration (GPT if needed)
                             ↓
4. spaCy NER validation → Metrics calculation
                             ↓
5. Wikidata enrichment → Entity linking
                             ↓
6. Database storage → Relationship generation
                             ↓
7. REST API → Frontend visualization
```

**Processing Time:** ~7-9 seconds per article
**Batch Throughput:** ~100 articles in 12-15 minutes (parallel)

---

## Configuration

**Environment Variables** (`.env`)

```bash
# LLM APIs
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...

# Models
CLAUDE_MODEL=claude-sonnet-4-20250514
GEMINI_MODEL=gemini-2.5-flash
OPENAI_MODEL=gpt-4o-mini

# Pipeline
CHUNK_SIZE=200
CHUNK_OVERLAP=50
CONFIDENCE_THRESHOLD=0.4
SIMILARITY_THRESHOLD=0.75
PARALLEL_PROCESSING=true

# NLP
SPACY_MODEL=en_core_web_trf
ENABLE_WIKIDATA_ENRICHMENT=true

# Database
DATABASE_URL=postgresql://...  # Or individual params

# Security
ADMIN_API_KEY=secure-random-key
CORS_ORIGINS=http://localhost:3000
```

---

## Cost Model

**Per Article:**
- Claude Sonnet 4: $0.018
- Gemini 2.5 Flash: $0.0004
- GPT-4o-mini (arbitration, ~30%): $0.00023
- **Total: ~$0.019/article**

**Monthly (1000 articles):**
- LLM API costs: ~$19-20
- Hetzner hosting: $10.50
- **Total: ~$30-32/month**

**Budget Protection:**
- Daily cap: $5
- Monthly cap: $25
- Cost tracking in database
- `scripts/check_budget.py` for monitoring

---

## Performance

**Single Article:**
- Ingestion: 0.5s
- LLM extraction (parallel): 3-5s
- Validation: 1s
- spaCy NER: 0.1s
- Wikidata: 2s
- **Total: 7-9s**

**Batch (100 articles):**
- Parallel: 12-15 min
- Sequential: 25-30 min

**Accuracy (validated on 50 articles):**
- Entity F1 vs spaCy: 0.91
- Summary similarity (Claude vs Gemini): 0.84 avg
- Wikidata match rate: 78%

---

## Deployment Details

**Docker Compose Services:**

```yaml
postgres:     # 512MB-1GB RAM, persistent volume
api:          # 512MB-1GB RAM, stateless
worker:       # 3-5GB RAM, persistent ML model cache
frontend:     # 256MB-512MB RAM, stateless
caddy:        # 128MB-256MB RAM, auto-HTTPS
```

**Key Features:**
- ML models cached in volume (fast redeploys)
- PostgreSQL data persisted
- Caddy auto-SSL
- Health checks for all services
- Resource limits configured

---

## Monitoring

**Application Metrics:**
- `/api/stats` - Articles, facts, costs
- `/api/health` - Database connectivity
- `scripts/check_budget.py` - Cost alerts

**System Metrics:**
- `docker stats` - Container resources
- Docker logs - Application logs
- PostgreSQL stats - Database size

---

## Security

- Bearer token authentication (admin endpoints)
- Rate limiting (slowapi)
- CORS configured
- No API keys in code
- Environment variables only
- HTTPS enforced (Caddy)
- Database password-protected

---

## Future Improvements

1. **Caching:** Redis for API responses
2. **Search:** Elasticsearch for full-text search
3. **Real-time:** WebSocket updates for processing status
4. **Analytics:** Grafana dashboard
5. **Testing:** Automated test suite
6. **CI/CD:** GitHub Actions deployment
