// Enriched entity data with all statistics, connections, facts, etc.
import { EntityData } from '../components/EntityDetailsPanel';

export const enrichedEntityData: Record<string, EntityData> = {
  'phil-scott': {
    id: 'phil-scott',
    name: 'Phil Scott',
    type: 'PERSON',
    confidence: 0.95,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q7182573',
      description: 'American politician, 82nd Governor of Vermont',
      birth_date: 'August 4, 1958',
      occupation: 'Politician',
      position: '82nd Governor of Vermont',
      party: 'Republican Party',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Phil_Scott_(politician)',
    },
    statistics: {
      article_count: 12,
      first_seen: '2024-01-15',
      last_seen: '2024-05-15',
      centrality: 0.82,
    },
    connections: [
      { entity_id: 'climate-bill', entity_name: 'Climate Bill 2024', entity_type: 'EVENT', relationship: 'vetoed', strength: 0.9 },
      { entity_id: 'vt-legislature', entity_name: 'Vermont Legislature', entity_type: 'ORG', relationship: 'signed legislation', strength: 0.85 },
      { entity_id: 'montpelier', entity_name: 'Montpelier', entity_type: 'LOCATION', relationship: 'works in', strength: 0.7 },
    ],
    facts: [
      {
        text: 'Governor Phil Scott vetoed the Climate Bill 2024 on May 15, 2024, citing concerns about economic impact on Vermont businesses.',
        confidence: 0.92,
        sources: ['Claude', 'Gemini'],
        article_id: 'vt_climate_2024',
        date: '2024-05-15',
      },
      {
        text: 'Phil Scott signed education funding legislation allocating $1.2B to Vermont schools.',
        confidence: 0.88,
        sources: ['Claude', 'GPT'],
        article_id: 'vt_education_funding',
        date: '2024-04-03',
      },
    ],
    recent_articles: [
      { id: 'vt_climate_2024', title: 'Vermont Climate Bill Vetoed by Governor', date: 'May 15, 2024' },
      { id: 'vt_education_funding', title: 'State Budget Passes with Education Focus', date: 'April 3, 2024' },
      { id: 'vt_infrastructure', title: 'Governor Announces Infrastructure Plan', date: 'March 12, 2024' },
    ],
  },

  'bernie-sanders': {
    id: 'bernie-sanders',
    name: 'Bernie Sanders',
    type: 'PERSON',
    confidence: 0.98,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q359442',
      description: 'United States Senator from Vermont',
      birth_date: 'September 8, 1941',
      occupation: 'Politician',
      position: 'U.S. Senator from Vermont',
      party: 'Independent',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Bernie_Sanders',
    },
    statistics: {
      article_count: 18,
      first_seen: '2024-01-01',
      last_seen: '2024-05-20',
      centrality: 0.91,
    },
    connections: [
      { entity_id: 'burlington', entity_name: 'Burlington', entity_type: 'LOCATION', relationship: 'former mayor', strength: 0.95 },
      { entity_id: 'peter-welch', entity_name: 'Peter Welch', entity_type: 'PERSON', relationship: 'colleague', strength: 0.8 },
      { entity_id: 'climate-bill', entity_name: 'Climate Bill 2024', entity_type: 'EVENT', relationship: 'supported', strength: 0.75 },
    ],
    facts: [
      {
        text: 'Senator Bernie Sanders spoke at a Burlington town hall advocating for stronger climate action.',
        confidence: 0.94,
        sources: ['Claude', 'Gemini', 'GPT'],
        article_id: 'sanders_climate_rally',
        date: '2024-05-20',
      },
    ],
    recent_articles: [
      { id: 'sanders_climate_rally', title: 'Sanders Rallies Support for Climate Bill', date: 'May 20, 2024' },
      { id: 'sanders_healthcare', title: 'Senator Pushes for Medicare Expansion', date: 'April 18, 2024' },
    ],
  },

  'burlington': {
    id: 'burlington',
    name: 'Burlington',
    type: 'LOCATION',
    confidence: 0.96,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q49218',
      description: 'Largest city in Vermont',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Burlington,_Vermont',
    },
    statistics: {
      article_count: 24,
      first_seen: '2024-01-05',
      last_seen: '2024-05-22',
      centrality: 0.88,
    },
    connections: [
      { entity_id: 'bernie-sanders', entity_name: 'Bernie Sanders', entity_type: 'PERSON', relationship: 'former mayor', strength: 0.95 },
      { entity_id: 'peter-welch', entity_name: 'Peter Welch', entity_type: 'PERSON', relationship: 'represents', strength: 0.85 },
      { entity_id: 'uvm', entity_name: 'University of Vermont', entity_type: 'ORG', relationship: 'home to', strength: 0.9 },
      { entity_id: 'lake-champlain', entity_name: 'Lake Champlain', entity_type: 'LOCATION', relationship: 'located on', strength: 0.7 },
    ],
    facts: [
      {
        text: 'Burlington voted overwhelmingly in favor of the climate initiative with 78% support.',
        confidence: 0.91,
        sources: ['Claude', 'Gemini'],
        article_id: 'burlington_climate_vote',
        date: '2024-05-22',
      },
    ],
    recent_articles: [
      { id: 'burlington_climate_vote', title: 'Burlington Votes for Climate Action', date: 'May 22, 2024' },
      { id: 'burlington_development', title: 'Downtown Development Plan Approved', date: 'April 30, 2024' },
    ],
  },

  'climate-bill': {
    id: 'climate-bill',
    name: 'Climate Bill 2024',
    type: 'EVENT',
    confidence: 0.93,
    sources: ['Claude', 'Gemini', 'GPT'],
    statistics: {
      article_count: 15,
      first_seen: '2024-03-01',
      last_seen: '2024-05-20',
      centrality: 0.85,
    },
    connections: [
      { entity_id: 'phil-scott', entity_name: 'Phil Scott', entity_type: 'PERSON', relationship: 'vetoed by', strength: 0.9 },
      { entity_id: 'vt-legislature', entity_name: 'Vermont Legislature', entity_type: 'ORG', relationship: 'proposed by', strength: 0.95 },
      { entity_id: 'bernie-sanders', entity_name: 'Bernie Sanders', entity_type: 'PERSON', relationship: 'supported by', strength: 0.75 },
      { entity_id: 'molly-gray', entity_name: 'Molly Gray', entity_type: 'PERSON', relationship: 'supported by', strength: 0.8 },
      { entity_id: 'uvm', entity_name: 'University of Vermont', entity_type: 'ORG', relationship: 'researched by', strength: 0.7 },
      { entity_id: 'vtdigger', entity_name: 'VTDigger', entity_type: 'ORG', relationship: 'covered by', strength: 0.65 },
    ],
    facts: [
      {
        text: 'The Climate Bill 2024 aimed to reduce Vermont\'s carbon emissions by 40% by 2030 through renewable energy incentives.',
        confidence: 0.95,
        sources: ['Claude', 'Gemini', 'GPT'],
        article_id: 'climate_bill_details',
        date: '2024-03-15',
      },
      {
        text: 'Governor Phil Scott vetoed the Climate Bill citing economic concerns, despite strong legislative support.',
        confidence: 0.92,
        sources: ['Claude', 'Gemini'],
        article_id: 'vt_climate_2024',
        date: '2024-05-15',
      },
    ],
    recent_articles: [
      { id: 'sanders_climate_rally', title: 'Sanders Rallies Support for Climate Bill', date: 'May 20, 2024' },
      { id: 'vt_climate_2024', title: 'Vermont Climate Bill Vetoed by Governor', date: 'May 15, 2024' },
      { id: 'climate_bill_debate', title: 'Legislature Debates Climate Action', date: 'April 10, 2024' },
    ],
  },

  'vt-legislature': {
    id: 'vt-legislature',
    name: 'Vermont Legislature',
    type: 'ORG',
    confidence: 0.94,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q1545358',
      description: 'Legislative branch of Vermont state government',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Vermont_General_Assembly',
    },
    statistics: {
      article_count: 20,
      first_seen: '2024-01-10',
      last_seen: '2024-05-18',
      centrality: 0.79,
    },
    connections: [
      { entity_id: 'montpelier', entity_name: 'Montpelier', entity_type: 'LOCATION', relationship: 'located in', strength: 0.95 },
      { entity_id: 'climate-bill', entity_name: 'Climate Bill 2024', entity_type: 'EVENT', relationship: 'proposed', strength: 0.9 },
      { entity_id: 'phil-scott', entity_name: 'Phil Scott', entity_type: 'PERSON', relationship: 'works with', strength: 0.85 },
    ],
    facts: [
      {
        text: 'The Vermont Legislature passed the Climate Bill with bipartisan support before the governor\'s veto.',
        confidence: 0.89,
        sources: ['Claude', 'GPT'],
        article_id: 'legislature_climate_vote',
        date: '2024-04-25',
      },
    ],
    recent_articles: [
      { id: 'legislature_climate_vote', title: 'Legislature Passes Climate Bill', date: 'April 25, 2024' },
      { id: 'legislature_budget', title: 'Budget Approved by Lawmakers', date: 'March 28, 2024' },
    ],
  },

  'peter-welch': {
    id: 'peter-welch',
    name: 'Peter Welch',
    type: 'PERSON',
    confidence: 0.94,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q7177134',
      description: 'United States Senator from Vermont',
      birth_date: 'May 2, 1947',
      occupation: 'Politician',
      position: 'U.S. Senator from Vermont',
      party: 'Democratic Party',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Peter_Welch',
    },
    statistics: {
      article_count: 8,
      first_seen: '2024-02-01',
      last_seen: '2024-05-10',
      centrality: 0.68,
    },
    connections: [
      { entity_id: 'burlington', entity_name: 'Burlington', entity_type: 'LOCATION', relationship: 'represents', strength: 0.85 },
      { entity_id: 'bernie-sanders', entity_name: 'Bernie Sanders', entity_type: 'PERSON', relationship: 'colleague', strength: 0.8 },
    ],
    facts: [
      {
        text: 'Senator Peter Welch represents Vermont in the United States Senate.',
        confidence: 0.96,
        sources: ['Claude', 'Gemini', 'GPT'],
        article_id: 'welch_profile',
        date: '2024-02-01',
      },
    ],
    recent_articles: [
      { id: 'welch_infrastructure', title: 'Welch Supports Infrastructure Bill', date: 'May 10, 2024' },
    ],
  },

  'molly-gray': {
    id: 'molly-gray',
    name: 'Molly Gray',
    type: 'PERSON',
    confidence: 0.89,
    sources: ['Claude', 'Gemini'],
    statistics: {
      article_count: 5,
      first_seen: '2024-03-15',
      last_seen: '2024-05-18',
      centrality: 0.54,
    },
    connections: [
      { entity_id: 'climate-bill', entity_name: 'Climate Bill 2024', entity_type: 'EVENT', relationship: 'supports', strength: 0.8 },
    ],
    facts: [
      {
        text: 'Molly Gray publicly supported the Climate Bill 2024.',
        confidence: 0.87,
        sources: ['Claude', 'Gemini'],
        article_id: 'gray_climate_support',
        date: '2024-05-18',
      },
    ],
    recent_articles: [
      { id: 'gray_climate_support', title: 'Gray Urges Climate Action', date: 'May 18, 2024' },
    ],
  },

  'montpelier': {
    id: 'montpelier',
    name: 'Montpelier',
    type: 'LOCATION',
    confidence: 0.97,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q33486',
      description: 'Capital city of Vermont',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Montpelier,_Vermont',
    },
    statistics: {
      article_count: 16,
      first_seen: '2024-01-10',
      last_seen: '2024-05-19',
      centrality: 0.72,
    },
    connections: [
      { entity_id: 'vt-legislature', entity_name: 'Vermont Legislature', entity_type: 'ORG', relationship: 'home to', strength: 0.95 },
      { entity_id: 'phil-scott', entity_name: 'Phil Scott', entity_type: 'PERSON', relationship: 'workplace of', strength: 0.7 },
    ],
    facts: [
      {
        text: 'Montpelier serves as the capital of Vermont and houses the state legislature.',
        confidence: 0.98,
        sources: ['Claude', 'Gemini', 'GPT'],
        article_id: 'montpelier_capital',
        date: '2024-01-10',
      },
    ],
    recent_articles: [
      { id: 'montpelier_flooding', title: 'Montpelier Flood Recovery Continues', date: 'May 19, 2024' },
    ],
  },

  'uvm': {
    id: 'uvm',
    name: 'University of Vermont',
    type: 'ORG',
    confidence: 0.92,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q49117',
      description: 'Public university in Burlington, Vermont',
      wikipedia_url: 'https://en.wikipedia.org/wiki/University_of_Vermont',
    },
    statistics: {
      article_count: 11,
      first_seen: '2024-02-15',
      last_seen: '2024-05-12',
      centrality: 0.66,
    },
    connections: [
      { entity_id: 'burlington', entity_name: 'Burlington', entity_type: 'LOCATION', relationship: 'located in', strength: 0.9 },
      { entity_id: 'climate-bill', entity_name: 'Climate Bill 2024', entity_type: 'EVENT', relationship: 'researched', strength: 0.7 },
    ],
    facts: [
      {
        text: 'University of Vermont researchers published studies supporting climate policy.',
        confidence: 0.88,
        sources: ['Claude', 'Gemini'],
        article_id: 'uvm_climate_research',
        date: '2024-05-12',
      },
    ],
    recent_articles: [
      { id: 'uvm_climate_research', title: 'UVM Study Shows Climate Impact', date: 'May 12, 2024' },
    ],
  },

  'lake-champlain': {
    id: 'lake-champlain',
    name: 'Lake Champlain',
    type: 'LOCATION',
    confidence: 0.91,
    sources: ['Claude', 'Gemini'],
    wikidata: {
      id: 'Q1169',
      description: 'Lake in North America',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Lake_Champlain',
    },
    statistics: {
      article_count: 7,
      first_seen: '2024-03-01',
      last_seen: '2024-05-08',
      centrality: 0.48,
    },
    connections: [
      { entity_id: 'burlington', entity_name: 'Burlington', entity_type: 'LOCATION', relationship: 'borders', strength: 0.8 },
      { entity_id: 'green-mountain-power', entity_name: 'Green Mountain Power', entity_type: 'ORG', relationship: 'operates near', strength: 0.6 },
    ],
    facts: [],
    recent_articles: [
      { id: 'lake_conservation', title: 'Lake Champlain Conservation Efforts', date: 'May 8, 2024' },
    ],
  },

  'vtdigger': {
    id: 'vtdigger',
    name: 'VTDigger',
    type: 'ORG',
    confidence: 0.88,
    sources: ['Claude', 'GPT'],
    wikidata: {
      id: 'Q7906785',
      description: 'Vermont news organization',
      wikipedia_url: 'https://en.wikipedia.org/wiki/VTDigger',
    },
    statistics: {
      article_count: 9,
      first_seen: '2024-01-20',
      last_seen: '2024-05-15',
      centrality: 0.58,
    },
    connections: [
      { entity_id: 'climate-bill', entity_name: 'Climate Bill 2024', entity_type: 'EVENT', relationship: 'covered', strength: 0.65 },
    ],
    facts: [],
    recent_articles: [],
  },

  'green-mountain-power': {
    id: 'green-mountain-power',
    name: 'Green Mountain Power',
    type: 'ORG',
    confidence: 0.86,
    sources: ['Claude', 'Gemini'],
    statistics: {
      article_count: 6,
      first_seen: '2024-02-20',
      last_seen: '2024-04-30',
      centrality: 0.52,
    },
    connections: [
      { entity_id: 'lake-champlain', entity_name: 'Lake Champlain', entity_type: 'LOCATION', relationship: 'operates near', strength: 0.6 },
    ],
    facts: [],
    recent_articles: [],
  },

  'brattleboro': {
    id: 'brattleboro',
    name: 'Brattleboro',
    type: 'LOCATION',
    confidence: 0.93,
    sources: ['Claude', 'Gemini', 'GPT'],
    wikidata: {
      id: 'Q49179',
      description: 'Town in Vermont',
      wikipedia_url: 'https://en.wikipedia.org/wiki/Brattleboro,_Vermont',
    },
    statistics: {
      article_count: 4,
      first_seen: '2024-03-05',
      last_seen: '2024-04-15',
      centrality: 0.38,
    },
    connections: [
      { entity_id: 'town-meeting', entity_name: 'Town Meeting Day', entity_type: 'EVENT', relationship: 'hosted', strength: 0.7 },
    ],
    facts: [],
    recent_articles: [],
  },

  'town-meeting': {
    id: 'town-meeting',
    name: 'Town Meeting Day',
    type: 'EVENT',
    confidence: 0.90,
    sources: ['Claude', 'Gemini'],
    statistics: {
      article_count: 5,
      first_seen: '2024-03-05',
      last_seen: '2024-03-05',
      centrality: 0.42,
    },
    connections: [
      { entity_id: 'brattleboro', entity_name: 'Brattleboro', entity_type: 'LOCATION', relationship: 'held in', strength: 0.7 },
    ],
    facts: [],
    recent_articles: [],
  },
};
