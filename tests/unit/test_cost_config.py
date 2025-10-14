"""
Unit tests for CostConfig cost calculation logic

Tests the centralized cost configuration and calculation methods.
"""

import pytest
from vermont_news_analyzer.config import CostConfig


class TestCostConfig:
    """Test CostConfig cost calculations"""

    @pytest.mark.unit
    def test_cost_constants_defined(self):
        """Should have all required cost constants"""
        assert CostConfig.CLAUDE_INPUT_COST == 3.00
        assert CostConfig.CLAUDE_OUTPUT_COST == 15.00
        assert CostConfig.GEMINI_INPUT_COST == 0.075
        assert CostConfig.GEMINI_OUTPUT_COST == 0.30
        assert CostConfig.GPT_INPUT_COST == 0.15
        assert CostConfig.GPT_OUTPUT_COST == 0.60

    @pytest.mark.unit
    def test_budget_caps_defined(self):
        """Should have budget cap constants"""
        assert CostConfig.MONTHLY_BUDGET_CAP > 0
        assert CostConfig.DAILY_BUDGET_CAP > 0
        assert CostConfig.MONTHLY_BUDGET_CAP > CostConfig.DAILY_BUDGET_CAP

    @pytest.mark.unit
    def test_calculate_article_cost_basic(self):
        """Should calculate cost for one article"""
        input_tokens = 1000
        output_tokens = 500

        costs = CostConfig.calculate_article_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            include_arbitration=False
        )

        # Check structure
        assert 'claude' in costs
        assert 'gemini' in costs
        assert 'gpt' in costs
        assert 'total' in costs

        # Claude cost should be highest (most expensive per token)
        assert costs['claude'] > costs['gemini']
        assert costs['claude'] > costs['gpt']

        # Total should equal sum
        assert costs['total'] == costs['claude'] + costs['gemini'] + costs['gpt']

    @pytest.mark.unit
    def test_calculate_article_cost_with_arbitration(self):
        """Should include GPT arbitration cost when enabled"""
        input_tokens = 1000
        output_tokens = 500

        costs_with = CostConfig.calculate_article_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            include_arbitration=True
        )

        costs_without = CostConfig.calculate_article_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            include_arbitration=False
        )

        # With arbitration should cost more
        assert costs_with['gpt'] > costs_without['gpt']
        assert costs_with['total'] > costs_without['total']

        # GPT cost with arbitration should be ~30% of full cost
        full_gpt_cost = (
            (input_tokens * CostConfig.GPT_INPUT_COST / 1_000_000) +
            (output_tokens * CostConfig.GPT_OUTPUT_COST / 1_000_000)
        )
        expected_gpt = full_gpt_cost * CostConfig.ARBITRATION_FREQUENCY
        assert abs(costs_with['gpt'] - expected_gpt) < 0.0001

    @pytest.mark.unit
    def test_calculate_article_cost_zero_tokens(self):
        """Should handle zero tokens gracefully"""
        costs = CostConfig.calculate_article_cost(
            input_tokens=0,
            output_tokens=0
        )

        assert costs['claude'] == 0.0
        assert costs['gemini'] == 0.0
        assert costs['gpt'] == 0.0
        assert costs['total'] == 0.0

    @pytest.mark.unit
    def test_get_model_costs_anthropic(self):
        """Should return Claude costs for anthropic provider"""
        costs = CostConfig.get_model_costs('anthropic')

        assert costs['input'] == CostConfig.CLAUDE_INPUT_COST
        assert costs['output'] == CostConfig.CLAUDE_OUTPUT_COST

    @pytest.mark.unit
    def test_get_model_costs_google(self):
        """Should return Gemini costs for google provider"""
        costs = CostConfig.get_model_costs('google')

        assert costs['input'] == CostConfig.GEMINI_INPUT_COST
        assert costs['output'] == CostConfig.GEMINI_OUTPUT_COST

    @pytest.mark.unit
    def test_get_model_costs_openai(self):
        """Should return GPT costs for openai provider"""
        costs = CostConfig.get_model_costs('openai')

        assert costs['input'] == CostConfig.GPT_INPUT_COST
        assert costs['output'] == CostConfig.GPT_OUTPUT_COST

    @pytest.mark.unit
    def test_get_model_costs_invalid_provider(self):
        """Should return zeros for invalid provider"""
        costs = CostConfig.get_model_costs('invalid_provider')

        assert costs['input'] == 0.0
        assert costs['output'] == 0.0

    @pytest.mark.unit
    def test_realistic_article_cost(self):
        """Should calculate realistic cost for typical article"""
        # Typical article: 4000 chars = ~1000 tokens
        article_length = 4000
        input_tokens = article_length // 4
        output_tokens = 500

        costs = CostConfig.calculate_article_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            include_arbitration=True
        )

        # Total cost should be reasonable (< $0.02 per article)
        assert costs['total'] < 0.02

        # Cost breakdown should be reasonable
        # Claude is most expensive
        assert costs['claude'] > 0.01
        # Gemini is cheapest
        assert costs['gemini'] < 0.001

    @pytest.mark.unit
    def test_cost_per_million_tokens(self):
        """Should match advertised pricing per 1M tokens"""
        # Process 1 million tokens
        input_tokens = 1_000_000
        output_tokens = 1_000_000

        costs = CostConfig.calculate_article_cost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            include_arbitration=False
        )

        # Claude: $3 input + $15 output = $18 total
        expected_claude = CostConfig.CLAUDE_INPUT_COST + CostConfig.CLAUDE_OUTPUT_COST
        assert abs(costs['claude'] - expected_claude) < 0.01

        # Gemini: $0.075 input + $0.30 output = $0.375 total
        expected_gemini = CostConfig.GEMINI_INPUT_COST + CostConfig.GEMINI_OUTPUT_COST
        assert abs(costs['gemini'] - expected_gemini) < 0.01

    @pytest.mark.unit
    def test_arbitration_frequency(self):
        """Should use correct arbitration frequency"""
        assert CostConfig.ARBITRATION_FREQUENCY == 0.30
        assert 0 < CostConfig.ARBITRATION_FREQUENCY < 1.0


