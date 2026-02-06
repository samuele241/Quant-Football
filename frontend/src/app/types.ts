export interface PlayerDetailData {
  player: string;
  trend_slope: number;
  advanced_metrics?: {
    conversion_rate: number;
    goals_per_90: number;
    total_shots: number;
    xg_diff: number;
    fair_value: number; // Fair Value in €
  };
  history: Array<{
    date: string;
    goals: number;
    xg: number;
    team: string;
    opponent?: string;
  }>;
}

export interface PlayerData {
  player: string;
  goals: number;
  quant_efficiency_score: number;
}

export interface StatCardProps {
  title: string;
  player: string;
  score: number;
  type: 'top' | 'flop';
}

export interface SimilarPlayer {
  player: string;
  team: string;
  match_score: number;
  goals_90: number;
  xg_90: number;
  fair_value?: number; // Fair Value dalla API (già incluso in data.fair_value)
  data?: {
    goals_p90: number;
    xg_p90: number;
    assists_p90: number;
    efficiency: number;
    fair_value?: number; // Fair Value nel campo data
  };
}

