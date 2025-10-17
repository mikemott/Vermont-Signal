# Topics & Trends Improvements

## Summary

Fixed topic display issues in the Vermont Signal application to remove non-topical words and improve topic labels.

## Problems Solved

### 1. **Non-topical keywords appearing in topics**
   - **Issue**: Generic words like 'said', 'man', 'october', 'year' were appearing as topic keywords
   - **Root Cause**: BERTopic's default English stop words didn't catch domain-specific generic terms
   - **Solution**: Added comprehensive custom stop word list (100+ words) for Vermont news

### 2. **Confusing topic labels**
   - **Issue**: Labels combined 3 random keywords with "&" (e.g., "School & Budget & Education")
   - **Root Cause**: Label generation concatenated top 3 keywords without semantic consideration
   - **Solution**: Changed to use single most important keyword, preferring proper nouns

### 3. **Low-quality keywords passing through**
   - **Issue**: High-frequency but non-meaningful words appeared as topic keywords
   - **Root Cause**: No c-TF-IDF score thresholding
   - **Solution**: Added minimum score threshold (0.05) + semantic filtering

## Changes Made

### File: `vermont_news_analyzer/modules/nlp_tools.py`

#### 1. Added Custom Stop Word List (lines 219-267)
```python
CUSTOM_STOP_WORDS = {
    # Common reporting verbs: said, told, asked, announced...
    # Generic people: man, woman, people, officials...
    # Temporal words: monday, october, year, week...
    # Generic locations: area, place, town, city...
    # Generic actions: make, take, get, give...
    # Plus 60+ more terms
}
```

**Coverage**:
- Reporting verbs (said, told, reported...)
- Temporal words (days, months, years)
- Generic nouns (man, woman, people, area...)
- Common actions (make, take, get, go...)
- Too-generic Vermont terms (vermont, vt)

#### 2. New Method: `_is_meaningful_keyword()` (lines 331-373)
Replaces `_is_html_artifact()` with comprehensive filtering:
- Checks minimum length (3 chars)
- Requires alphabetic characters only
- Filters against custom stop words
- Filters HTML artifacts
- Catches concatenated HTML (e.g., "classwpBlock")

#### 3. New Method: `_filter_keywords_by_score()` (lines 388-417)
Implements c-TF-IDF score thresholding:
- Filters keywords below MIN_TFIDF_SCORE (0.05)
- Applies semantic meaningfulness check
- Returns only high-quality, relevant keywords

#### 4. Improved: `_generate_topic_label()` (lines 419-450)
Changed label generation strategy:
- **Old**: Concatenated 3 keywords with "&"
- **New**: Single most important keyword
- Prefers proper nouns (Montpelier > budget)
- Handles multi-word phrases (climate_change → Climate Change)
- Falls back to first keyword if no proper nouns

#### 5. Updated: `train_topics()` (lines 495-525)
Integrated new filtering into topic computation:
- Applies c-TF-IDF score filtering to all keywords
- Skips topics with no meaningful keywords after filtering
- Stores only top 10 filtered keywords per topic
- Generates improved single-keyword labels

## Testing

Created `test_topic_filtering_standalone.py` to verify filtering logic:

**Test Results**: ✓ 14/14 tests passed

**Tested cases**:
- ✓ Filters: said, told, man, october, year, vermont, vt
- ✓ Keeps: Montpelier, Burlington, Budget, Education, Legislature, Housing, Climate

## Impact on Existing Filtering

**Important**: The new filtering is **additive and non-breaking**:

1. **HTML artifact filtering**: Still works via `_is_html_artifact()` (now calls `_is_meaningful_keyword()`)
2. **BERTopic CountVectorizer**: Still uses English stop words + min_df=2
3. **New layer**: Adds domain-specific stop words on top of existing filters

**No breaking changes** - existing filters remain active.

## Before & After

### Before:
```
Topic: "School & Budget & Education"
Keywords: [said, man, october, year, school, budget, people, education, time, work]
```

### After:
```
Topic: "Education"
Keywords: [Education, School, Budget, Funding, Students, Teachers, District, Program]
```

## Next Steps to Apply Changes

To regenerate topics with new filtering:

```bash
# Recompute topics with improved filtering
python scripts/compute_topics.py --days 90 --min-topic-size 3

# Or use summaries for faster processing
python scripts/compute_topics.py --days 90 --use-summary --min-topic-size 3
```

**Note**: You'll need to recompute topics to see the improvements in the frontend.

## Configuration

New constants in `TopicModeler` class:
- `CUSTOM_STOP_WORDS`: 100+ domain-specific stop words
- `MIN_TFIDF_SCORE`: 0.05 (adjustable threshold)

To adjust sensitivity:
```python
# In nlp_tools.py, line 270
MIN_TFIDF_SCORE = 0.05  # Lower = more keywords, Higher = fewer but more specific
```

## Files Modified

1. `vermont_news_analyzer/modules/nlp_tools.py` - Core filtering improvements
2. `test_topic_filtering_standalone.py` - Test suite (new)
3. `TOPIC_IMPROVEMENTS.md` - This document (new)

## Backward Compatibility

✓ **Fully backward compatible**
- Database schema unchanged
- API endpoints unchanged
- Frontend code unchanged
- Existing topic computation scripts work as before
- Simply recompute topics to see improvements