class TestCostEstimation:
    """Test cost estimation scenarios"""

    @pytest.mark.unit
    def test_daily_budget_articles(self):
        """Should calculate how many articles fit in daily budget"""
        # Average article cost
        input_tokens = 1000
        output_tokens = 500
        article_cost = CostConfig.calculate_article_cost(
            input_tokens, output_tokens, include_arbitration=True
        )['total']

        # How many articles in daily budget?
        articles_per_day = int(CostConfig.DAILY_BUDGET_CAP / article_cost)

        # Should be reasonable (50-200 articles/day)
        assert 50 <= articles_per_day <= 200

    @pytest.mark.unit
    def test_monthly_budget_articles(self):
        """Should calculate how many articles fit in monthly budget"""
        # Average article cost
        input_tokens = 1000
        output_tokens = 500
        article_cost = CostConfig.calculate_article_cost(
            input_tokens, output_tokens, include_arbitration=True
        )['total']

        # How many articles in monthly budget?
        articles_per_month = int(CostConfig.MONTHLY_BUDGET_CAP / article_cost)

        # Should be reasonable (1500-6000 articles/month)
        assert 1500 <= articles_per_month <= 6000

    @pytest.mark.unit
    def test_cost_scales_linearly(self):
        """Should scale cost linearly with token count"""
        small_cost = CostConfig.calculate_article_cost(
            input_tokens=100,
            output_tokens=50,
            include_arbitration=False
        )['total']

        large_cost = CostConfig.calculate_article_cost(
            input_tokens=1000,
            output_tokens=500,
            include_arbitration=False
        )['total']

        # Large should be ~10x small (linear scaling)
        ratio = large_cost / small_cost
        assert 9 < ratio < 11  # Allow some floating point variance
