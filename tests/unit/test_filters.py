"""
Unit tests for Vermont Signal content filters

Tests all filter functions for correct behavior on edge cases and typical inputs.
Filters are critical for data quality, so comprehensive testing is essential.
"""

import pytest
from vermont_news_analyzer.collector.filters import (
    is_obituary,
    is_new_hampshire_article,
    is_vermont_related,
    is_event_listing,
    is_too_short,
    is_review,
    is_sports_game,
    is_classified_ad,
    is_weather_alert,
    should_filter_article,
    contains_policy_keywords,
    POLICY_WHITELIST
)


# ============================================================================
# OBITUARY FILTER TESTS
# ============================================================================

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
    def test_name_age_pattern(self):
        """Should detect 'Name, Age' obituary pattern"""
        assert is_obituary("John Smith, 75") is True
        assert is_obituary("Mary Johnson, 82, of Burlington") is True
        assert is_obituary("Karen Bourdon Gorin, 72, Middlebury native") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_death_notices(self):
        """Should detect death notice patterns"""
        assert is_obituary("Death notice: John Putnam") is True
        assert is_obituary("In memoriam: Jane Doe") is True
        assert is_obituary("Celebration of life for Sarah Smith") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_passed_away_pattern(self):
        """Should detect 'passed away' language"""
        assert is_obituary("Local man passed away at age 65") is True
        assert is_obituary("Mary Smith passed away peacefully") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_obituary_with_age(self):
        """Should NOT flag news articles that mention age"""
        # News about someone who is alive
        assert is_obituary("Governor, 58, signs new climate bill") is False
        assert is_obituary("Senator John Smith, 65, proposes tax reform") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_name_only_obituary(self):
        """Should detect name-only obituaries (2-4 words, no news keywords)"""
        assert is_obituary("John Putnam") is True
        assert is_obituary("Elizabeth McGrath") is True
        assert is_obituary("Barbara Fee Dickason") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_obituary_with_news_keywords(self):
        """Should NOT flag articles with political/news keywords"""
        assert is_obituary("Governor Scott announces") is False
        assert is_obituary("Mayor Smith proposes budget") is False
        assert is_obituary("Senator Sanders introduces bill") is False


# ============================================================================
# NEW HAMPSHIRE FILTER TESTS
# ============================================================================

class TestNewHampshireFilter:
    """Test NH article filtering"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_explicit_nh_keyword(self):
        """Should detect explicit New Hampshire mentions"""
        assert is_new_hampshire_article("New Hampshire governor signs bill") is True
        assert is_new_hampshire_article("Manchester NH police report") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_nh_cities(self):
        """Should detect NH cities"""
        assert is_new_hampshire_article("Manchester school board meeting") is True
        assert is_new_hampshire_article("Portsmouth developer plans project") is True
        assert is_new_hampshire_article("Nashua city council votes") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_border_stories_not_filtered(self):
        """Should NOT filter border stories mentioning both VT and NH"""
        # These should NOT be filtered (Vermont is mentioned)
        assert is_new_hampshire_article("Vermont and New Hampshire agree on border policy") is False
        assert is_new_hampshire_article("VT-NH partnership announced") is False
        assert is_new_hampshire_article("Vermont governor meets with NH counterpart") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_nh_abbreviation_edge_cases(self):
        """Should handle NH abbreviation carefully"""
        # This is tricky - "NH" could be middle initial
        # Current implementation may flag false positives
        text = "John NH Smith speaks"
        # Document expected behavior (may need refinement)
        result = is_new_hampshire_article(text)
        # If this fails, consider improving regex to avoid middle initials


# ============================================================================
# VERMONT RELATED FILTER TESTS
# ============================================================================

class TestVermontRelatedFilter:
    """Test Vermont relevance detection"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_explicit_vermont_keyword(self):
        """Should detect explicit Vermont mentions"""
        assert is_vermont_related("Vermont legislature passes bill") is True
        assert is_vermont_related("VT climate policy announced") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_vermont_cities(self):
        """Should detect Vermont cities"""
        assert is_vermont_related("Burlington mayor announces") is True
        assert is_vermont_related("Montpelier capitol building") is True
        assert is_vermont_related("Rutland development project") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_vermont_regions(self):
        """Should detect Vermont regions"""
        assert is_vermont_related("Northeast Kingdom farmers") is True
        assert is_vermont_related("Champlain Valley housing") is True
        assert is_vermont_related("Green Mountains tourism") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_vermont_related(self):
        """Should NOT detect non-Vermont content"""
        assert is_vermont_related("National news story") is False
        assert is_vermont_related("Boston mayor announces") is False


