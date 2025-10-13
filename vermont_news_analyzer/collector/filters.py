"""
Vermont Signal Content Filters
Filters for Vermont-related content and low-value content removal

Filters out:
- Obituaries and death notices
- Event calendars and listings
- Very short articles (< 200 chars)
- Reviews (movies, restaurants, books, music)
- Sports game coverage
- Classified ads and real estate listings
- Weather alerts and forecasts
- Community announcements
"""

import re
from typing import List, Tuple

# Vermont-related keywords and patterns for filtering regional sources
VERMONT_KEYWORDS: List[str] = [
    # State names
    r'\bvermont\b', r'\bvt\b', r'\bvt\.',

    # Major cities
    r'\bburlington\b', r'\bmontpelier\b', r'\brutland\b', r'\bbrattleboro\b',
    r'\bbarre\b', r'\bsouth burlington\b', r'\bcolchester\b', r'\bessex\b',
    r'\bwinooski\b', r'\bst\. albans\b', r'\bnewport\b', r'\bvergennes\b',

    # Regions
    r'\bnortheast kingdom\b', r'\bchamplain valley\b', r'\bgreen mountains\b',
    r'\bmad river valley\b', r'\bupper valley\b',

    # Counties
    r'\bchittenden county\b', r'\bwindham county\b', r'\bwindsor county\b',
    r'\bfranklin county\b', r'\brutland county\b', r'\borange county\b',

    # Notable locations
    r'\blake champlain\b', r'\bstowe\b', r'\bkillington\b', r'\bsugarbush\b',
    r'\bmarlboro\b', r'\bmiddlebury\b', r'\bbenning?ton\b', r'\bst\. johnsbury\b',
    r'\bwhite river junction\b', r'\bspringfield\b', r'\blyndon\b',
]


def is_vermont_related(text: str) -> bool:
    """
    Check if text contains Vermont-related keywords

    Used to filter regional/national news sources that may include
    non-Vermont content (e.g., Boston.com, regional TV stations)

    Args:
        text: Article title or summary to check

    Returns:
        True if Vermont-related, False otherwise
    """
    if not text:
        return False

    text_lower = text.lower()
    for keyword_pattern in VERMONT_KEYWORDS:
        if re.search(keyword_pattern, text_lower):
            return True

    return False


def is_obituary(title: str, summary: str = '') -> bool:
    """
    Check if article is an obituary or death notice

    Obituaries are filtered out as they don't provide relevant news
    facts for political/business/policy analysis.

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if obituary, False otherwise
    """
    if not title:
        return False

    text_lower = f"{title} {summary}".lower()
    title_lower = title.lower()

    # Obituary indicator patterns
    obit_patterns = [
        r'\bobituar(y|ies)\b',
        r'\bdeath notices?\b',
        r'\bin memoriam\b',
        r'\bpassed away\b',
        r'\bdied\b.*\b(age|years old)\b',
        r'\bservices? will be held\b',
        r'\bcelebration of life\b',
        r'\bmemorial service\b',
        r',\s*\d{2,3},?\s+\w+\s+native$',  # "Name, age, City native" pattern
    ]

    for pattern in obit_patterns:
        if re.search(pattern, text_lower):
            return True

    # "Name, age, of City" or "Name, age, City native" pattern
    # e.g., "John Smith, 75, of Burlington" or "Karen Bourdon Gorin, 72, Middlebury native"
    name_age_city_pattern = r'^[A-Z][\w\s]+,\s*\d+,?\s+(of\s+|.*\s+native)'
    if re.search(name_age_city_pattern, title):
        return True

    # "Name, age" pattern at end of title
    # e.g., "Barbara Fee Dickason, 93"
    name_age_pattern = r',\s*\d{2,3}(\s|$)'
    if re.search(name_age_pattern, title):
        return True

    # Name-only obituaries (common pattern: just a person's name, 2-4 words, no common news words)
    # This catches titles like "John Putnam" or "Elizabeth McGrath"
    words = title.strip().split()
    if 2 <= len(words) <= 4:
        # Check if it's just capitalized words (names) with no obvious news keywords
        news_keywords = [
            'court', 'state', 'town', 'school', 'police', 'fire', 'vote',
            'council', 'board', 'committee', 'mayor', 'governor', 'senator',
            'arrest', 'crash', 'accident', 'meeting', 'election', 'bill',
            'law', 'budget', 'tax', 'company', 'business', 'report', 'study'
        ]

        # Check if all words are capitalized (typical of names)
        all_capitalized = all(word[0].isupper() for word in words if word)
        has_news_keyword = any(keyword in title_lower for keyword in news_keywords)

        # If it's just capitalized names with no news keywords, likely an obituary
        if all_capitalized and not has_news_keyword:
            return True

    return False


