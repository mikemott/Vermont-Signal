# Vermont Signal Test Suite

## Overview

Comprehensive test suite for Vermont Signal V2 covering unit tests, integration tests, and fixtures.

## Running Tests

### Quick Start

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=vermont_news_analyzer --cov-report=html

# Run only unit tests (fast)
pytest -m unit

# Run only filter tests
pytest -m filter

# Run specific test file
pytest tests/unit/test_filters.py

# Run specific test
pytest tests/unit/test_filters.py::TestObituaryFilter::test_explicit_obituary_keyword

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Test Markers

Tests are organized with markers for selective running:

- `@pytest.mark.unit` - Fast unit tests, no external dependencies
- `@pytest.mark.integration` - Integration tests (database, API calls)
- `@pytest.mark.slow` - Slow tests (ML models, large datasets)
- `@pytest.mark.filter` - Content filter tests
- `@pytest.mark.database` - Database operation tests
- `@pytest.mark.security` - Security-related tests

### Examples

```bash
# Run only unit tests (fast)
pytest -m unit

# Run all except slow tests
pytest -m "not slow"

# Run filter and database tests
pytest -m "filter or database"

# Skip integration tests (no database required)
pytest -m "not integration"
```

## Test Structure

```
tests/
├── README.md                          # This file
├── conftest.py                        # Shared fixtures and configuration
├── unit/                              # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_filters.py                # Content filter tests ✅
│   ├── test_entity_normalization.py   # Entity deduplication tests ✅
│   ├── test_config.py                 # Configuration tests (TODO)
│   └── test_cost_tracking.py          # Budget protection tests (TODO)
├── integration/                       # Integration tests (database, API)
│   ├── __init__.py
│   ├── test_database.py               # Database operations (TODO)
│   ├── test_api_endpoints.py          # API endpoint tests (TODO)
│   └── test_pipeline.py               # End-to-end pipeline (TODO)
└── fixtures/                          # Test data and fixtures
    ├── sample_articles.json           # Sample article data (TODO)
    └── sample_extractions.json        # Sample LLM outputs (TODO)
```

## Test Coverage

### Current Coverage

**✅ Implemented:**
- Content filters (comprehensive)
- Entity normalization logic
- Deduplication logic
- Edge cases and boundary conditions

**🚧 To Do:**
- Database operations (CRUD)
- API endpoint tests
- End-to-end pipeline tests
- Cost tracking logic
- Configuration validation

### Target Coverage

- **Overall:** 70%+ coverage (enforced by pytest.ini)
- **Critical modules:** 90%+ coverage
  - `collector/filters.py` ✅ (comprehensive)
  - `modules/database.py` (partial)
  - `batch_processor.py` (TODO)

## Writing Tests

### Guidelines

1. **Test file naming:** `test_*.py` or `*_test.py`
2. **Test function naming:** `test_<what_it_tests>`
3. **Test class naming:** `Test<ComponentName>`
4. **Use markers:** Add appropriate `@pytest.mark.*` decorators
5. **Use fixtures:** Reuse fixtures from `conftest.py`
6. **Docstrings:** Document what each test validates

### Example Test

```python
import pytest
from vermont_news_analyzer.collector.filters import is_obituary

class TestObituaryFilter:
    """Test obituary detection logic"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_explicit_obituary_keyword(self):
        """Should detect explicit 'obituary' keyword"""
        assert is_obituary("John Smith Obituary") is True
        assert is_obituary("Obituaries for October 14") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_obituary_with_age(self):
        """Should NOT flag news articles that mention age"""
        assert is_obituary("Governor, 58, signs new bill") is False
```

### Using Fixtures

```python
def test_article_storage(mock_database, sample_article_data):
    """Test storing an article in the database"""
    db = mock_database
    article_id = db.store_article(sample_article_data)
    assert article_id is not None
```

## Continuous Integration

### GitHub Actions (TODO)

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest -m unit  # Fast unit tests only
```

## Test Data

### Sample Articles

Use fixtures for consistent test data:

```python
@pytest.fixture
def sample_article():
    return {
        "title": "Vermont Legislature Passes Bill",
        "content": "..." # Long enough to pass filters
    }
```

### Mocking External Services

Always mock external API calls:

```python
from unittest.mock import patch

@patch('vermont_news_analyzer.modules.llm_extraction.anthropic.Anthropic')
def test_claude_extraction(mock_claude):
    mock_claude.return_value.messages.create.return_value = {...}
    # Test extraction logic without hitting real API
```

## Debugging Tests

### Common Issues

1. **Import errors:** Ensure `PYTHONPATH` includes project root
2. **Database tests fail:** Use mocks for unit tests, or set up test DB
3. **API key errors:** Use `mock_env_vars` fixture

### Debug Commands

```bash
# Show test collection (don't run)
pytest --collect-only

# Show why test was skipped
pytest -rs

# Drop into debugger on failure
pytest --pdb

# Print output even for passing tests
pytest -s

# Disable warnings
pytest --disable-warnings
```

## Performance

### Test Execution Time

- **Unit tests:** < 5 seconds total
- **Integration tests:** < 30 seconds
- **Full suite:** < 60 seconds

### Optimization Tips

- Use `@pytest.mark.slow` for expensive tests
- Mock external services (databases, APIs)
- Use fixtures to share expensive setup
- Run unit tests first in CI

## Contributing

When adding new features:

1. ✅ Write tests FIRST (TDD)
2. ✅ Ensure all tests pass
3. ✅ Maintain >70% coverage
4. ✅ Add appropriate markers
5. ✅ Document test purpose

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