# ============================================================================
# EVENT LISTING FILTER TESTS
# ============================================================================

class TestEventListingFilter:
    """Test event listing detection"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_event_calendar_keywords(self):
        """Should detect event calendar language"""
        assert is_event_listing("Community calendar for October") is True
        assert is_event_listing("Upcoming events this weekend") is True
        assert is_event_listing("Things to do in Burlington") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_event_date_range(self):
        """Should detect date range event titles"""
        assert is_event_listing("Events: October 15-20") is True
        assert is_event_listing("This weekend's events") is True
        assert is_event_listing("Happening this Friday") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_event_listing(self):
        """Should NOT flag news about events"""
        # News ABOUT an event, not a listing
        assert is_event_listing("Governor announces infrastructure plan") is False
        assert is_event_listing("Concert raises funds for charity") is False


# ============================================================================
# TOO SHORT FILTER TESTS
# ============================================================================

class TestTooShortFilter:
    """Test minimum word count requirements"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_very_short_content(self):
        """Should filter very short articles (< 50 words)"""
        title = "Short Title"
        content = "This is too short."  # Only 4 words
        assert is_too_short(title, content) is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_adequate_word_count(self):
        """Should NOT filter articles with adequate word count (>= 50 words)"""
        title = "Vermont Legislature Passes Climate Bill"
        # Create content with exactly 50 words
        content = " ".join(["word"] * 50)
        assert is_too_short(title, content, min_words=50) is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_uses_summary_if_no_content(self):
        """Should use summary if content is missing"""
        title = "Title"
        content = ""
        # Create summary with 60 words
        summary = " ".join(["word"] * 60)
        assert is_too_short(title, content, summary, min_words=50) is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_strips_html_tags_before_word_count(self):
        """Should strip HTML tags before counting words"""
        title = "CLAWS"
        # Content with HTML tags - only 8 words of actual text
        content = '<p>All this cuz of a faulty inspection sticker</p>\n\n<figure class="wp-block-image size-large"><img alt="" class="wp-image-268440" height="1024" src="https://example.com/image.png" width="831" /></figure>'
        # Should be filtered as too short (8 words < 50 words)
        assert is_too_short(title, content, min_words=50) is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_adequate_text_with_html_tags(self):
        """Should NOT filter articles with adequate words even with HTML tags"""
        title = "Vermont Legislature Passes Climate Bill"
        # Content with HTML tags but enough words (60 words)
        words = " ".join(["word"] * 60)
        content = f'<p>{words}</p><div>More content here</div>'
        assert is_too_short(title, content, min_words=50) is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_word_count_more_reliable_than_char_count(self):
        """Word count should be more consistent than character count"""
        # 10 long words (100+ chars) vs 50 short words (100+ chars)
        long_words = " ".join(["antidisestablishmentarianism"] * 10)  # 10 words, 280 chars
        short_words = " ".join(["hi"] * 50)  # 50 words, 150 chars

        # Long words but low count - should filter
        assert is_too_short("Title", long_words, min_words=50) is True

        # Short words but good count - should NOT filter
        assert is_too_short("Title", short_words, min_words=50) is False


# ============================================================================
# REVIEW FILTER TESTS
# ============================================================================

