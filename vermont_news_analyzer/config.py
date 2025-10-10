"""
Configuration module for Vermont News Analyzer Pipeline
Loads environment variables and provides configuration settings for all tiers
"""

import os
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "vermont_news_analyzer" / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
LOG_DIR = BASE_DIR / "vermont_news_analyzer" / "logs"

# Create directories if they don't exist
for directory in [INPUT_DIR, OUTPUT_DIR, LOG_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================================
# API CONFIGURATION
# ============================================================================

class APIConfig:
    """API keys and model configuration for LLM services"""

    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # Model names
    CLAUDE_MODEL: str = os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # API request configuration
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    TIMEOUT_SECONDS: int = int(os.getenv("TIMEOUT_SECONDS", "30"))

    @classmethod
    def validate(cls) -> bool:
        """Validate that required API keys are present"""
        missing_keys = []

        if not cls.ANTHROPIC_API_KEY:
            missing_keys.append("ANTHROPIC_API_KEY")
        if not cls.GOOGLE_API_KEY:
            missing_keys.append("GOOGLE_API_KEY")
        if not cls.OPENAI_API_KEY:
            missing_keys.append("OPENAI_API_KEY")

        if missing_keys:
            logging.warning(
                f"Missing API keys: {', '.join(missing_keys)}. "
                f"Set them in .env file or environment variables."
            )
            return False

        return True


# ============================================================================
# PIPELINE CONFIGURATION
# ============================================================================

class PipelineConfig:
    """Configuration for pipeline processing parameters"""

    # Text chunking
    CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "200"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "50"))

    # Confidence and similarity thresholds
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.4"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))

    # Processing modes
    BATCH_MODE: bool = os.getenv("BATCH_MODE", "false").lower() == "true"
    PARALLEL_PROCESSING: bool = os.getenv("PARALLEL_PROCESSING", "true").lower() == "true"

    # Entity types to extract
    ENTITY_TYPES: list = [
        "PERSON",
        "ORGANIZATION",
        "LOCATION",
        "GPE",  # Geopolitical entity
        "DATE",
        "PRODUCT",
        "EVENT"
    ]


# ============================================================================
# NLP TOOLS CONFIGURATION
# ============================================================================

class NLPConfig:
    """Configuration for spaCy, BERTopic, and other NLP tools"""

    # spaCy model
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_trf")

    # BERTopic configuration
    BERTOPIC_MIN_TOPIC_SIZE: int = int(os.getenv("BERTOPIC_MIN_TOPIC_SIZE", "5"))
    BERTOPIC_N_GRAM_RANGE: tuple = (1, 3)

    # Sentence transformer model for embeddings
    SENTENCE_TRANSFORMER_MODEL: str = os.getenv(
        "SENTENCE_TRANSFORMER_MODEL",
        "all-MiniLM-L6-v2"
    )


# ============================================================================
# WIKIDATA CONFIGURATION
# ============================================================================

class WikidataConfig:
    """Configuration for Wikidata enrichment"""

    ENABLE_WIKIDATA_ENRICHMENT: bool = os.getenv(
        "ENABLE_WIKIDATA_ENRICHMENT",
        "true"
    ).lower() == "true"

    WIKIDATA_API_ENDPOINT: str = os.getenv(
        "WIKIDATA_API_ENDPOINT",
        "https://www.wikidata.org/w/api.php"
    )

    WIKIDATA_TIMEOUT: int = int(os.getenv("WIKIDATA_TIMEOUT", "10"))

    # Vermont-specific entity filtering
    VERMONT_GEONAME_ID: str = "5242283"  # GeoNames ID for Vermont


# ============================================================================
# LOGGING CONFIGURATION
# ============================================================================

