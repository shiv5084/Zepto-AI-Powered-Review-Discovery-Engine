export interface MetricItem {
  theme: string;
  count: number;
  average_rating: number;
  root_cause?: string;
  opportunity_score?: number;
  evidence?: string[];
}

export interface DiscoveryChallenge {
  pain_point: string;
  count: number;
  frequency_within_segment: number;
}

export interface UnderservedSegment {
  segment: string;
  count: number;
  pct_sample: number;
  average_rating: number;
  pct_negative_reviews: number;
  priority_score: number;
  priority_rank: number;
  discovery_challenges: DiscoveryChallenge[];
}

export interface Opportunity {
  problem: string;
  evidence: string;
  suggested_ai_solution: string;
  expected_impact: string;
}

export interface SentimentDistribution {
  positive_count: number;
  neutral_count: number;
  negative_count: number;
  positive_pct: number;
  neutral_pct: number;
  negative_pct: number;
  total_reviews: number;
}

export interface DashboardMetrics {
  repeat_purchase_drivers: MetricItem[];
  exploration_barriers: MetricItem[];
  discovery_methods: MetricItem[];
  habit_drivers: MetricItem[];
  information_needs: MetricItem[];
  top_frustrations: MetricItem[];
  underserved_segments: UnderservedSegment[];
  unmet_needs: MetricItem[];
  opportunities: Opportunity[];
}

export interface DashboardData {
  week_ending: string;
  pulse_note_text: string;
  total_reviews_analyzed: number;
  product_discovery_relevant_reviews: number;
  sentiment_distribution: SentimentDistribution;
  metrics: DashboardMetrics;
}
