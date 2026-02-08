"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  Trophy, 
  Zap, 
  AlertCircle, 
  RefreshCcw, 
  ArrowLeft,
  Package2
} from 'lucide-react';
import { TeamCard } from './components/TeamCard';
import { LoadingSkeleton } from './components/LoadingSkeleton';
import type { LeagueSimulatorResponse, ForecastData } from './types';

const API_BASE = "http://127.0.0.1:8000";

const LeagueSimulator: React.FC = () => {
  const router = useRouter();
  const [forecast, setForecast] = useState<ForecastData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [simulations, setSimulations] = useState(10000);
  const [pendingSimulations, setPendingSimulations] = useState(10000);
  const [sortBy, setSortBy] = useState<'win' | 'top4' | 'relegation'>('win');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [cached, setCached] = useState(false);

  const fetchForecast = useCallback(async (sims: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/analytics/league-forecast?simulations=${sims}&use_cache=true`
      );
      
      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data: LeagueSimulatorResponse = await response.json();
      setForecast(data.forecast);
      setCached(data.cached);
      setSimulations(sims);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to fetch league forecast';
      setError(errorMsg);
      console.error('API Error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchForecast(simulations);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Debounced simulation change
  useEffect(() => {
    const timer = setTimeout(() => {
      if (pendingSimulations !== simulations) {
        fetchForecast(pendingSimulations);
      }
    }, 500);

    return () => clearTimeout(timer);
  }, [pendingSimulations, simulations, fetchForecast]);

  const handleSimulationChange = (value: string) => {
    const newValue = parseInt(value);
    setPendingSimulations(newValue);
  };

  const handleRefresh = () => {
    fetchForecast(simulations);
  };

  // Get teams sorted by category
  const getTopByCategory = (category: 'win' | 'top4' | 'relegation', limit: number = 3) => {
    if (!forecast) return [];
    return Object.entries(forecast)
      .map(([name, data]) => {
        let probability = 0;
        if (category === 'win') {
          probability = data.win_league_pct;
        } else if (category === 'top4') {
          probability = data.top4_pct;
        } else {
          probability = data.relegation_pct;
        }
        return {
          name,
          probability,
          ...data
        };
      })
      .sort((a, b) => b.probability - a.probability)
      .slice(0, limit);
  };

  const topWinners = getTopByCategory('win', 3);
  const topTop4 = getTopByCategory('top4', 4);
  const topRelegation = getTopByCategory('relegation', 3);

  // Full rankings with sorting
  const sortedWinners = useMemo(() => {
    if (!forecast) return [];
    const teams = Object.entries(forecast)
      .map(([name, data], idx) => ({
        name,
        position: idx + 1,
        ...data
      }))
      .sort((a, b) => {
        let aVal = 0, bVal = 0;
        if (sortBy === 'win') {
          aVal = a.win_league_pct;
          bVal = b.win_league_pct;
        } else if (sortBy === 'top4') {
          aVal = a.top4_pct;
          bVal = b.top4_pct;
        } else {
          aVal = a.relegation_pct;
          bVal = b.relegation_pct;
        }
        return sortOrder === 'desc' ? bVal - aVal : aVal - bVal;
      });
    return teams;
  }, [forecast, sortBy, sortOrder]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-slate-100">
      {/* Background Elements */}
      <div className="fixed inset-0 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-blue-500/10 blur-[120px] rounded-full" />
        <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-emerald-500/10 blur-[120px] rounded-full" />
        <div className="absolute top-1/2 right-0 w-96 h-96 bg-purple-500/5 blur-[120px] rounded-full" />
      </div>

      {/* Navbar */}
      <motion.nav 
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="fixed top-0 w-full z-50 px-6 md:px-12 py-4 flex items-center justify-between bg-slate-950/80 backdrop-blur border-b border-white/5"
      >
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push('/dashboard')}
            className="p-2 hover:bg-slate-800 rounded-lg transition-colors"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-5 h-5 text-slate-400" />
          </button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-500 rounded-lg flex items-center justify-center shadow-lg">
              <Zap className="w-5 h-5 text-white" />
            </div>
            <span className="font-black text-lg">League Simulator</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {cached && (
            <motion.div
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-emerald-500/20 border border-emerald-500/30 rounded-full"
            >
              <Package2 className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs font-semibold text-emerald-300">Cached</span>
            </motion.div>
          )}
          
          <select
            value={pendingSimulations}
            onChange={(e) => handleSimulationChange(e.target.value)}
            disabled={loading}
            className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm font-medium hover:border-slate-600 disabled:opacity-50 transition-colors"
          >
            <option value="1000">1,000 sims</option>
            <option value="5000">5,000 sims</option>
            <option value="10000">10,000 sims</option>
            <option value="50000">50,000 sims</option>
          </select>

          <button
            onClick={handleRefresh}
            disabled={loading}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors disabled:opacity-50"
            title="Refresh forecast"
          >
            <RefreshCcw className={`w-5 h-5 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </motion.nav>

      {/* Main Content */}
      <main className="relative z-10 pt-24 px-6 md:px-12 pb-12 max-w-7xl mx-auto">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-black uppercase tracking-tight mb-2 italic">
            🏆 League Simulator
          </h1>
          <p className="text-slate-400">
            Monte Carlo simulation with {simulations.toLocaleString()} iterations. Predictions for Serie A 2024/25 season.
          </p>
        </motion.div>

        {/* Error State */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-8 p-4 bg-red-500/20 border border-red-500/30 rounded-lg flex items-start gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-red-200 mb-1">Error loading forecast</h3>
              <p className="text-sm text-red-300">{error}</p>
            </div>
          </motion.div>
        )}

        {/* Three-Column Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-12">
          {/* Column 1: Win League */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <div className="sticky top-28 bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700/50 shadow-2xl">
              <div className="flex items-center gap-2 mb-6">
                <Trophy className="w-6 h-6 text-yellow-400" />
                <h2 className="text-xl font-black uppercase tracking-tight">Win League</h2>
              </div>

              {loading ? (
                <LoadingSkeleton />
              ) : (
                <motion.div className="space-y-3">
                  {topWinners.map((team, idx) => (
                    <TeamCard
                      key={team.name}
                      index={idx}
                      position={idx + 1}
                      name={team.name}
                      probability={team.probability}
                      currentElo={team.current_elo}
                      currentPoints={team.current_points}
                      avgPoints={team.avg_points}
                      avgPosition={team.avg_position}
                      type="winner"
                    />
                  ))}
                </motion.div>
              )}
            </div>
          </motion.div>

          {/* Column 2: Top 4 Champions League */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="sticky top-28 bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700/50 shadow-2xl">
              <div className="flex items-center gap-2 mb-6">
                <Zap className="w-6 h-6 text-blue-400" />
                <h2 className="text-xl font-black uppercase tracking-tight">Top 4 CL</h2>
              </div>

              {loading ? (
                <LoadingSkeleton />
              ) : (
                <motion.div className="space-y-3">
                  {topTop4.map((team, idx) => (
                    <TeamCard
                      key={team.name}
                      index={idx}
                      position={idx + 1}
                      name={team.name}
                      probability={team.top4_pct}
                      currentElo={team.current_elo}
                      currentPoints={team.current_points}
                      avgPoints={team.avg_points}
                      avgPosition={team.avg_position}
                      type="top4"
                    />
                  ))}
                </motion.div>
              )}
            </div>
          </motion.div>

          {/* Column 3: Relegation */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <div className="sticky top-28 bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700/50 shadow-2xl">
              <div className="flex items-center gap-2 mb-6">
                <AlertCircle className="w-6 h-6 text-red-400" />
                <h2 className="text-xl font-black uppercase tracking-tight">Relegation</h2>
              </div>

              {loading ? (
                <LoadingSkeleton />
              ) : (
                <motion.div className="space-y-3">
                  {topRelegation.map((team, idx) => (
                    <TeamCard
                      key={team.name}
                      index={idx}
                      position={idx + 1}
                      name={team.name}
                      probability={team.relegation_pct}
                      currentElo={team.current_elo}
                      currentPoints={team.current_points}
                      avgPoints={team.avg_points}
                      avgPosition={team.avg_position}
                      type="relegation"
                    />
                  ))}
                </motion.div>
              )}
            </div>
          </motion.div>
        </div>

        {/* Full Table Section */}
        {forecast && !loading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl p-6 border border-slate-700/50 shadow-2xl">
              <div className="mb-6 flex items-center justify-between flex-wrap gap-4">
                <h2 className="text-2xl font-black uppercase tracking-tight">Full Rankings</h2>
                <div className="flex gap-2">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-sm font-medium hover:border-slate-500 transition-colors"
                  >
                    <option value="win">Sort by Win %</option>
                    <option value="top4">Sort by Top 4 %</option>
                    <option value="relegation">Sort by Relegation %</option>
                  </select>
                  <button
                    onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                    className="px-3 py-2 bg-slate-700 hover:bg-slate-600 border border-slate-600 rounded-lg text-sm font-medium transition-colors"
                  >
                    {sortOrder === 'desc' ? '↓ Desc' : '↑ Asc'}
                  </button>
                </div>
              </div>

              <div className="grid grid-cols-1 gap-2 max-h-[600px] overflow-y-auto">
                {sortedWinners.map((team, idx) => (
                  <motion.div
                    key={team.name}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: idx * 0.02 }}
                    className="flex items-center justify-between p-3 bg-slate-750/50 hover:bg-slate-700/50 rounded-lg border border-slate-700/30 transition-colors"
                  >
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <span className="text-sm font-bold text-slate-400 w-8 flex-shrink-0">#{idx + 1}</span>
                      <span className="font-semibold truncate">{team.name.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="flex gap-8 text-sm flex-shrink-0">
                      <div className="text-right">
                        <span className="font-bold text-yellow-400">{team.win_league_pct.toFixed(1)}%</span>
                        <p className="text-xs text-slate-400">Win</p>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-blue-400">{team.top4_pct.toFixed(1)}%</span>
                        <p className="text-xs text-slate-400">Top 4</p>
                      </div>
                      <div className="text-right">
                        <span className="font-bold text-red-400">{team.relegation_pct.toFixed(1)}%</span>
                        <p className="text-xs text-slate-400">Releg</p>
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
};

export default LeagueSimulator;