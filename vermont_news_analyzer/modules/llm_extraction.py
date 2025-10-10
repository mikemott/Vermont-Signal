"""
Tier 1 LLM Extraction Module: Multi-model fact extraction
Implements parallel API calls to Claude, Gemini, and GPT-4o-mini with structured JSON output
"""

import json
import logging
import asyncio
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import sys

# API client imports
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

sys.path.append(str(Path(__file__).parent.parent))
from config import APIConfig, PromptTemplates, PipelineConfig

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Container for LLM extraction results"""
    model_name: str
    consensus_summary: str
    extracted_facts: List[Dict]
    raw_response: str
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict] = None


class LLMExtractor:
    """Base class for LLM extraction with common functionality"""

    def __init__(self, max_retries: int = None, timeout: int = None):
        """
        Initialize extractor

        Args:
            max_retries: Maximum retry attempts (defaults to config)
            timeout: Request timeout in seconds (defaults to config)
        """
        self.max_retries = max_retries or APIConfig.MAX_RETRIES
        self.timeout = timeout or APIConfig.TIMEOUT_SECONDS

    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON from LLM response, handling markdown code blocks

        Args:
            response_text: Raw response text

        Returns:
            Dict or None if parsing fails
        """

        # Try direct parsing first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass

        # Try extracting from markdown code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding JSON object in text
        brace_start = response_text.find('{')
        brace_end = response_text.rfind('}')
        if brace_start != -1 and brace_end != -1:
            try:
                return json.loads(response_text[brace_start:brace_end + 1])
            except json.JSONDecodeError:
                pass

        logger.error("Failed to parse JSON from response")
        return None

    def _validate_extraction_schema(self, data: Dict) -> bool:
        """
        Validate extraction response has required fields

        Args:
            data: Parsed JSON response

        Returns:
            bool: True if valid
        """

        if 'consensus_summary' not in data:
            logger.error("Missing 'consensus_summary' field")
            return False

        if 'extracted_facts' not in data:
            logger.error("Missing 'extracted_facts' field")
            return False

        if not isinstance(data['extracted_facts'], list):
            logger.error("'extracted_facts' must be a list")
            return False

        # Validate fact objects
        for fact in data['extracted_facts']:
            if not isinstance(fact, dict):
                logger.error("Each fact must be a dictionary")
                return False

            required_fields = ['entity', 'type', 'confidence', 'event_description']
            for field in required_fields:
                if field not in fact:
                    logger.error(f"Fact missing required field: {field}")
                    return False

        return True


class ClaudeExtractor(LLMExtractor):
    """Extractor for Claude models via Anthropic API"""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize Claude extractor

        Args:
            api_key: Anthropic API key (defaults to config)
            model: Model name (defaults to config)
        """
        super().__init__()

        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic package not installed")

        self.api_key = api_key or APIConfig.ANTHROPIC_API_KEY
        self.model = model or APIConfig.CLAUDE_MODEL
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def extract(self, text: str, chunk_id: str = None) -> ExtractionResult:
        """
        Extract facts using Claude

        Args:
            text: Article text or chunk
            chunk_id: Optional chunk identifier

        Returns:
            ExtractionResult
        """

        logger.info(f"Claude extraction started for chunk: {chunk_id or 'full_article'}")

        prompt = PromptTemplates.CLAUDE_EXTRACTION_PROMPT.format(input_text=text)

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    temperature=0.0,  # Deterministic for fact extraction
                    messages=[
                        {"role": "user", "content": prompt}
                    ]
                )

                response_text = response.content[0].text

                # Parse JSON
                data = self._parse_json_response(response_text)
                if not data:
                    logger.warning(f"Claude attempt {attempt + 1}: JSON parsing failed")
                    continue

                # Validate schema
                if not self._validate_extraction_schema(data):
                    logger.warning(f"Claude attempt {attempt + 1}: Schema validation failed")
                    continue

                logger.info("Claude extraction successful")
                return ExtractionResult(
                    model_name="claude",
                    consensus_summary=data['consensus_summary'],
                    extracted_facts=data['extracted_facts'],
                    raw_response=response_text,
                    success=True,
                    metadata={
                        'chunk_id': chunk_id,
                        'model': self.model,
                        'usage': {
                            'input_tokens': response.usage.input_tokens,
                            'output_tokens': response.usage.output_tokens
                        }
                    }
                )

            except Exception as e:
                logger.error(f"Claude attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    return ExtractionResult(
                        model_name="claude",
                        consensus_summary="",
                        extracted_facts=[],
                        raw_response="",
                        success=False,
                        error_message=str(e)
                    )


class GeminiExtractor(LLMExtractor):
    """Extractor for Gemini models via Google Generative AI API"""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize Gemini extractor

        Args:
            api_key: Google API key (defaults to config)
            model: Model name (defaults to config)
        """
        super().__init__()

        if not GOOGLE_AVAILABLE:
            raise ImportError("google-generativeai package not installed")

        self.api_key = api_key or APIConfig.GOOGLE_API_KEY
        self.model_name = model or APIConfig.GEMINI_MODEL

        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)

    def extract(self, text: str, chunk_id: str = None) -> ExtractionResult:
        """
        Extract facts using Gemini

        Args:
            text: Article text or chunk
            chunk_id: Optional chunk identifier

        Returns:
            ExtractionResult
        """

        logger.info(f"Gemini extraction started for chunk: {chunk_id or 'full_article'}")

        prompt = PromptTemplates.GEMINI_EXTRACTION_PROMPT.format(input_text=text)

        for attempt in range(self.max_retries):
            try:
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.0,
                        'top_p': 0.95,
                        'max_output_tokens': 4096,
                    }
                )

                response_text = response.text

                # Parse JSON
                data = self._parse_json_response(response_text)
                if not data:
                    logger.warning(f"Gemini attempt {attempt + 1}: JSON parsing failed")
                    continue

                # Validate schema
                if not self._validate_extraction_schema(data):
                    logger.warning(f"Gemini attempt {attempt + 1}: Schema validation failed")
                    continue

                logger.info("Gemini extraction successful")
                return ExtractionResult(
                    model_name="gemini",
                    consensus_summary=data['consensus_summary'],
                    extracted_facts=data['extracted_facts'],
                    raw_response=response_text,
                    success=True,
                    metadata={
                        'chunk_id': chunk_id,
                        'model': self.model_name,
                        'usage': {
                            'prompt_tokens': response.usage_metadata.prompt_token_count if hasattr(response, 'usage_metadata') else None,
                            'output_tokens': response.usage_metadata.candidates_token_count if hasattr(response, 'usage_metadata') else None
                        }
                    }
                )

            except Exception as e:
                logger.error(f"Gemini attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    return ExtractionResult(
                        model_name="gemini",
                        consensus_summary="",
                        extracted_facts=[],
                        raw_response="",
                        success=False,
                        error_message=str(e)
                    )


