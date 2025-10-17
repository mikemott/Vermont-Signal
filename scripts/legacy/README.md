# Legacy Scripts

This directory contains old migration and setup scripts that are no longer needed for production use but are kept for historical reference.

## Migration Scripts (V1 → V2)

These scripts were used for the one-time migration from Vermont Signal V1 to V2:

- `migrate_v1_to_v2.py` - Main migration script
- `migrate_v1_via_api.py` - API-based migration approach
- `export_v1_articles.py` - Export articles from V1 database
- `export_v1_via_proxy.py` - Export via proxy (Railway)
- `export_simple.py` - Simple export utility

## Duplicate Database Setup Scripts

These are duplicate implementations of the database schema initialization:

- `init_db_simple.py` - Simplified schema setup (superseded by `vermont_news_analyzer/modules/database.py`)
- `init_db_local.py` - Local development setup (superseded by `scripts/init_db.py`)

## Current Production Scripts

For current production use, see:
- Database initialization: `scripts/init_db.py` or use the API endpoint `/api/admin/init-db`
- Database schema: `vermont_news_analyzer/modules/database.py` (canonical source)

---

**Note:** These scripts are archived and may not work with the current V2 schema. Do not use for new deployments.
