"""
Vermont Signal RSS Collector Module
Collects Vermont news from RSS feeds and prepares for multi-model analysis
"""

from .rss_collector import RSSCollector
from .content_extractor import ContentExtractor
from .feeds import RSS_FEEDS, FILTERED_FEEDS, SOURCE_MAPPING
from .filters import (
    is_vermont_related,
    is_obituary,
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

__all__ = [
    'RSSCollector',
    'ContentExtractor',
    'RSS_FEEDS',
    'FILTERED_FEEDS',
    'SOURCE_MAPPING',
    'is_vermont_related',
    'is_obituary',
    'is_event_listing',
    'is_too_short',
    'is_review',
    'is_sports_game',
    'is_classified_ad',
    'is_weather_alert',
    'should_filter_article',
    'contains_policy_keywords',
    'POLICY_WHITELIST'
]
