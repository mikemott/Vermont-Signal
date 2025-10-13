"""
Vermont Signal RSS Feed Definitions
Curated list of Vermont news sources with filtering and source mapping
"""

from typing import Dict, Set

# RSS Feeds to monitor for Vermont news
RSS_FEEDS = [
    # Major sources - VTDigger (comprehensive Vermont coverage)
    "https://vtdigger.org/feed/",
    "https://vtdigger.org/government-politics/feed/",
    "https://vtdigger.org/business/feed/",
    "https://vtdigger.org/environment/feed/",

    # Major sources - Statewide Vermont media
    "https://www.sevendaysvt.com/vermont/Rss.xml/feed",
    "https://www.vermontpublic.org/podcast/vermont-edition/rss.xml",
    "https://vermontbiz.com/rss.xml",
    "https://www.mychamplainvalley.com/feed/",

    # Major sources - Regional coverage with Vermont focus
    "https://www.boston.com/tag/vermont/feed/",
    "https://whdh.com/regional/vermont/feed/",
    "https://www.news10.com/news/vt-news/feed/",
    "https://www.mynbc5.com/topstories-rss",

    # Regional - Southern Vermont
    "https://reformer.com/search/?nsa=eedition&c[]=outdoors,history,local-news,business,health&l=50&t=article&f=atom&altf=mrss&fulltext=complete&ips=1000",
    "https://benningtonbanner.com/search/?nsa=eedition&c[]=outdoors,history,local-news,business,health&l=50&t=article&f=atom&altf=mrss&fulltext=complete&ips=1000",
    "https://thevermontstandard.com/feed/",

    # Regional - Central Vermont
    "https://timesargus.com/search/?nsa=eedition&c[]=outdoors,history,local-news,business,health&l=50&t=article&f=atom&altf=mrss&fulltext=complete&ips=1000",
    "https://rutlandherald.com/search/?nsa=eedition&c[]=outdoors,history,local-news,business,health&l=50&t=article&f=atom&altf=mrss&fulltext=complete&ips=1000",

    # Regional - Central/Western Vermont
    "https://www.addisonindependent.com/feed/",

    # Regional - Mountain/Resort areas
    "https://mountaintimes.info/feed/",

    # Regional - Upper Valley/Northern Vermont
    "https://vnews.com/feed/",
    "https://samessenger.com/search/?nsa=eedition&c[]=outdoors,history,local-news,business,health&l=50&t=article&f=atom&altf=mrss&fulltext=complete&ips=1000",

    # Local Community Papers
    "https://www.manchesterjournal.com/search/?nsa=eedition&c=local-news&l=50&t=article&f=atom&altf=mrss&fulltext=complete&pgs=1&ips=1200x630",
    "https://www.ourherald.com/feed/",
    "https://vermontdailychronicle.com/feed/",
    "https://www.chestertelegraph.org/feed/",
    "https://thebridgevt.org/feed/",
    "https://hardwickgazette.org/feed/",
    "https://www.charlottenewsvt.org/feed/",
]

# Feeds that require Vermont keyword filtering (regional/national sources that may include non-VT content)
FILTERED_FEEDS: Set[str] = {
    "https://www.boston.com/tag/vermont/feed/",
    "https://whdh.com/regional/vermont/feed/",
    "https://www.news10.com/news/vt-news/feed/",
    "https://www.mynbc5.com/topstories-rss",
    "https://www.mychamplainvalley.com/feed/",
}

# Feeds that may be rate-limited (require slower polling and longer delays)
RATE_LIMITED_FEEDS: Set[str] = {
    "https://samessenger.com/search/?nsa=eedition&c[]=outdoors,history,local-news,business,health&l=50&t=article&f=atom&altf=mrss&fulltext=complete&ips=1000",
    "https://www.manchesterjournal.com/search/?nsa=eedition&c=local-news&l=50&t=article&f=atom&altf=mrss&fulltext=complete&pgs=1&ips=1200x630",
}

# Source name mappings (clean up feed titles for better readability)
SOURCE_MAPPING: Dict[str, str] = {
    # Long feed titles from search-based RSS feeds
    "www.reformer.com - RSS Results in outdoors,history,local-news,business,health of type article": "Brattleboro Reformer",
    "benningtonbanner.com - RSS Results in outdoors,history,local-news,business,health of type article": "Bennington Banner",
    "timesargus.com - RSS Results in outdoors,history,local-news,business,health of type article": "Times Argus",
    "rutlandherald.com - RSS Results in outdoors,history,local-news,business,health of type article": "Rutland Herald",
    "samessenger.com - RSS Results in outdoors,history,local-news,business,health of type article": "St. Albans Messenger",
    "manchesterjournal.com - RSS Results in local-news of type article": "Manchester Journal",

    # Generic titles that need clarification
    "Vermont News | NEWS10 ABC": "NEWS10 ABC",
    "Top Stories": "NBC5",

    # Community papers with verbose titles
    "The White River Valley Herald": "White River Valley Herald",
    "Vermont Daily Chronicle": "Vermont Daily Chronicle",
    "The Chester Telegraph": "Chester Telegraph",
    "The Bridge": "Montpelier Bridge",
    "The Hardwick Gazette": "Hardwick Gazette",
    "The Charlotte News": "Charlotte News",

    # Regional sources with state clarification
    "Vermont - 7NEWS Boston | WHDH.com": "7News Boston (Vermont)",
    "Vermont – Boston News, Weather, Sports | WHDH 7News": "7News Boston (Vermont)",
}
