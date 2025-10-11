# Vermont Signal

## Overview

A production-grade news analysis pipeline that extracts facts from Vermont local news using multi-model LLM ensemble (Claude + Gemini + GPT) with NLP validation.

---

## Architecture

### V1 System (Legacy - Fly.io)
- **Status**: Production, being phased out
- **Location**: Fly.io
- **Components**:
  - App: `vermont-signal` (Fly.io)
  - Database: `vermont-signal-db` (Postgres on Fly.io)
- **Credentials**:
  - User: `vermont_signal`
  - Password: `vermont_v1_2025_secure` (RESET on 2025-10-11)
  - Database: `vermont_signal`
- **Features**: Single Claude model, basic sentiment analysis

### V2 System (Current - Railway)
- **Status**: Active development
- **Location**: Railway
- **Components**:
  - API Service: `api` (FastAPI on Railway)
  - Worker Service: `worker` (Batch processor with cron)
  - Database: PostgreSQL (Railway managed)
- **API URL**: `https://api-production-9b77.up.railway.app`
- **Features**:
  - Multi-model ensemble (Claude Sonnet 4 + Gemini 2.5 Flash + GPT-4o-mini)
  - spaCy NER validation
  - Wikidata enrichment
  - Entity relationship extraction
  - Confidence scoring

### Frontend (Next.js)
- **Location**: `./web/` directory
- **Framework**: Next.js with TypeScript
- **Styling**: Tailwind CSS + Playfair Display + Work Sans typography
- **Design**: Financial Times-inspired layout with centered header and horizontal tabs

---

## Key Files & Directories

```
Vermont-Signal/
├── PROJECT_SUMMARY.md             # This file
├── RAILWAY_DEPLOYMENT_2025.md     # Railway deployment guide
│
├── api_server.py                  # FastAPI backend
├── Dockerfile.api                 # Docker config for API service
├── Dockerfile.worker              # Docker config for worker service
├── schema.sql                     # Database schema
│
├── vermont_news_analyzer/         # Core pipeline code
│   ├── modules/
│   │   ├── ingestion.py           # Text cleaning & chunking
│   │   ├── llm_extraction.py      # Multi-LLM extraction
│   │   ├── validation.py          # Cross-validation
│   │   ├── nlp_tools.py           # spaCy & BERTopic
│   │   ├── enrichment.py          # Wikidata & fusion
│   │   └── database.py            # Database interface
│   ├── config.py                  # Configuration
│   └── main.py                    # Pipeline orchestrator
│
├── web/                           # Next.js frontend
│   ├── app/                       # Next.js 15 app router
│   ├── components/                # React components
│   └── public/                    # Static assets
│
├── scripts/                       # Utility scripts
│   ├── migrate_v1_to_v2.py        # V1 migration script
│   └── init_db_simple.py          # Database initialization
│
├── docs/
│   └── archive/                   # Archived documentation
│
└── .env                           # Environment variables
```

---

## Current Status

### ✅ Completed
1. V2 API deployed on Railway
2. V2 database provisioned on Railway
3. V1 database password reset (can now access V1 data)
4. Migration script ready (`migrate_v1_to_v2.py`)
5. Next.js frontend scaffold

### ⏳ In Progress / Next Steps
1. **Run V1 → V2 migration** (use `V1_DATABASE_ACCESS.md`)
2. Initialize V2 database schema on Railway
3. Deploy worker service to Railway
4. Process migrated articles through V2 pipeline
5. Connect Next.js frontend to Railway API
6. Test end-to-end flow

---

## Migration Plan

### Goal
Import **high-value** articles from V1 while filtering out routine content (obituaries, school notes, event listings, etc.)

### Expected Results
- From ~800 V1 articles → ~500-550 imported to V2 (62-68%)
- Filter out ~250-300 low-value articles (32-38%)

### Steps
1. **Analyze** - Review what would be imported
2. **Dry run** - Test migration without importing
3. **Execute** - Import articles to V2
4. **Process** - Run V2 pipeline on imported articles

See `V1_DATABASE_ACCESS.md` for detailed instructions.

---

## Environment Variables

### Local Development (`.env`)
```bash
# API Keys
ANTHROPIC_API_KEY=sk-ant-api03-...
GOOGLE_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...

# Models
CLAUDE_MODEL=claude-sonnet-4-20250514
GEMINI_MODEL=gemini-2.5-flash
OPENAI_MODEL=gpt-4o-mini

# Pipeline Config
CHUNK_SIZE=200
CONFIDENCE_THRESHOLD=0.4
PARALLEL_PROCESSING=true
```

