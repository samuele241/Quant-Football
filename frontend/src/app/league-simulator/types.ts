export interface TeamForecast {
  win_league_pct: number;
  top4_pct: number;
  relegation_pct: number;
  avg_points: number;
  avg_position: number;
  current_points: number;
  current_elo: number;
}

export interface ForecastData {
  [teamName: string]: TeamForecast;
}

export interface LeagueSimulatorResponse {
  cached: boolean;
  season: string;
  simulations: number;
  forecast: ForecastData;
}

export interface TeamWithPosition extends TeamForecast {
  name: string;
  position?: number;
}
