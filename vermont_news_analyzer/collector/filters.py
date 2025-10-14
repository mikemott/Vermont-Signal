"""
Vermont Signal Content Filters
Filters for Vermont-related content and low-value content removal

Filters out:
- New Hampshire articles (non-Vermont content)
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

# New Hampshire keywords to filter out non-Vermont articles
NEW_HAMPSHIRE_KEYWORDS: List[str] = [
    r'\bnew hampshire\b', r'\bnh\b', r'\bn\.h\.\b',

    # Major NH cities
    r'\bmanchester\b', r'\bnashua\b', r'\bconcord\b', r'\bdover\b',
    r'\brochester\b', r'\bsalem\b', r'\bmerrimack\b', r'\bhudson\b',
    r'\blondonderry\b', r'\bderry\b', r'\bkeene\b', r'\bportsmouth\b',
    r'\blaconia\b', r'\bclaremont\b', r'\blebanon\b', r'\bfranconia\b',

    # NH Regions
    r'\bwhite mountains\b', r'\blakes region\b', r'\bmonadnock region\b',
    r'\bseacoast\b.*\bnh\b', r'\bnh seacoast\b',
]

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

# Policy/Political keywords that should NEVER be filtered (WHITELIST)
# These keywords indicate newsworthy political/policy content
POLICY_WHITELIST: List[str] = [
    # Legislative terms
    r'\b(bill|legislation|statute|law|act|resolution|amendment)\b',
    r'\b(legislature|senate|house|assembly|congress)\b',
    r'\b(committee|subcommittee|caucus|commission)\b',

    # Government actions
    r'\b(policy|regulation|ordinance|rule|directive)\b',
    r'\b(budget|appropriation|funding|grant|subsidy|allocation)\b',
    r'\b(tax|taxation|levy|assessment)\b',
    r'\b(revenue|spending|fiscal|financial) (forecast|projection|update|plan|report)\b',

    # Government officials
    r'\b(governor|lieutenant governor|attorney general)\b',
    r'\b(mayor|selectboard|city council|town meeting)\b',
    r'\b(senator|representative|delegate|assemblyman|assemblywoman)\b',
    r'\b(secretary of state|treasurer|auditor)\b',

    # Climate/environmental policy (NOT weather)
    r'\bclimate (policy|action|plan|legislation|bill|law)\b',
    r'\bcarbon (tax|pricing|market|trading|credit)\b',
    r'\bemissions? (reduction|target|cap|trading|standard)\b',
    r'\bgreenhouse gas (reduction|policy|regulation)\b',
    r'\brenewable energy (policy|mandate|standard|requirement)\b',
    r'\benvironmental (policy|regulation|protection|law)\b',

    # Sports/stadium policy (NOT game coverage)
    r'\b(stadium|arena|facility) (funding|budget|proposal|plan|bond|construction)\b',
    r'\bsports (betting|gambling|wagering) (bill|legislation|law|legalization)\b',
    r'\b(athletic|sports) (program|department) (budget|funding|grant)\b',
    r'\bfacility (construction|development|building) (plan|proposal|project)\b',

    # Political processes
    r'\b(election|campaign|vote|referendum|ballot|initiative)\b',
    r'\b(hearing|testimony|debate|public comment|forum)\b',
    r'\b(veto|override|passed|approved|rejected|signed into law)\b',
    r'\b(petition|lawsuit|litigation|court case|ruling|decision)\b',

    # Policy domains
    r'\b(education|healthcare|housing|transportation|infrastructure) (policy|reform|bill|plan|proposal)\b',
    r'\b(zoning|land use|development|planning) (policy|reform|ordinance|regulation)\b',
    r'\b(housing|education) (affordability|funding|access) (plan|proposal|bill|initiative)\b',
]


def contains_policy_keywords(text: str) -> bool:
    """
    Check if text contains policy-relevant keywords (WHITELIST)

    Articles with policy keywords should generally NOT be filtered,
    as they contain newsworthy political/government content.

    Args:
        text: Article title or summary to check

    Returns:
        True if contains policy keywords, False otherwise
    """
    if not text:
        return False

    text_lower = text.lower()
    for pattern in POLICY_WHITELIST:
        if re.search(pattern, text_lower):
            return True

    return False


def is_new_hampshire_article(text: str) -> bool:
    """
    Check if text is about New Hampshire (non-Vermont content)

    VT Digger and other regional sources sometimes publish NH articles.
    This filters out content that is clearly about NH, not VT.

    IMPROVED: Context-aware detection to avoid false positives from
    middle initials (e.g., "Senator NH Thompson")

    Args:
        text: Article title or summary to check

    Returns:
        True if New Hampshire-related, False otherwise
    """
    if not text:
        return False

    text_lower = text.lower()

    # Check for explicit "New Hampshire" mention
    if re.search(r'\bnew hampshire\b', text_lower):
        # Border story check: only filter if Vermont NOT mentioned
        if not re.search(r'\bvermont\b|\bvt\b', text_lower):
            return True

    # Check for "NH" in clear New Hampshire contexts (NOT middle initials)
    nh_context_patterns = [
        r'\bn\.h\.\b',  # N.H. with periods (state abbreviation)
        r'\bnh\s+(state|governor|legislature|senate|house|lawmakers|residents|voters)\b',
        r'\b(in|from|near|across)\s+nh\b',  # Geographic context
        r'\bnh\s+(seacoast|white mountains|lakes region)\b',  # NH regions
    ]

    for pattern in nh_context_patterns:
        if re.search(pattern, text_lower):
            if not re.search(r'\bvermont\b|\bvt\b', text_lower):
                return True

    # Check for NH cities (excluding common Vermont/NH border towns)
    nh_city_patterns = [
        r'\bmanchester\b', r'\bnashua\b', r'\bconcord\b', r'\bdover\b',
        r'\brochester\b', r'\bsalem\b', r'\bmerrimack\b', r'\bhudson\b',
        r'\blondonderry\b', r'\bderry\b', r'\bkeene\b', r'\bportsmouth\b',
        r'\blaconia\b', r'\bclaremont\b', r'\blebanon\b',
    ]

    for pattern in nh_city_patterns:
        if re.search(pattern, text_lower):
            # Border story check
            if not re.search(r'\bvermont\b|\bvt\b', text_lower):
                return True

    return False


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


def is_too_short(title: str, content: str, summary: str = '', min_words: int = 50) -> bool:
    """
    Check if article is too short to contain substantial news content

    Very short articles are often briefs, announcements, or fragments
    that don't provide enough context for fact extraction.

    Uses word count instead of character count for more consistent and
    reliable filtering across different writing styles.

    Args:
        title: Article title
        content: Article content/text
        summary: Article summary
        min_words: Minimum word count (default 50)

    Returns:
        True if too short, False otherwise
    """
    # Use the longest available text
    text = content or summary or ''

    # Strip HTML tags to get actual text content
    # Simple regex approach: remove everything between < and >
    text_without_html = re.sub(r'<[^>]+>', '', text)

    # Count words (split on whitespace)
    words = text_without_html.split()
    word_count = len(words)

    return word_count < min_words


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

    IMPROVED: Distinguishes between game coverage (filter) and
    sports-related policy/funding stories (don't filter).

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if sports game coverage, False otherwise
    """
    if not title:
        return False

    text = f"{title} {summary}"
    text_lower = text.lower()
    title_lower = title.lower()

    # WHITELIST: Sports policy/funding should NOT be filtered
    # Check policy keywords first to avoid false positives
    if contains_policy_keywords(text):
        # Additional check: explicit sports policy patterns
        sports_policy_patterns = [
            r'\b(stadium|arena|facility) (funding|budget|proposal|plan|bond|construction)\b',
            r'\bsports (betting|gambling|wagering) (bill|legislation|law|legalization)\b',
            r'\b(athletic|sports) (program|department) (budget|funding|grant|allocation)\b',
            r'\b(coach|player) (contract|salary|compensation) (approved|negotiated)\b',
            r'\b(team|franchise) (relocation|move|proposal|approval)\b',
        ]

        for pattern in sports_policy_patterns:
            if re.search(pattern, text_lower):
                return False  # This is sports POLICY, not game coverage

    # Game score patterns: "Team 3, Team 2" or "Team beats Team" or "Team vs Team"
    score_patterns = [
        r'\b\d+\s*-\s*\d+\b',  # 3-2, 21-14
        r'\b\w+\s+\d+,\s+\w+\s+\d+\b',  # Team 3, Team 2
        r'\bvs\.?\s+',  # vs or vs.
        r'\b(beat|beats|win|wins|won|defeat|defeats|defeated|tops)\b',  # victory verbs
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

    IMPROVED: Distinguishes between weather forecasts (filter) and
    climate policy articles (don't filter). Climate policy is newsworthy
    and should be extracted.

    Args:
        title: Article title
        summary: Article summary/description

    Returns:
        True if weather alert, False otherwise
    """
    if not title:
        return False

    text = f"{title} {summary}"
    text_lower = text.lower()
    title_lower = title.lower()

    # WHITELIST: Climate/environmental policy should NOT be filtered
    # Check policy keywords first to avoid false positives
    if contains_policy_keywords(text):
        # Additional check: explicit climate policy patterns
        climate_policy_patterns = [
            r'\bclimate (policy|action|plan|legislation|bill|law)\b',
            r'\bcarbon (tax|pricing|market|trading|credit)\b',
            r'\bemissions? (reduction|target|cap|trading|standard)\b',
            r'\brenewable energy (policy|mandate|standard)\b',
            r'\benvironmental (policy|regulation|protection|law)\b',
        ]

        for pattern in climate_policy_patterns:
            if re.search(pattern, text_lower):
                return False  # This is climate POLICY, not weather

    # Weather alert patterns (actual forecasts)
    weather_patterns = [
        r'\bweather forecast\b',
        r'\bforecast:',
        r'\bweather (alert|warning|outlook|update)\b',
        r'\bstorm watch\b',
        r'\bwinter storm (watch|warning|advisory)\b',
        r'\bflood (watch|warning|advisory)\b',
        r'\bsevere weather (watch|warning)\b',
        r'\btoday\'?s weather\b',
        r'\b\d+-day (forecast|outlook|weather)\b',  # 7-day forecast, 5-day outlook
        r'\bextended forecast\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\'?s weather\b',
    ]

    for pattern in weather_patterns:
        if re.search(pattern, text_lower):
            return True

    # Temperature patterns in title: "High of 75°" or "Temps in the 60s" or "High temperatures expected"
    # (These are clearly weather forecasts, not policy)
    temp_patterns = [
        r'\b(high|low|temp|temperature)s?\s+(of|in|to reach)\s+\d+°?',  # "High of 75", "temps in the 60s"
        r'\b(high|low) (temp|temperature)s?\s+(expected|forecast)',  # "High temperatures expected"
    ]

    for pattern in temp_patterns:
        if re.search(pattern, title_lower):
            return True

    return False


def should_filter_article(
    title: str,
    content: str = '',
    summary: str = '',
    min_words: int = 50
) -> Tuple[bool, str]:
    """
    Master filter function - checks all low-value content filters

    Args:
        title: Article title
        content: Article content/text
        summary: Article summary
        min_words: Minimum word count for articles (default 50)

    Returns:
        Tuple of (should_filter: bool, reason: str)
        - should_filter: True if article should be filtered out
        - reason: Human-readable reason for filtering
    """
    if not title:
        return True, "missing_title"

    # Check each filter in order
    # New Hampshire filter first (geography-based)
    text_to_check = f"{title} {summary}"
    if is_new_hampshire_article(text_to_check):
        return True, "new_hampshire_article"

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

    if is_too_short(title, content, summary, min_words):
        return True, "too_short"

    return False, "passed"