class TestReviewFilter:
    """Test review detection"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_explicit_review_keyword(self):
        """Should detect explicit 'review' keyword"""
        assert is_review("Movie review: New film released") is True
        assert is_review("Book review: Latest bestseller") is True
        assert is_review("Restaurant review: New Burlington eatery") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_star_ratings(self):
        """Should detect star rating patterns"""
        assert is_review("Great restaurant ★★★★★") is True
        assert is_review("Movie gets 4 stars") is True
        assert is_review("Album rated 8/10") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_review(self):
        """Should NOT flag news articles"""
        assert is_review("Governor reviews budget proposal") is False
        assert is_review("Board reviews zoning application") is False


# ============================================================================
# SPORTS GAME FILTER TESTS
# ============================================================================

class TestSportsGameFilter:
    """Test sports game coverage detection"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_game_scores(self):
        """Should detect game score patterns"""
        assert is_sports_game("Patriots 21, Jets 14") is True
        assert is_sports_game("Vermont defeats New Hampshire 3-2 in hockey") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_game_recap_keywords(self):
        """Should detect game recap language"""
        assert is_sports_game("Game recap: Catamounts win championship") is True
        assert is_sports_game("Basketball scoreboard for Friday") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_sports_game(self):
        """Should NOT flag non-sports content"""
        assert is_sports_game("Governor beats legislative deadline") is False
        assert is_sports_game("School board defeats budget proposal") is False


# ============================================================================
# CLASSIFIED AD FILTER TESTS
# ============================================================================

class TestClassifiedAdFilter:
    """Test classified ad detection"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_for_sale_listings(self):
        """Should detect for sale/rent listings"""
        assert is_classified_ad("House for sale in Burlington") is True
        assert is_classified_ad("Apartment for rent, 2 bed 1 bath") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_job_listings(self):
        """Should detect job postings"""
        assert is_classified_ad("Help wanted: Restaurant server") is True
        assert is_classified_ad("Now hiring: Retail positions") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_legal_notices(self):
        """Should detect legal/public notices"""
        assert is_classified_ad("Public notice: Zoning hearing") is True
        assert is_classified_ad("Legal notice: Estate sale") is True


# ============================================================================
# WEATHER FILTER TESTS
# ============================================================================

class TestWeatherAlertFilter:
    """Test weather alert detection"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_weather_forecast_keywords(self):
        """Should detect weather forecast language"""
        assert is_weather_alert("Today's weather forecast") is True
        assert is_weather_alert("7-day forecast for Burlington") is True
        assert is_weather_alert("Winter storm watch issued") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_temperature_patterns(self):
        """Should detect temperature mentions"""
        assert is_weather_alert("High of 75 degrees today") is True
        assert is_weather_alert("Temps in the 60s expected") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_not_climate_policy(self):
        """Should NOT filter climate policy articles"""
        # This is a known edge case - climate policy might get filtered
        # Document expected behavior
        assert is_weather_alert("Vermont climate policy targets emissions") is False
        assert is_weather_alert("Carbon tax proposal debated") is False


# ============================================================================
# MASTER FILTER TESTS
# ============================================================================