def is_event_listing(title: str, summary: str = '') -> bool:
    """
    Check if article is an event calendar listing or community event

    Events are filtered out as they don't provide factual news analysis.

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if event listing, False otherwise
    """
    if not title:
        return False

    text_lower = f"{title} {summary}".lower()
    title_lower = title.lower()

    # Event indicator patterns
    event_patterns = [
        r'\bevent calendar\b',
        r'\bcommunity calendar\b',
        r'\bupcoming events?\b',
        r'\bthings to do\b',
        r'\bevents? this week(end)?\b',
        r'\bwhat\'?s happening\b',
        r'\bsave the date\b',
        r'\bmark your calendar\b',
        r'\bevent listings?\b',
        r'\bcommunity events?\b',
        r'\barts? & entertainment calendar\b',
    ]

    for pattern in event_patterns:
        if re.search(pattern, text_lower):
            return True

    # Date range patterns: "Events: June 15-20" or "This Weekend's Events"
    date_range_pattern = r'\bevents?:?\s+(this|next|june|july|august|september|october|november|december|january|february|march|april|may|\d+)'
    if re.search(date_range_pattern, title_lower):
        return True

    # "Happening this weekend" style titles
    happening_pattern = r'\bhappening (this|next|on) (week(end)?|month|saturday|sunday|friday)\b'
    if re.search(happening_pattern, title_lower):
        return True

    return False


def is_too_short(title: str, content: str, summary: str = '', min_length: int = 200) -> bool:
    """
    Check if article is too short to contain substantial news content

    Very short articles are often briefs, announcements, or fragments
    that don't provide enough context for fact extraction.

    Args:
        title: Article title
        content: Article content/text
        summary: Article summary
        min_length: Minimum character length (default 200)

    Returns:
        True if too short, False otherwise
    """
    # Use the longest available text
    text = content or summary or ''

    # Count actual text length (excluding whitespace)
    text_length = len(text.strip())

    return text_length < min_length


def is_review(title: str, summary: str = '') -> bool:
    """
    Check if article is a review (movie, book, restaurant, music, etc.)

    Reviews are opinion pieces that don't typically contain factual news.

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if review, False otherwise
    """
    if not title:
        return False

    text_lower = f"{title} {summary}".lower()
    title_lower = title.lower()

    # Review indicator patterns
    review_patterns = [
        r'\breview:',
        r'\breviewed\b',
        r'\bmovie review\b',
        r'\bbook review\b',
        r'\balbum review\b',
        r'\brestaurant review\b',
        r'\bfood review\b',
        r'\bfilm review\b',
        r'\bconcert review\b',
        r'\btheater review\b',
        r'\bplay review\b',
        r'\bart review\b',
        r'\bmusic review\b',
    ]

    for pattern in review_patterns:
        if re.search(pattern, text_lower):
            return True

    # Star rating patterns: "★★★★" or "4 stars" or "5/5"
    rating_patterns = [
        r'[★⭐]{2,5}',
        r'\b\d\s+stars?\b',
        r'\b\d/5\b',
        r'\b\d\.?\d?/10\b',
    ]

    for pattern in rating_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def is_sports_game(title: str, summary: str = '') -> bool:
    """
    Check if article is sports game coverage or scores

    Sports games are filtered unless they involve policy/politics.

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if sports game coverage, False otherwise
    """
    if not title:
        return False

    text_lower = f"{title} {summary}".lower()
    title_lower = title.lower()

    # Game score patterns: "Team 3, Team 2" or "Team beats Team" or "Team vs Team"
    score_patterns = [
        r'\b\d+\s*-\s*\d+\b',  # 3-2, 21-14
        r'\b\w+\s+\d+,\s+\w+\s+\d+\b',  # Team 3, Team 2
        r'\bvs\.?\s+',  # vs or vs.
        r'\bbeats?\b',  # beat, beats
        r'\bdefeats?\b',  # defeat, defeats
        r'\btops\b',  # tops (in sports context)
    ]

    # Only flag as sports if it contains sports keywords + score patterns
    sports_keywords = [
        'football', 'basketball', 'baseball', 'hockey', 'soccer',
        'game', 'playoff', 'championship', 'tournament', 'season',
        'score', 'final', 'overtime', 'quarter', 'inning', 'period'
    ]

    has_sports_keyword = any(keyword in text_lower for keyword in sports_keywords)

    if has_sports_keyword:
        for pattern in score_patterns:
            if re.search(pattern, text_lower):
                return True

    # Explicit game recap titles
    recap_patterns = [
        r'\bgame recap\b',
        r'\bgame notes?\b',
        r'\brecap:',
        r'\bscoreboard\b',
        r'\bgame summary\b',
        r'\bmatch report\b',
    ]

    for pattern in recap_patterns:
        if re.search(pattern, text_lower):
            return True

    return False


