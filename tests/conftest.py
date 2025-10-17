"""
Pytest configuration and fixtures for Vermont Signal tests

Provides reusable test fixtures for database connections, mock data, etc.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import os


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, no external dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (database, API calls)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (ML models, large datasets)"
    )
    config.addinivalue_line(
        "markers", "filter: Content filter tests"
    )
    config.addinivalue_line(
        "markers", "database: Database operation tests"
    )
    config.addinivalue_line(
        "markers", "security: Security-related tests"
    )


# ============================================================================
# ENVIRONMENT FIXTURES
# ============================================================================

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    test_env = {
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "GOOGLE_API_KEY": "test-google-key",
        "OPENAI_API_KEY": "test-openai-key",
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "test_db",
        "DATABASE_USER": "test_user",
        "DATABASE_PASSWORD": "test_password",
        "ADMIN_API_KEY": "test-admin-key",
    }

    for key, value in test_env.items():
        monkeypatch.setenv(key, value)

    return test_env


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture
def mock_database():
    """Mock VermontSignalDatabase for testing"""
    from unittest.mock import MagicMock

    db = MagicMock()
    db.connect = MagicMock()
    db.disconnect = MagicMock()
    db.get_connection = MagicMock()

    # Mock connection context manager
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    db.get_connection.return_value.__enter__.return_value = mock_conn

    return db


@pytest.fixture
def sample_article_data():
    """Sample article data for testing"""
    return {
        "title": "Vermont Legislature Passes Climate Bill",
        "url": "https://vtdigger.org/2025/10/14/climate-bill",
        "content": """
            The Vermont Legislature passed a comprehensive climate bill on Thursday,
            marking a significant step in the state's efforts to reduce carbon emissions.
            Governor Phil Scott praised the bipartisan effort, saying "This is a win for Vermont."
            The bill includes provisions for renewable energy investment and carbon pricing.
            Senator Bernie Sanders also expressed support for the measure.
        """ * 3,  # Make it long enough
        "summary": "Vermont passes comprehensive climate legislation",
        "source": "VTDigger",
        "author": "John Reporter",
        "published_date": "2025-10-14T10:00:00"
    }


@pytest.fixture
def sample_extraction_result():
    """Sample LLM extraction result for testing"""
    return {
        "consensus_summary": "Vermont Legislature passes climate bill with bipartisan support",
        "extracted_facts": [
            {
                "entity": "Vermont Legislature",
                "type": "ORGANIZATION",
                "confidence": 0.95,
                "event_description": "Passed comprehensive climate bill",
                "sources": ["claude", "gemini"]
            },
            {
                "entity": "Phil Scott",
                "type": "PERSON",
                "confidence": 0.92,
                "event_description": "Governor praised the bipartisan effort",
                "sources": ["claude", "gemini"]
            },
            {
                "entity": "Bernie Sanders",
                "type": "PERSON",
                "confidence": 0.90,
                "event_description": "Senator expressed support for the measure",
                "sources": ["claude"]
            }
        ],
        "metadata": {
            "processing_timestamp": "2025-10-14T10:30:00",
            "total_facts": 3,
            "high_confidence_facts": 3,
            "overall_confidence": 0.92,
            "conflict_report": {
                "has_conflicts": False,
                "summary_similarity": 0.88
            }
        },
        "spacy_validation": {
            "entity_count": 5,
            "comparison": {
                "precision": 0.85,
                "recall": 0.80,
                "f1_score": 0.82
            }
        }
    }


# ============================================================================
# FILTER TEST FIXTURES
# ============================================================================

@pytest.fixture
def obituary_samples():
    """Sample obituary texts for testing"""
    return {
        "explicit": "John Smith Obituary - Services at 2pm",
        "age_pattern": "Mary Johnson, 82, of Burlington",
        "passed_away": "Local teacher passed away at age 65",
        "name_only": "Barbara Fee Dickason",
        "death_notice": "Death notice: John Putnam"
    }


@pytest.fixture
def event_listing_samples():
    """Sample event listing texts"""
    return {
        "calendar": "Community Calendar for October",
        "upcoming": "Upcoming events this weekend in Burlington",
        "things_to_do": "Things to do in Vermont this fall",
        "date_range": "Events: October 15-20"
    }


@pytest.fixture
def valid_news_samples():
    """Sample valid news article texts"""
    return {
        "climate": "Vermont Legislature passes comprehensive climate legislation",
        "budget": "Governor proposes $8 billion state budget",
        "education": "Burlington School Board approves new curriculum",
        "infrastructure": "State announces $100M infrastructure investment"
    }


# ============================================================================
# MOCK LLM FIXTURES
# ============================================================================

@pytest.fixture
def mock_claude_response():
    """Mock Claude API response"""
    return {
        "consensus_summary": "Test summary from Claude",
        "extracted_facts": [
            {
                "entity": "Test Entity",
                "type": "PERSON",
                "confidence": 0.9,
                "event_description": "Test event"
            }
        ]
    }


@pytest.fixture
def mock_gemini_response():
    """Mock Gemini API response"""
    return {
        "consensus_summary": "Test summary from Gemini",
        "extracted_facts": [
            {
                "entity": "Test Entity",
                "type": "PERSON",
                "confidence": 0.85,
                "event_description": "Test event"
            }
        ]
    }


# ============================================================================
# COST TRACKING FIXTURES
# ============================================================================

@pytest.fixture
def sample_api_costs():
    """Sample API cost data"""
    return [
        {
            "provider": "anthropic",
            "model": "claude-sonnet-4",
            "input_tokens": 1500,
            "output_tokens": 500,
            "cost": 0.018
        },
        {
            "provider": "google",
            "model": "gemini-2.5-flash",
            "input_tokens": 1500,
            "output_tokens": 500,
            "cost": 0.0004
        },
        {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "input_tokens": 1500,
            "output_tokens": 500,
            "cost": 0.00023
        }
    ]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_mock_cursor_with_results(results):
    """Create a mock database cursor that returns specified results"""
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = results[0] if results else None
    mock_cursor.fetchall.return_value = results
    mock_cursor.rowcount = len(results)
    return mock_cursor