class TestMasterFilter:
    """Test the master should_filter_article function"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_filter_returns_reason(self):
        """Should return tuple with (should_filter, reason)"""
        should_filter, reason = should_filter_article("John Smith, 75", "Brief content")
        assert should_filter is True
        assert reason == "obituary"

    @pytest.mark.unit
    @pytest.mark.filter
    def test_passes_valid_article(self):
        """Should pass valid Vermont news articles"""
        title = "Vermont Legislature Passes Climate Bill"
        content = "A" * 300  # Adequate length
        should_filter, reason = should_filter_article(title, content)
        assert should_filter is False
        assert reason == "passed"

    @pytest.mark.unit
    @pytest.mark.filter
    def test_filter_priority_order(self):
        """Should apply filters in correct priority order"""
        # NH filter should come before obituary filter
        title = "New Hampshire obituary: John Smith"
        should_filter, reason = should_filter_article(title, "A" * 300)
        assert should_filter is True
        assert reason == "new_hampshire_article"

    @pytest.mark.unit
    @pytest.mark.filter
    def test_missing_title(self):
        """Should filter articles with missing title"""
        should_filter, reason = should_filter_article("", "content here")
        assert should_filter is True
        assert reason == "missing_title"


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestFilterEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_empty_strings(self):
        """Should handle empty strings gracefully"""
        assert is_obituary("") is False
        assert is_new_hampshire_article("") is False
        assert is_event_listing("") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_none_values(self):
        """Should handle None values gracefully"""
        assert is_obituary(None) is False
        assert is_new_hampshire_article(None) is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_unicode_content(self):
        """Should handle unicode characters"""
        assert is_obituary("John Smith, 75, célébration de vie") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_case_insensitivity(self):
        """Should be case-insensitive"""
        assert is_obituary("OBITUARY: JOHN SMITH") is True
        assert is_new_hampshire_article("new hampshire") is True
        assert is_event_listing("UPCOMING EVENTS") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_whitespace_handling(self):
        """Should handle extra whitespace"""
        assert is_obituary("  Obituary:  John  Smith  ") is True
        assert is_event_listing("\n\nEvent Calendar\n\n") is True


# ============================================================================
# POLICY WHITELIST TESTS (NEW - October 2025)
# ============================================================================

class TestPolicyWhitelist:
    """Test policy whitelist functionality for preventing false positives"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_policy_whitelist_exists(self):
        """Should have policy whitelist defined"""
        assert POLICY_WHITELIST is not None
        assert len(POLICY_WHITELIST) > 0
        assert isinstance(POLICY_WHITELIST, list)

    @pytest.mark.unit
    @pytest.mark.filter
    def test_contains_policy_keywords_legislative_terms(self):
        """Should detect legislative/government keywords"""
        assert contains_policy_keywords("Senate passes new climate bill") is True
        assert contains_policy_keywords("Legislature debates housing legislation") is True
        assert contains_policy_keywords("Governor signs carbon tax law") is True
        assert contains_policy_keywords("House amendment proposed") is True
        assert contains_policy_keywords("Act 250 reform statute") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_contains_policy_keywords_climate_policy(self):
        """Should detect climate policy (not weather)"""
        assert contains_policy_keywords("Vermont climate action plan unveiled") is True
        assert contains_policy_keywords("Carbon pricing legislation proposed") is True
        assert contains_policy_keywords("Climate bill passes committee") is True
        assert contains_policy_keywords("Carbon tax debate continues") is True
        assert contains_policy_keywords("Emissions reduction policy approved") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_contains_policy_keywords_sports_policy(self):
        """Should detect sports policy (not game coverage)"""
        assert contains_policy_keywords("Stadium funding proposal approved") is True
        assert contains_policy_keywords("Sports betting legislation debated") is True
        assert contains_policy_keywords("Arena bond proposal passes") is True
        assert contains_policy_keywords("Sports wagering law signed") is True
        assert contains_policy_keywords("Facility construction plan unveiled") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_contains_policy_keywords_budget_financial(self):
        """Should detect budget and financial policy"""
        assert contains_policy_keywords("State budget proposal released") is True
        assert contains_policy_keywords("Tax policy reform debated") is True
        assert contains_policy_keywords("Appropriations bill passes") is True
        assert contains_policy_keywords("Revenue forecast updated") is True
        assert contains_policy_keywords("Spending plan approved") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_contains_policy_keywords_education_housing(self):
        """Should detect education and housing policy"""
        assert contains_policy_keywords("Education funding bill introduced") is True
        assert contains_policy_keywords("School voucher legislation debated") is True
        assert contains_policy_keywords("Housing affordability plan proposed") is True
        assert contains_policy_keywords("Zoning reform ordinance approved") is True
        assert contains_policy_keywords("Rent control policy discussed") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_contains_policy_keywords_negative_cases(self):
        """Should NOT detect non-policy content"""
        assert contains_policy_keywords("Today's weather forecast") is False
        assert contains_policy_keywords("Patriots win game 21-14") is False
        assert contains_policy_keywords("Restaurant review: Great pizza") is False
        assert contains_policy_keywords("Local man celebrates birthday") is False
        assert contains_policy_keywords("Concert this weekend") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_contains_policy_keywords_empty_none(self):
        """Should handle empty/None values gracefully"""
        assert contains_policy_keywords("") is False
        assert contains_policy_keywords(None) is False