def is_classified_ad(title: str, summary: str = '') -> bool:
    """
    Check if article is a classified ad or listing

    Classifieds don't contain news content.

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if classified ad, False otherwise
    """
    if not title:
        return False

    text_lower = f"{title} {summary}".lower()
    title_lower = title.lower()

    # Classified patterns
    classified_patterns = [
        r'\bfor sale\b',
        r'\bfor rent\b',
        r'\bhelp wanted\b',
        r'\bjob opening\b',
        r'\bnow hiring\b',
        r'\breal estate\b',
        r'\bclassifieds?\b',
        r'\blistings?\b',
        r'\bpublic notice\b',
        r'\blegal notice\b',
        r'\bbid request\b',
        r'\brfp\b',  # Request for Proposal
    ]

    for pattern in classified_patterns:
        if re.search(pattern, text_lower):
            return True

    # Price patterns (likely listings): "$XX,XXX" or "$X.XX"
    price_pattern = r'\$[\d,]+(\.\d{2})?'
    if re.search(price_pattern, title):
        # Check if it's a listing-style title
        listing_keywords = ['sale', 'rent', 'bed', 'bath', 'acre', 'sqft']
        if any(keyword in title_lower for keyword in listing_keywords):
            return True

    return False


def is_weather_alert(title: str, summary: str = '') -> bool:
    """
    Check if article is a weather alert or forecast

    Weather alerts don't contain policy/political news.

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if weather alert, False otherwise
    """
    if not title:
        return False

    text_lower = f"{title} {summary}".lower()
    title_lower = title.lower()

    # Weather alert patterns
    weather_patterns = [
        r'\bweather forecast\b',
        r'\bforecast:',
        r'\bweather alert\b',
        r'\bweather warning\b',
        r'\bstorm watch\b',
        r'\bwinter storm\b',
        r'\bflood watch\b',
        r'\bsevere weather\b',
        r'\btoday\'?s weather\b',
        r'\bweather update\b',
        r'\b7-day forecast\b',
        r'\bextended forecast\b',
    ]

    for pattern in weather_patterns:
        if re.search(pattern, text_lower):
            return True

    # Temperature patterns in title: "High of 75°" or "Temps in the 60s"
    temp_pattern = r'(high|low|temp|temperature)s?\s+(of|in)\s+\d+°?'
    if re.search(temp_pattern, title_lower):
        return True

    return False


def should_filter_article(
    title: str,
    content: str = '',
    summary: str = '',
    min_length: int = 200
) -> Tuple[bool, str]:
    """
    Master filter function - checks all low-value content filters

    Args:
        title: Article title
        content: Article content/text
        summary: Article summary
        min_length: Minimum character length for articles

    Returns:
        Tuple of (should_filter: bool, reason: str)
        - should_filter: True if article should be filtered out
        - reason: Human-readable reason for filtering
    """
    if not title:
        return True, "missing_title"

    # Check each filter in order
    if is_obituary(title, summary):
        return True, "obituary"

    if is_event_listing(title, summary):
        return True, "event_listing"

    if is_review(title, summary):
        return True, "review"

    if is_sports_game(title, summary):
        return True, "sports_game"

    if is_classified_ad(title, summary):
        return True, "classified_ad"

    if is_weather_alert(title, summary):
        return True, "weather_alert"

    if is_too_short(title, content, summary, min_length):
        return True, "too_short"

    return False, "passed"