class LogConfig:
    """Logging configuration"""

    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Path = Path(os.getenv(
        "LOG_FILE",
        str(LOG_DIR / "pipeline.log")
    ))

    # Log format
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    DATE_FORMAT: str = "%Y-%m-%d %H:%M:%S"

    @classmethod
    def setup_logging(cls) -> None:
        """Configure logging for the entire application"""

        # Ensure log directory exists
        cls.LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

        logging.basicConfig(
            level=getattr(logging, cls.LOG_LEVEL.upper()),
            format=cls.LOG_FORMAT,
            datefmt=cls.DATE_FORMAT,
            handlers=[
                logging.FileHandler(cls.LOG_FILE),
                logging.StreamHandler()
            ]
        )


# ============================================================================
# PROMPT TEMPLATES
# ============================================================================

class PromptTemplates:
    """Structured prompts for LLM extraction"""

    CLAUDE_EXTRACTION_PROMPT = """You are an expert fact-extractor and news analyst. Your task is to process the following news article text and extract structured information.

Article Text:
{input_text}

Generate a JSON response with the following structure:
{{
  "consensus_summary": "A concise factual summary (max 3 sentences) preserving all core facts",
  "extracted_facts": [
    {{
      "entity": "entity name",
      "type": "PERSON|ORGANIZATION|LOCATION|DATE|PRODUCT|EVENT",
      "confidence": 0.0-1.0,
      "event_description": "who did what, when, where, why",
      "note": "optional note about uncertainty or verification status"
    }}
  ]
}}

Rules:
1. Prioritize factual fidelity - do not hallucinate
2. If uncertain about a fact, set confidence < 0.4 and add a note
3. Extract ALL named entities and events
4. Link entities to events with clear descriptions
5. Return ONLY valid JSON, no additional text"""

    GEMINI_EXTRACTION_PROMPT = """You are a deep contextual analyst specializing in news analysis. Analyze this article with focus on causal inference and event linking.

Article Text:
{input_text}

Generate a JSON response with:
{{
  "consensus_summary": "A concise factual summary (max 3 sentences) with contextual insights",
  "extracted_facts": [
    {{
      "entity": "entity name",
      "type": "PERSON|ORGANIZATION|LOCATION|DATE|PRODUCT|EVENT",
      "confidence": 0.0-1.0,
      "event_description": "detailed causal chain - who did what, why it happened, what resulted",
      "note": "optional contextual note"
    }}
  ]
}}

Focus on:
- Causal relationships between events
- Temporal sequences
- Motivations and outcomes
- Relationships between entities

Return ONLY valid JSON."""

    CONFLICT_RESOLUTION_PROMPT = """You are a fact-checking arbitrator. Two AI models have analyzed the same article and produced different outputs. Your task is to reconcile conflicts and produce the most accurate extraction.

Original Article:
{input_text}

Claude's Output:
{claude_output}

Gemini's Output:
{gemini_output}

Identified Conflicts:
{conflicts}

Generate a reconciled JSON output that:
1. Resolves conflicts by determining the most accurate information
2. Combines complementary information from both sources
3. Flags any remaining uncertainties with low confidence scores
4. Explains conflict resolution in notes field

Return the same JSON structure:
{{
  "consensus_summary": "reconciled summary",
  "extracted_facts": [...]
}}

Return ONLY valid JSON."""


# ============================================================================
# VALIDATION
# ============================================================================

def validate_configuration() -> bool:
    """
    Validate all configuration settings

    Returns:
        bool: True if configuration is valid, False otherwise
    """

    # Setup logging first
    LogConfig.setup_logging()
    logger = logging.getLogger(__name__)

    # Validate API keys
    if not APIConfig.validate():
        logger.error("API configuration validation failed")
        return False

    # Validate directories
    for directory in [INPUT_DIR, OUTPUT_DIR, LOG_DIR]:
        if not directory.exists():
            logger.error(f"Required directory does not exist: {directory}")
            return False

    logger.info("Configuration validation successful")
    return True


# Initialize logging on module import
LogConfig.setup_logging()
