// Sample processed articles from the Vermont news pipeline
// This matches the output format from the Python backend

export interface Article {
  article_id: string;
  title: string;
  source: string;
  date: string;
  url: string;
  consensus_summary: string;
  read_time: number; // minutes
  extracted_facts: Array<{
    entity: string;
    type: 'PERSON' | 'LOCATION' | 'ORG' | 'EVENT';
    confidence: number;
    event_description?: string;
    sources: string[];
  }>;
  metadata: {
    processing_timestamp: string;
    total_facts: number;
    high_confidence_facts: number;
    overall_confidence: number;
    conflict_report: {
      has_conflicts: boolean;
      summary_similarity: number;
    };
  };
}

export const sampleArticles: Article[] = [
  {
    article_id: 'vt_climate_2024_001',
    title: 'Vermont Legislature Passes Historic Climate Bill Despite Veto Threat',
    source: 'VTDigger',
    date: '2024-03-15',
    url: 'https://vtdigger.org/2024/03/15/climate-bill',
    consensus_summary: 'The Vermont Legislature voted 95-45 to pass comprehensive climate legislation requiring a 40% reduction in greenhouse gas emissions by 2030. Governor Phil Scott indicated he would veto the bill, citing concerns about economic impact on small businesses.',
    read_time: 4,
    extracted_facts: [
      { entity: 'Phil Scott', type: 'PERSON', confidence: 0.98, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Vermont Legislature', type: 'ORG', confidence: 0.95, sources: ['claude', 'gemini'] },
      { entity: 'Climate Bill 2024', type: 'EVENT', confidence: 0.92, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Montpelier', type: 'LOCATION', confidence: 0.88, sources: ['claude', 'gemini'] },
      { entity: 'Burlington', type: 'LOCATION', confidence: 0.75, sources: ['claude'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-15T14:30:00',
      total_facts: 12,
      high_confidence_facts: 10,
      overall_confidence: 0.95,
      conflict_report: { has_conflicts: false, summary_similarity: 0.89 }
    }
  },
  {
    article_id: 'vt_housing_2024_002',
    title: 'Burlington Approves Controversial Housing Development in Old North End',
    source: 'Seven Days',
    date: '2024-03-14',
    url: 'https://sevendaysvt.com/2024/03/14/housing',
    consensus_summary: 'Burlington City Council voted 8-4 to approve a 120-unit affordable housing project in the Old North End, overriding neighborhood objections about parking and density. The project will include 30% affordable units.',
    read_time: 3,
    extracted_facts: [
      { entity: 'Burlington', type: 'LOCATION', confidence: 0.97, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Burlington City Council', type: 'ORG', confidence: 0.94, sources: ['claude', 'gemini'] },
      { entity: 'Old North End', type: 'LOCATION', confidence: 0.91, sources: ['claude', 'gemini'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-14T16:45:00',
      total_facts: 8,
      high_confidence_facts: 7,
      overall_confidence: 0.88,
      conflict_report: { has_conflicts: false, summary_similarity: 0.85 }
    }
  },
  {
    article_id: 'vt_education_2024_003',
    title: 'UVM Announces Major Expansion of Climate Research Center',
    source: 'VTDigger',
    date: '2024-03-13',
    url: 'https://vtdigger.org/2024/03/13/uvm-climate',
    consensus_summary: 'The University of Vermont secured a $12 million federal grant to expand its Gund Institute for Environment, adding new research facilities focused on Lake Champlain ecosystem restoration and renewable energy technology.',
    read_time: 5,
    extracted_facts: [
      { entity: 'University of Vermont', type: 'ORG', confidence: 0.99, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Lake Champlain', type: 'LOCATION', confidence: 0.96, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Burlington', type: 'LOCATION', confidence: 0.85, sources: ['gemini'] },
      { entity: 'Gund Institute', type: 'ORG', confidence: 0.92, sources: ['claude', 'gemini'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-13T10:20:00',
      total_facts: 10,
      high_confidence_facts: 9,
      overall_confidence: 0.93,
      conflict_report: { has_conflicts: false, summary_similarity: 0.91 }
    }
  },
  {
    article_id: 'vt_politics_2024_004',
    title: 'Bernie Sanders Announces Healthcare Town Halls Across Vermont',
    source: 'Seven Days',
    date: '2024-03-12',
    url: 'https://sevendaysvt.com/2024/03/12/sanders-healthcare',
    consensus_summary: 'Senator Bernie Sanders will hold five town hall meetings across Vermont in April to discuss Medicare for All legislation. Events scheduled in Burlington, Rutland, Brattleboro, St. Johnsbury, and Bennington.',
    read_time: 3,
    extracted_facts: [
      { entity: 'Bernie Sanders', type: 'PERSON', confidence: 0.99, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Burlington', type: 'LOCATION', confidence: 0.95, sources: ['claude', 'gemini'] },
      { entity: 'Rutland', type: 'LOCATION', confidence: 0.95, sources: ['claude', 'gemini'] },
      { entity: 'Brattleboro', type: 'LOCATION', confidence: 0.95, sources: ['claude', 'gemini'] },
      { entity: 'St. Johnsbury', type: 'LOCATION', confidence: 0.93, sources: ['claude', 'gemini'] },
      { entity: 'Bennington', type: 'LOCATION', confidence: 0.93, sources: ['claude', 'gemini'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-12T09:15:00',
      total_facts: 11,
      high_confidence_facts: 10,
      overall_confidence: 0.96,
      conflict_report: { has_conflicts: false, summary_similarity: 0.93 }
    }
  },
  {
    article_id: 'vt_business_2024_005',
    title: 'Green Mountain Power Announces Grid Modernization Investment',
    source: 'VTDigger',
    date: '2024-03-11',
    url: 'https://vtdigger.org/2024/03/11/gmp-grid',
    consensus_summary: 'Green Mountain Power unveiled a $200 million plan to upgrade Vermont\'s electrical grid infrastructure, focusing on smart meters, battery storage, and enhanced resilience against extreme weather events.',
    read_time: 4,
    extracted_facts: [
      { entity: 'Green Mountain Power', type: 'ORG', confidence: 0.98, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Vermont', type: 'LOCATION', confidence: 0.92, sources: ['claude', 'gemini'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-11T13:40:00',
      total_facts: 7,
      high_confidence_facts: 6,
      overall_confidence: 0.89,
      conflict_report: { has_conflicts: false, summary_similarity: 0.87 }
    }
  },
  {
    article_id: 'vt_local_2024_006',
    title: 'Montpelier Completes Flood Recovery Milestone One Year After Disaster',
    source: 'Seven Days',
    date: '2024-03-10',
    url: 'https://sevendaysvt.com/2024/03/10/montpelier-flood',
    consensus_summary: 'Downtown Montpelier reached 95% business reopening rate following last summer\'s devastating floods. City officials credit coordinated state and federal disaster relief, though some residents still face housing challenges.',
    read_time: 6,
    extracted_facts: [
      { entity: 'Montpelier', type: 'LOCATION', confidence: 0.99, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Phil Scott', type: 'PERSON', confidence: 0.78, sources: ['claude'] },
      { entity: 'Vermont', type: 'LOCATION', confidence: 0.88, sources: ['gemini'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-10T11:25:00',
      total_facts: 9,
      high_confidence_facts: 7,
      overall_confidence: 0.85,
      conflict_report: { has_conflicts: true, summary_similarity: 0.79 }
    }
  },
  {
    article_id: 'vt_culture_2024_007',
    title: 'Burlington\'s Flynn Center Announces Fall Performance Season',
    source: 'Seven Days',
    date: '2024-03-09',
    url: 'https://sevendaysvt.com/2024/03/09/flynn-season',
    consensus_summary: 'The Flynn Center for the Performing Arts revealed its fall lineup featuring national touring acts, Vermont Symphony Orchestra performances, and local theater productions, marking the venue\'s return to pre-pandemic programming levels.',
    read_time: 3,
    extracted_facts: [
      { entity: 'Burlington', type: 'LOCATION', confidence: 0.97, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Flynn Center', type: 'ORG', confidence: 0.95, sources: ['claude', 'gemini'] },
      { entity: 'Vermont Symphony Orchestra', type: 'ORG', confidence: 0.91, sources: ['claude', 'gemini'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-09T15:50:00',
      total_facts: 8,
      high_confidence_facts: 7,
      overall_confidence: 0.91,
      conflict_report: { has_conflicts: false, summary_similarity: 0.88 }
    }
  },
  {
    article_id: 'vt_education_2024_008',
    title: 'Vermont School Districts Grapple with Teacher Shortage Crisis',
    source: 'VTDigger',
    date: '2024-03-08',
    url: 'https://vtdigger.org/2024/03/08/teacher-shortage',
    consensus_summary: 'State education officials report 300+ unfilled teaching positions across Vermont school districts, with rural areas particularly affected. Legislative proposals include housing assistance and loan forgiveness programs to attract educators.',
    read_time: 5,
    extracted_facts: [
      { entity: 'Vermont', type: 'LOCATION', confidence: 0.94, sources: ['claude', 'gemini', 'gpt'] },
      { entity: 'Vermont Legislature', type: 'ORG', confidence: 0.87, sources: ['claude', 'gemini'] },
      { entity: 'Montpelier', type: 'LOCATION', confidence: 0.72, sources: ['claude'] },
    ],
    metadata: {
      processing_timestamp: '2024-03-08T08:30:00',
      total_facts: 9,
      high_confidence_facts: 7,
      overall_confidence: 0.84,
      conflict_report: { has_conflicts: false, summary_similarity: 0.82 }
    }
  }
];