class GPTExtractor(LLMExtractor):
    """Extractor for GPT models via OpenAI API (used for conflict resolution)"""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize GPT extractor

        Args:
            api_key: OpenAI API key (defaults to config)
            model: Model name (defaults to config)
        """
        super().__init__()

        if not OPENAI_AVAILABLE:
            raise ImportError("openai package not installed")

        self.api_key = api_key or APIConfig.OPENAI_API_KEY
        self.model = model or APIConfig.OPENAI_MODEL
        self.client = OpenAI(api_key=self.api_key)

    def resolve_conflicts(
        self,
        original_text: str,
        claude_output: Dict,
        gemini_output: Dict,
        conflicts: List[str]
    ) -> ExtractionResult:
        """
        Use GPT to resolve conflicts between Claude and Gemini outputs

        Args:
            original_text: Original article text
            claude_output: Claude's extraction result
            gemini_output: Gemini's extraction result
            conflicts: List of identified conflicts

        Returns:
            ExtractionResult with reconciled output
        """

        logger.info("GPT conflict resolution started")

        prompt = PromptTemplates.CONFLICT_RESOLUTION_PROMPT.format(
            input_text=original_text,
            claude_output=json.dumps(claude_output, indent=2),
            gemini_output=json.dumps(gemini_output, indent=2),
            conflicts='\n'.join(conflicts)
        )

        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a fact-checking arbitrator that resolves conflicts between AI outputs."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=4096
                )

                response_text = response.choices[0].message.content

                # Parse JSON
                data = self._parse_json_response(response_text)
                if not data:
                    logger.warning(f"GPT attempt {attempt + 1}: JSON parsing failed")
                    continue

                # Validate schema
                if not self._validate_extraction_schema(data):
                    logger.warning(f"GPT attempt {attempt + 1}: Schema validation failed")
                    continue

                logger.info("GPT conflict resolution successful")
                return ExtractionResult(
                    model_name="gpt_arbitrator",
                    consensus_summary=data['consensus_summary'],
                    extracted_facts=data['extracted_facts'],
                    raw_response=response_text,
                    success=True,
                    metadata={
                        'model': self.model,
                        'conflicts_resolved': len(conflicts),
                        'usage': {
                            'prompt_tokens': response.usage.prompt_tokens,
                            'completion_tokens': response.usage.completion_tokens,
                            'total_tokens': response.usage.total_tokens
                        }
                    }
                )

            except Exception as e:
                logger.error(f"GPT attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    return ExtractionResult(
                        model_name="gpt_arbitrator",
                        consensus_summary="",
                        extracted_facts=[],
                        raw_response="",
                        success=False,
                        error_message=str(e)
                    )


class ParallelExtractor:
    """Orchestrates parallel extraction with multiple LLMs"""

    def __init__(self):
        """Initialize parallel extractor with all models"""
        try:
            self.claude = ClaudeExtractor()
            logger.info("Claude extractor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Claude: {e}")
            self.claude = None

        try:
            self.gemini = GeminiExtractor()
            logger.info("Gemini extractor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            self.gemini = None

        try:
            self.gpt = GPTExtractor()
            logger.info("GPT extractor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GPT: {e}")
            self.gpt = None

    def extract_parallel(
        self,
        text: str,
        chunk_id: str = None
    ) -> Tuple[Optional[ExtractionResult], Optional[ExtractionResult]]:
        """
        Run Claude and Gemini extraction in parallel

        Args:
            text: Article text or chunk
            chunk_id: Optional chunk identifier

        Returns:
            Tuple of (Claude result, Gemini result)
        """

        logger.info("Starting parallel extraction with Claude and Gemini")

        if not PipelineConfig.PARALLEL_PROCESSING:
            # Sequential processing
            claude_result = self.claude.extract(text, chunk_id) if self.claude else None
            gemini_result = self.gemini.extract(text, chunk_id) if self.gemini else None
            return claude_result, gemini_result

        # Parallel processing using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = {}

            if self.claude:
                futures['claude'] = executor.submit(self.claude.extract, text, chunk_id)

            if self.gemini:
                futures['gemini'] = executor.submit(self.gemini.extract, text, chunk_id)

            results = {}
            for model, future in futures.items():
                try:
                    results[model] = future.result(timeout=self.claude.timeout if self.claude else 30)
                except Exception as e:
                    logger.error(f"{model} parallel extraction failed: {e}")
                    results[model] = None

            return results.get('claude'), results.get('gemini')