### Railway (Production)
- Same environment variables set via Railway dashboard
- Plus: `DATABASE_URL` (auto-provided by Railway)
- Plus: `TZ=America/New_York` (for correct cron timing)

---

## Quick Commands

### Railway (V2)
```bash
# Check status
railway status

# View logs
railway logs

# Open shell
railway shell

# Check API health
curl https://api-production-9b77.up.railway.app/api/health

# Check database status
curl https://api-production-9b77.up.railway.app/api/admin/db-status
```

### Fly.io (V1)
```bash
# Check status
flyctl status -a vermont-signal-db

# Connect to database
flyctl postgres connect -a vermont-signal-db

# Start proxy for migration
flyctl proxy 5432:5432 -a vermont-signal-db
```

### Migration
```bash
# 1. Start V1 proxy (Terminal 1)
flyctl proxy 5432:5432 -a vermont-signal-db

# 2. Analyze (Terminal 2)
source venv/bin/activate
python migrate_v1_to_v2.py --analyze --days 90 \
  --v1-host localhost \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password vermont_v1_2025_secure

# 3. Dry run
python migrate_v1_to_v2.py --import --dry-run --days 30 \
  --v1-host localhost \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password vermont_v1_2025_secure

# 4. Execute
python migrate_v1_to_v2.py --import --days 90 \
  --v1-host localhost \
  --v1-database vermont_signal \
  --v1-user vermont_signal \
  --v1-password vermont_v1_2025_secure
```

### Local Development
```bash
# Activate virtual environment
source venv/bin/activate

# Run API server locally
python api_server.py

# Run Next.js frontend
cd web
npm run dev

# Process a single article
python vermont_news_analyzer/main.py --mode single --text "Article text..."
```

---

## Cost Estimates

### Railway (V2)
- API (512MB, 24/7): ~$2-3/month
- Worker (2GB, 4hrs/day): ~$6-8/month
- PostgreSQL: Free (up to 5GB)
- **Subtotal**: ~$8-11/month

### LLM API Costs
- Claude Sonnet 4: ~$0.018/article
- Gemini 2.5 Flash: ~$0.0004/article
- GPT-4o-mini (arbitration): ~$0.00075/article
- **Cost per article**: ~$0.019 (with arbitration: ~$0.020)
- **Monthly estimate** (processing ~1000 articles): ~$20-25/month

### Total: ~$33-36/month

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL
- **LLMs**: Claude Sonnet 4, Gemini 2.5 Flash, GPT-4o-mini
- **NLP**: spaCy (en_core_web_trf), BERTopic
- **Knowledge Base**: Wikidata API
- **Hosting**: Railway

### Frontend
- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **Fonts**: Playfair Display (headings), Work Sans (body)
- **Design**: Financial Times-inspired

### Development
- **Version Control**: Git
- **Environment**: Python 3.13, Node.js
- **Package Management**: pip (Python), npm (Node.js)

---

## Key Documentation Files

1. **V1_DATABASE_ACCESS.md** - V1 credentials & migration instructions
2. **MIGRATION_STRATEGY.md** - Filtering logic & expected results
3. **RAILWAY_DEPLOYMENT_2025.md** - Railway deployment guide
4. **README.md** - Main project documentation
5. **PROJECT_SUMMARY.md** - This file (quick reference)

---

## Next Immediate Actions

1. ✅ **V1 password reset** - COMPLETE
2. ⏳ **Verify V2 database is initialized**
   ```bash
   curl https://api-production-9b77.up.railway.app/api/admin/db-status
   ```
3. ⏳ **Run migration analysis**
   - Follow steps in `V1_DATABASE_ACCESS.md`
4. ⏳ **Execute migration**
   - Import high-value V1 articles to V2
5. ⏳ **Process articles**
   - Run V2 pipeline on migrated data
6. ⏳ **Update frontend**
   - Connect to Railway API URL

---

## Support & Resources

### Project Resources
- V1 Database: `vermont-signal-db.flycast` (Fly.io)
- V2 API: `https://api-production-9b77.up.railway.app`
- V2 Database: Railway managed (via `DATABASE_URL`)

### External Documentation
- Railway: https://docs.railway.com
- Fly.io: https://fly.io/docs
- FastAPI: https://fastapi.tiangolo.com
- Next.js: https://nextjs.org/docs

### Monitoring
- Railway Dashboard: https://railway.app/dashboard
- Fly.io Dashboard: https://fly.io/dashboard
- Check API health: `/api/health`
- Check stats: `/api/stats`
