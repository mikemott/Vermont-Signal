# Vermont Signal

**Production-grade multi-model news analysis for Vermont local news**

Extract facts, entities, and relationships from news articles using:
- **Claude Sonnet 4** + **Gemini 2.5 Flash** + **GPT-4o-mini** (ensemble)
- **spaCy NER** validation
- **Wikidata** enrichment
- **Interactive entity network** visualization

---

## Quick Start

### 1. Setup

```bash
# Clone repository
git clone https://github.com/yourusername/vermont-signal.git
cd vermont-signal

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_trf

# Configure environment
cp .env.example .env
nano .env  # Add your API keys
```

### 2. Run Locally

```bash
# Start API server
python api_server.py

# Start frontend (new terminal)
cd web
npm install
npm run dev
```

Visit: http://localhost:3000

### 3. Process Articles

```bash
# Single article
python vermont_news_analyzer/main.py \
  --mode single \
  --url "https://vtdigger.org/2024/..."

# Batch processing
python vermont_news_analyzer/main.py \
  --mode batch \
  --input-dir data/input
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         TIER 1: INGESTION                        │
│  Text Cleaning → Chunking → Parallel LLM Extraction             │
│  (Claude 3.5 Sonnet + Gemini 1.5 Flash)                         │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                    TIER 2: VALIDATION                            │
│  Cross-Validation → Conflict Detection → GPT-4o-mini Arbitration│
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                    TIER 3: NLP VALIDATION                        │
│  spaCy NER (ground truth) → BERTopic (corpus topics)            │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│                  TIER 4: ENRICHMENT & FUSION                     │
│  Wikidata Linking → Verification → Structured JSON Output       │
└─────────────────────────────────────────────────────────────────┘
```

**4-Tier Pipeline:**
1. **Ingestion** - Text cleaning, chunking
2. **LLM Extraction** - Claude + Gemini parallel extraction
3. **Validation** - Cross-model validation, conflict resolution, spaCy NER
4. **Enrichment** - Wikidata linking, relationship extraction

**Stack:**
- Backend: FastAPI (Python 3.13)
- Frontend: Next.js 15 (TypeScript, Tailwind)
- Database: PostgreSQL
- NLP: spaCy, BERTopic
- Deployment: Docker Compose (Hetzner Cloud)

---

## Documentation

- **[Architecture](docs/architecture.md)** - System design, data flow, database schema
- **[Deployment](docs/deployment.md)** - Hetzner Cloud deployment guide
- **[API Reference](api_server.py)** - REST API endpoints

---

## Features

- **Multi-model ensemble** - Claude, Gemini, GPT arbitration
- **Entity extraction** - People, places, organizations, events
- **Relationship detection** - Co-occurrence analysis
- **Wikidata enrichment** - Entity disambiguation & metadata
- **Interactive visualization** - D3 force-directed entity network
- **Cost tracking** - Token usage & budget monitoring
- **Rate limiting** - Production-ready API security

---

## Cost

**Per Article:** ~$0.019
- Claude Sonnet 4: $0.018
- Gemini 2.5 Flash: $0.0004
- GPT-4o-mini (arbitration): $0.00023

**Monthly (1000 articles):**
- LLM APIs: ~$20
- Hetzner hosting: $10.50
- **Total: ~$30-32/month**

---

## License

MIT License

---

## Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