class TestClimateWeatherDistinction:
    """Test distinction between climate policy and weather alerts"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_climate_policy_not_filtered_as_weather(self):
        """Climate policy articles should NOT be filtered as weather"""
        # These should NOT be weather alerts (policy content)
        assert is_weather_alert("Vermont climate action plan targets 2030 emissions") is False
        assert is_weather_alert("Legislature debates carbon pricing legislation") is False
        assert is_weather_alert("Climate bill includes renewable energy mandates") is False
        assert is_weather_alert("Governor signs climate policy into law") is False
        assert is_weather_alert("Carbon tax proposal advances in committee") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_weather_forecasts_still_filtered(self):
        """Weather forecasts should still be filtered"""
        # These SHOULD be weather alerts (not policy)
        assert is_weather_alert("Today's forecast: Sunny with high of 75") is True
        assert is_weather_alert("Winter storm watch issued for Vermont") is True
        assert is_weather_alert("7-day weather outlook") is True
        assert is_weather_alert("High temperatures expected this weekend") is True
        assert is_weather_alert("Flood watch in effect") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_climate_change_reporting_not_filtered(self):
        """Climate change news should NOT be filtered as weather"""
        assert is_weather_alert("Climate change impacts Vermont agriculture study") is False
        assert is_weather_alert("Global warming trends threaten ski industry") is False
        assert is_weather_alert("Climate science research funding approved") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_environmental_policy_not_filtered(self):
        """Environmental policy should NOT be filtered as weather"""
        assert is_weather_alert("Emissions reduction targets set by legislature") is False
        assert is_weather_alert("Clean energy legislation passes senate") is False
        assert is_weather_alert("Renewable energy mandate approved") is False
        assert is_weather_alert("Environmental protection law amended") is False


class TestNHMiddleInitialFix:
    """Test NH detection doesn't flag middle initials"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_nh_middle_initial_not_flagged(self):
        """Should NOT flag NH as middle initial"""
        # These should NOT be flagged as NH articles
        assert is_new_hampshire_article("John NH Smith speaks at event") is False
        assert is_new_hampshire_article("Governor Mike NH Doenges") is False
        assert is_new_hampshire_article("Mary NH Johnson appointed") is False
        assert is_new_hampshire_article("Senator Tom NH Williams") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_nh_state_abbreviation_flagged(self):
        """Should flag actual NH state abbreviation"""
        # These SHOULD be flagged as NH articles
        assert is_new_hampshire_article("Manchester, N.H. mayor announces") is True
        assert is_new_hampshire_article("NH governor signs bill") is True
        assert is_new_hampshire_article("Legislation in NH advances") is True
        assert is_new_hampshire_article("Portsmouth, NH development") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_nh_in_context_flagged(self):
        """Should flag NH in clear geographic/political context"""
        # These SHOULD be flagged
        assert is_new_hampshire_article("NH legislature votes on budget") is True
        assert is_new_hampshire_article("from NH seacoast region") is True
        assert is_new_hampshire_article("across NH state line") is True
        assert is_new_hampshire_article("NH voters approve measure") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_vt_nh_border_stories_not_flagged(self):
        """Should NOT flag VT-NH border stories"""
        # These should NOT be flagged (Vermont mentioned)
        assert is_new_hampshire_article("Vermont and NH sign agreement") is False
        assert is_new_hampshire_article("VT-NH border crossing opens") is False
        assert is_new_hampshire_article("Vermont governor meets NH counterpart") is False


