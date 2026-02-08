"use client";

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Calendar,
  Shield,
  Target,
  Info,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { AreaChart, Area, ReferenceLine } from 'recharts';
import type { PlayerDetailData } from '../../types';

const ACCENT_GREEN = '#00ff85';
const ACCENT_BLUE = '#3b82f6';
const TEXT_MUTED = '#64748b';

type MatchData = {
  date: string;
  goals: number;
  xg: number;
  team: string;
  opponent?: string;
};

type PredictionPoint = {
  total_goals: number;
  probability: number;
};

type PredictionResponse = {
  current_goals?: number;
  matches_remaining?: number;
  simulation?: PredictionPoint[];
};

const PredictionChart: React.FC<{ playerName: string; currentGoals: number; season: string }> = ({ playerName, currentGoals, season }) => {
  const [data, setData] = useState<PredictionPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [serverCurrent, setServerCurrent] = useState<number>(currentGoals);

  useEffect(() => {
    let mounted = true;
    const fetchPrediction = async () => {
      setLoading(true);
      setError(null);
      try {
        const resp = await fetch(`http://127.0.0.1:8000/analytics/prediction/${encodeURIComponent(playerName)}?season=${encodeURIComponent(season)}`);
        if (!resp.ok) throw new Error('Prediction API error');
        const json: PredictionResponse = await resp.json();
        if (!mounted) return;
        const sim = Array.isArray(json.simulation) ? json.simulation : [];
        // Normalize to numbers and sort by total_goals
        const normalized = sim
          .map(s => ({ total_goals: Number(s.total_goals), probability: Number(s.probability) }))
          .sort((a,b) => a.total_goals - b.total_goals);

        // Prefer server-reported current_goals when available
        const serverCurrent = typeof (json as any).current_goals === 'number' ? Number((json as any).current_goals) : currentGoals;

        // Remove simulation points that are less than serverCurrent (we only show probabilities to finish >= current)
        const filtered = normalized.filter(p => p.total_goals >= serverCurrent);

        // Convert probability to percentage for better readability in the chart (0..100)
        const percentified = filtered.map(p => ({ total_goals: p.total_goals, probability: p.probability * 100 }));
        setData(percentified);
        // update serverCurrent state for reference line / label
        setServerCurrent(serverCurrent);
      } catch (err: any) {
        console.error('Prediction fetch error', err);
        if (!mounted) return;
        setError(err?.message ?? 'Errore prediction');
        setData([]);
      } finally {
        if (!mounted) return;
        setLoading(false);
      }
    };
    if (playerName) fetchPrediction();
    return () => { mounted = false; };
  }, [playerName, season]);

  if (loading) return <div className="h-56 flex items-center justify-center text-sm text-slate-400">Loading projection…</div>;
  if (error) return <div className="h-56 flex items-center justify-center text-sm text-red-400">{error}</div>;
  if (!data.length) return <div className="h-56 flex items-center justify-center text-sm text-slate-400">No projection beyond current goals.</div>;

  return (
    <div className="w-full h-72">{/* increased height for readability */}
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 18, right: 24, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="gradSim" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#7c3aed" stopOpacity={0.85} />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" />
          <XAxis dataKey="total_goals" stroke="#94a3b8" fontSize={11} />
          <YAxis stroke="#94a3b8" fontSize={11} tickFormatter={(v) => `${v.toFixed(0)}%`} width={60} />
          <Tooltip contentStyle={{ backgroundColor: '#0f172a' }} formatter={(value: any) => [`${Number(value).toFixed(1)}%`, 'Probability']} labelFormatter={(label) => `Finish with ${label} goals`} />
          <ReferenceLine x={serverCurrent} stroke={ACCENT_GREEN} strokeDasharray="4 4" label={{ value: `Current: ${serverCurrent}`, position: 'top', fill: '#10b981' }} />
          <Area type="monotone" dataKey="probability" stroke="#7c3aed" fill="url(#gradSim)" fillOpacity={0.9} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

const PlayerPage: React.FC = () => {
  const params = useParams();
  const router = useRouter();
  const rawId = params?.id as string | undefined;
  const playerName = rawId ? decodeURIComponent(rawId) : '';

  const [data, setData] = useState<PlayerDetailData | null>(null);
  const [history, setHistory] = useState<MatchData[]>([]);
  const [contextData, setContextData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<string>('2025');

  useEffect(() => {
    let mounted = true;
    const fetchPlayerData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/analytics/player/${encodeURIComponent(playerName)}?season=${encodeURIComponent(selectedSeason)}`
        );
        if (!response.ok) {
          throw new Error(`Player ${playerName} not found`);
        }
        const json: PlayerDetailData = await response.json();
        if (!mounted) return;
        setData(json);
        setHistory(Array.isArray(json.history) ? json.history : []);
        
        // Fetch context data
        try {
          const contextResponse = await fetch(
            `http://127.0.0.1:8000/analytics/player/${encodeURIComponent(playerName)}/context?season=${encodeURIComponent(selectedSeason)}`
          );
          if (contextResponse.ok) {
            const contextJson = await contextResponse.json();
            if (mounted) setContextData(contextJson);
          }
        } catch (e) {
          console.log('Context data not available');
        }
      } catch (err: any) {
        console.error('Error fetching player data', err);
        if (!mounted) return;
        setError(err?.message ?? 'Errore durante la fetch');
        setData(null);
        setHistory([]);
      } finally {
        if (!mounted) return;
        setLoading(false);
      }
    };

    if (playerName) fetchPlayerData();
    else {
      setLoading(false);
      setError('Player ID mancante');
    }

    return () => {
      mounted = false;
    };
  }, [playerName, selectedSeason]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a]">
        <div className="w-12 h-12 border-4 border-[#00ff85]/20 border-t-[#00ff85] rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0a0a]">
        <div className="max-w-md text-center p-6 glass rounded-lg">
          <h3 className="text-lg font-bold mb-4">Errore</h3>
          <p className="text-sm text-slate-300 mb-6">{error ?? 'Dati giocatore non disponibili.'}</p>
          <div className="flex justify-center">
            <button
              onClick={() => router.push('/')}
              className="px-4 py-2 bg-[#00ff85] text-black rounded-lg font-bold"
            >
              Torna alla Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  const isBullish = data.trend_slope > 0;
  const birthDate = data.birth_date ? new Date(data.birth_date) : null;
  const age = birthDate
    ? Math.floor((Date.now() - birthDate.getTime()) / (365.25 * 24 * 60 * 60 * 1000))
    : null;
  const birthDateLabel = birthDate
    ? birthDate.toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' })
    : null;

  // Advanced metrics provided by API (con Fair Value!)
  const adv = data.advanced_metrics ?? {
    conversion_rate: 0,
    goals_per_90: 0,
    total_shots: 0,
    xg_diff: 0,
    fair_value: 0,
  } as {
    conversion_rate: number;
    goals_per_90: number;
    total_shots: number;
    xg_diff: number;
    fair_value: number;
    fair_value_updated_at?: string | null;
  };

  // Build a contextual System Note based on season advanced metrics and trend
  const systemNotes: string[] = [];
  if (adv.xg_diff >= 1.0) {
    systemNotes.push(`Overperforming vs xG by ${adv.xg_diff.toFixed(2)} goals this season.`);
  } else if (adv.xg_diff <= -1.0) {
    systemNotes.push(`Underperforming vs xG by ${Math.abs(adv.xg_diff).toFixed(2)} goals — finishing conversion may be low.`);
  } else {
    systemNotes.push(`Performance roughly in line with xG (${adv.xg_diff >= 0 ? '+' : ''}${adv.xg_diff.toFixed(2)}).`);
  }

  if (adv.conversion_rate >= 15) {
    systemNotes.push(`High conversion rate (${adv.conversion_rate.toFixed(1)}%). Likely clinical inside the box.`);
  } else if (adv.conversion_rate <= 5) {
    systemNotes.push(`Low conversion rate (${adv.conversion_rate.toFixed(1)}%) — finishing could improve.`);
  }

  if (adv.goals_per_90 >= 0.5) {
    systemNotes.push(`Strong scoring frequency: ${adv.goals_per_90.toFixed(2)} goals/90.`);
  }

  if (data.trend_slope >= 0.5) systemNotes.push('Player is in hot form (positive trend).');
  else if (data.trend_slope <= -0.5) systemNotes.push('Player is in a downturn (negative trend).');

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-[#0a0a0a] text-slate-100">
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[1000px] h-[600px] bg-[#00ff85]/5 blur-[120px] rounded-full opacity-30" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        <button onClick={() => router.back()} className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors mb-12 group">
          <div className="w-8 h-8 rounded-full bg-white/5 flex items-center justify-center group-hover:bg-[#00ff85]/10 group-hover:text-[#00ff85] transition-all">
            <ArrowLeft className="w-4 h-4" />
          </div>
          <span className="text-sm font-medium tracking-tight uppercase font-mono">Back to Analytics</span>
        </button>

        <header className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-16">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 mb-4">
              <Shield className="w-3 h-3 text-slate-400" />
              <span className="text-[10px] font-bold tracking-widest text-slate-400 uppercase">Serie A Enilive</span>
            </div>
            <div className="flex flex-col md:flex-row md:items-end md:gap-6">
              <h1 className="text-6xl md:text-8xl font-black tracking-tighter leading-none mb-4 uppercase">
                {data.player.split(' ').map((part, i) => (
                  <span key={i} className={i === 1 ? 'text-[#00ff85] block' : 'text-white block'}>
                    {part}
                  </span>
                ))}
              </h1>
              <div className="glass rounded-3xl p-6 border border-white/5 bg-gradient-to-br from-white/[0.04] to-transparent md:mb-4 md:w-[280px]">
                <div className="flex items-center gap-3 mb-4">
                  <div className="p-2 bg-white/10 rounded-lg">
                    <Calendar className="w-5 h-5 text-slate-300" />
                  </div>
                  <h4 className="font-bold text-slate-200">Age Profile</h4>
                </div>
                <div className="flex items-end justify-between">
                  <div>
                    <div className="text-5xl font-black text-white leading-none">{age ?? '—'}</div>
                    <div className="text-xs text-slate-400 uppercase font-bold tracking-wider mt-1">Years</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-400 uppercase font-bold tracking-wider">Birth Date</div>
                    <div className="text-sm font-semibold text-slate-200 mt-1">
                      {birthDateLabel ?? 'Not available'}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setSelectedSeason('2024')}
                className={`px-3 py-1 rounded-lg text-sm font-semibold ${selectedSeason === '2024' ? 'bg-[#00ff85] text-slate-900 shadow-[0_0_10px_rgba(0,255,133,0.2)]' : 'bg-white/5 text-slate-300'}`}
              >
                2024 / 2025
              </button>
              <button
                onClick={() => setSelectedSeason('2025')}
                className={`px-3 py-1 rounded-lg text-sm font-semibold ${selectedSeason === '2025' ? 'bg-[#00ff85] text-slate-900 shadow-[0_0_10px_rgba(0,255,133,0.2)]' : 'bg-white/5 text-slate-300'}`}
              >
                2025 / 2026
              </button>
            </div>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <span className="text-[10px] font-bold text-slate-500 tracking-widest uppercase">Current Quant Trend</span>
            <div className={`flex items-center gap-3 px-6 py-4 rounded-2xl glass border-2 ${
              isBullish ? 'border-[#00ff85]/30 bg-[#00ff85]/5' : 'border-red-500/30 bg-red-500/5'
            }`}>
              <div className={`p-2 rounded-xl ${isBullish ? 'bg-[#00ff85]/20' : 'bg-red-500/20'}`}>
                {isBullish ? <TrendingUp className="w-6 h-6 text-[#00ff85]" /> : <TrendingDown className="w-6 h-6 text-red-500" />}
              </div>
              <div>
                <div className={`text-2xl font-bold font-mono ${isBullish ? 'text-[#00ff85]' : 'text-red-500'}`}>{isBullish ? '+' : ''}{data.trend_slope.toFixed(2)}</div>
                <div className="text-[10px] text-slate-400 uppercase font-bold">Efficiency Vector</div>
              </div>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          <div className="lg:col-span-2 glass rounded-3xl p-8 border border-white/5">
            <div className="flex items-center justify-between mb-10">
              <div>
                <h3 className="text-xl font-bold mb-1">Performance Matrix</h3>
                <p className="text-sm text-slate-400">Comparing actual Goals vs Expected Goals (xG)</p>
              </div>
              <div className="flex gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-[#00ff85]" />
                  <span className="text-xs font-mono text-slate-300">Goals</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full border border-slate-500" />
                  <span className="text-xs font-mono text-slate-500">xG</span>
                </div>
              </div>
            </div>

            <div className="h-[350px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <CartesianGrid strokeDasharray="5 5" stroke="rgba(255,255,255,0.03)" vertical={false} />
                  <XAxis dataKey="date" stroke="#475569" fontSize={10} tickFormatter={(val) => new Date(val).toLocaleDateString('it-IT', { day: '2-digit', month: 'short' })} tickMargin={10} />
                  <YAxis stroke="#475569" fontSize={10} tickMargin={10} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)', boxShadow: '0 20px 40px rgba(0,0,0,0.4)' }} itemStyle={{ fontSize: '12px' }} />
                  <Line type="monotone" dataKey="goals" stroke={ACCENT_GREEN} strokeWidth={4} dot={{ fill: ACCENT_GREEN, r: 4, strokeWidth: 2, stroke: '#0a0a0a' }} activeDot={{ r: 6, fill: ACCENT_GREEN }} />
                  <Line type="monotone" dataKey="xg" stroke="#64748b" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Season Projection (Monte Carlo) */}
            <div className="mt-8 glass rounded-2xl p-6 border border-white/5 bg-gradient-to-br from-white/[0.02] to-transparent">
              <h4 className="text-lg font-bold mb-4">Season Projection (Monte Carlo)</h4>
              <PredictionChart playerName={data.player} currentGoals={data && history ? history.reduce((s, m) => s + (m.goals || 0), 0) : 0} season={selectedSeason} />
            </div>
          </div>

          <div className="flex flex-col gap-6">
            {/* Fair Value Card (NEW!) */}
            <div className="glass rounded-3xl p-6 border border-green-500/20 bg-gradient-to-br from-green-500/5 to-transparent">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-green-500/20 rounded-lg">
                  <Target className="w-5 h-5 text-green-400" />
                </div>
                <h4 className="font-bold text-green-400">Market Value</h4>
              </div>
              <div className="text-center py-4">
                <div className="text-5xl font-black text-green-400 mb-2">
                  €{(adv.fair_value / 1_000_000).toFixed(1)}M
                </div>
                <div className="text-xs text-slate-500 uppercase font-bold tracking-wider">
                  Estimated Fair Value
                </div>
              </div>
              <div className="mt-4 pt-4 border-t border-white/5 text-xs text-slate-400 text-center">
                Based on performance metrics & market standards
                {adv.fair_value_updated_at && (
                  <div className="mt-1 text-[10px] text-slate-500">
                    Updated {new Date(adv.fair_value_updated_at).toLocaleDateString('it-IT')}
                  </div>
                )}
              </div>
            </div>

            <div className="glass rounded-3xl p-6 border border-white/5 flex-1">
              <div className="flex items-center gap-3 mb-6">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Target className="w-5 h-5 text-blue-500" />
                </div>
                <h4 className="font-bold">Finishing Analysis</h4>
              </div>
              <div className="space-y-6">
                <div>
                  <div className="flex justify-between text-xs mb-2">
                    <span className="text-slate-500 uppercase font-bold tracking-wider">Conversion Rate</span>
                    <span className="font-mono text-[#00ff85]">{adv.conversion_rate.toFixed(1)}%</span>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full bg-[#00ff85]" style={{ width: `${Math.min(100, adv.conversion_rate)}%` }} />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 uppercase font-bold tracking-wider">Goals per 90'</div>
                    <div className="text-2xl font-bold mt-1">{adv.goals_per_90.toFixed(2)}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-slate-500 uppercase font-bold tracking-wider">Total Shots</div>
                    <div className="text-2xl font-bold mt-1">{adv.total_shots}</div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center text-xs mb-2">
                    <span className="text-slate-500 uppercase font-bold tracking-wider">xG Performance</span>
                    <span className={`font-mono ${adv.xg_diff >= 0 ? 'text-[#00ff85]' : 'text-red-400'}`}>{adv.xg_diff >= 0 ? '+' : ''}{adv.xg_diff.toFixed(2)}</span>
                  </div>
                  <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                    <div className={`h-full ${adv.xg_diff >= 0 ? 'bg-[#00ff85]' : 'bg-red-500'}`} style={{ width: `${Math.min(100, Math.abs(adv.xg_diff) * 10)}%` }} />
                  </div>
                </div>
              </div>
            </div>

            <div className="bg-[#00ff85] rounded-3xl p-8 flex flex-col justify-between">
              <div className="flex justify-between items-start text-slate-950">
                <Info className="w-6 h-6" />
                <span className="text-[10px] font-black uppercase tracking-widest border border-slate-950/20 px-2 py-1 rounded">System Note</span>
              </div>
              <ul className="mt-6 space-y-2 text-slate-950">
                {systemNotes.map((note, i) => (
                  <li key={i} className="font-bold text-sm">{note}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Context Analytics Section */}
        {contextData && (
          <div className="mb-12">
            <div className="flex items-center gap-3 mb-6">
              <div className="p-2 bg-purple-500/10 rounded-lg">
                <Shield className="w-5 h-5 text-purple-400" />
              </div>
              <h3 className="text-2xl font-bold">Opposition Analysis</h3>
              <span className="text-xs text-slate-500 uppercase font-bold tracking-wider px-2 py-1 bg-white/5 rounded">Advanced Context</span>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Difficulty Score */}
              <div className="glass rounded-3xl p-6 border border-purple-500/20">
                <div className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Calendar Difficulty</div>
                <div className="text-4xl font-black text-purple-400 mb-2">
                  {contextData.summary.difficulty_score.toFixed(0)}
                  <span className="text-lg text-slate-500">/100</span>
                </div>
                <div className="text-xs text-slate-400">
                  Avg Opponent ELO: {contextData.summary.avg_opponent_elo}
                </div>
                <div className="mt-4 h-2 bg-white/5 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500" 
                    style={{ width: `${contextData.summary.difficulty_score}%` }} 
                  />
                </div>
              </div>

              {/* Goal Quality */}
              <div className="glass rounded-3xl p-6 border border-cyan-500/20">
                <div className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">Goal Quality Index</div>
                <div className="text-4xl font-black text-cyan-400 mb-2">
                  {contextData.summary.goal_quality_index.toFixed(2)}
                  <span className="text-lg text-slate-500">x</span>
                </div>
                <div className="text-xs text-slate-400">
                  {contextData.summary.goal_quality_index > 1.0 
                    ? 'Scores vs strong teams' 
                    : 'More goals vs weaker sides'}
                </div>
              </div>

              {/* Splits */}
              <div className="glass rounded-3xl p-6 border border-orange-500/20">
                <div className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">vs Top Teams</div>
                <div className="text-4xl font-black text-orange-400 mb-2">
                  {contextData.splits.vs_top_teams.goals}
                  <span className="text-lg text-slate-500">G</span>
                </div>
                <div className="text-xs text-slate-400">ELO ≥ 1600</div>
              </div>

              <div className="glass rounded-3xl p-6 border border-green-500/20">
                <div className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-2">vs Bottom Teams</div>
                <div className="text-4xl font-black text-green-400 mb-2">
                  {contextData.splits.vs_bottom_teams.goals}
                  <span className="text-lg text-slate-500">G</span>
                </div>
                <div className="text-xs text-slate-400">ELO ≤ 1450</div>
              </div>
            </div>

            {/* Fair Value Adjustment */}
            {contextData.summary.fair_value_difficulty_adj !== 0 && (
              <div className="mt-6 glass rounded-2xl p-6 border border-yellow-500/20 bg-yellow-500/5">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-slate-500 uppercase font-bold tracking-wider mb-1">Fair Value Difficulty Adjustment</div>
                    <div className="text-sm text-slate-300">
                      Based on strength of opposition faced
                    </div>
                  </div>
                  <div className={`text-3xl font-black ${contextData.summary.fair_value_difficulty_adj > 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {contextData.summary.fair_value_difficulty_adj > 0 ? '+' : ''}{contextData.summary.fair_value_difficulty_adj.toFixed(1)}%
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <div className="glass rounded-3xl border border-white/5 overflow-hidden">
          <div className="px-8 py-6 border-b border-white/5 bg-white/[0.01]">
            <h3 className="font-bold flex items-center gap-2">
              <Calendar className="w-4 h-4 text-slate-500" />
              Recent Match History
            </h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="text-[10px] font-black uppercase tracking-widest text-slate-500 bg-white/[0.02]">
                  <th className="px-8 py-4">Date</th>
                  <th className="px-8 py-4">Opponent</th>
                  <th className="px-8 py-4">Goals</th>
                  <th className="px-8 py-4">Expected Goals (xG)</th>
                  <th className="px-8 py-4 text-right">Impact</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {history.slice().reverse().map((match, idx) => (
                  <tr key={idx} className="group hover:bg-white/[0.02] transition-colors">
                    <td className="px-8 py-5 font-mono text-sm text-slate-400">{new Date(match.date).toLocaleDateString('it-IT')}</td>
                    <td className="px-8 py-5 font-bold">{match.opponent ?? 'Unknown'}</td>
                    <td className="px-8 py-5"><span className={`text-sm font-bold ${match.goals > 0 ? 'text-[#00ff85]' : 'text-slate-500'}`}>{match.goals}</span></td>
                    <td className="px-8 py-5"><span className="font-mono text-sm text-slate-400">{match.xg.toFixed(2)}</span></td>
                    <td className="px-8 py-5 text-right"><div className={`inline-flex h-2 w-2 rounded-full ${match.goals > match.xg ? 'bg-[#00ff85] shadow-[0_0_10px_#00ff85]' : 'bg-slate-700'}`} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </motion.div>
  );
};

export default PlayerPage;