class TestSportsPolicyDistinction:
    """Test distinction between sports policy and game coverage"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_sports_policy_not_filtered(self):
        """Sports policy articles should NOT be filtered as games"""
        # These should NOT be sports games (policy content)
        assert is_sports_game("Legislature debates stadium funding proposal") is False
        assert is_sports_game("Sports betting legalization bill advances") is False
        assert is_sports_game("Arena construction bond approved") is False
        assert is_sports_game("Sports wagering law implementation begins") is False
        assert is_sports_game("Facility funding plan unveiled") is False

    @pytest.mark.unit
    @pytest.mark.filter
    def test_game_coverage_still_filtered(self):
        """Game coverage should still be filtered"""
        # These SHOULD be sports games (not policy)
        assert is_sports_game("Patriots 21, Jets 14 final score") is True
        assert is_sports_game("Catamounts win championship game") is True
        assert is_sports_game("Basketball scoreboard: Friday results") is True
        assert is_sports_game("Vermont defeats UNH 3-2 in hockey") is True
        assert is_sports_game("Game recap: Thrilling overtime victory") is True

    @pytest.mark.unit
    @pytest.mark.filter
    def test_sports_business_not_filtered(self):
        """Sports business/economics should NOT be filtered"""
        assert is_sports_game("Professional team ownership dispute") is False
        assert is_sports_game("Stadium economic impact study released") is False
        assert is_sports_game("Sports franchise tax incentives debated") is False


class TestPolicyWhitelistIntegration:
    """Test policy whitelist integration with master filter"""

    @pytest.mark.unit
    @pytest.mark.filter
    def test_climate_policy_passes_master_filter(self):
        """Climate policy should pass through master filter"""
        title = "Vermont Legislature Passes Landmark Climate Action Bill"
        content = "The Vermont legislature voted 85-65 to approve comprehensive climate legislation targeting carbon emissions reduction by 2030. The bill includes carbon pricing mechanisms and renewable energy mandates."
        should_filter, reason = should_filter_article(title, content)
        # Should NOT be filtered (is policy, not weather)
        assert should_filter is False
        assert reason == "passed"

    @pytest.mark.unit
    @pytest.mark.filter
    def test_sports_policy_passes_master_filter(self):
        """Sports policy should pass through master filter"""
        title = "Legislature Approves $150M Stadium Funding Proposal"
        content = "The state legislature approved a controversial stadium funding proposal yesterday, allocating $150 million in public funds for a new multi-use sports facility in Burlington. The legislation passed after months of debate."
        should_filter, reason = should_filter_article(title, content)
        # Should NOT be filtered (is policy, not game coverage)
        assert should_filter is False
        assert reason == "passed"

    @pytest.mark.unit
    @pytest.mark.filter
    def test_weather_forecast_still_filtered(self):
        """Weather forecasts should still be filtered"""
        title = "Today's Weather Forecast: Sunny and Warm"
        content = "Expect sunny skies and high temperatures in the mid-70s today across Vermont. The 7-day outlook shows continued pleasant weather through the weekend."
        should_filter, reason = should_filter_article(title, content)
        # Should be filtered (weather forecast)
        assert should_filter is True
        assert reason == "weather_alert"

    @pytest.mark.unit
    @pytest.mark.filter
    def test_game_coverage_still_filtered(self):
        """Game coverage should still be filtered"""
        title = "Catamounts Defeat UNH 3-2 in Overtime Thriller"
        content = "The Vermont Catamounts secured a dramatic 3-2 overtime victory against the University of New Hampshire last night. Game recap and highlights inside."
        should_filter, reason = should_filter_article(title, content)
        # Should be filtered (game coverage)
        assert should_filter is True
        assert reason == "sports_game"
