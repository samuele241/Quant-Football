"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  ArrowLeft,
  Shield,
  TrendingUp,
  TrendingDown,
  Target,
  Zap,
} from 'lucide-react';

interface TeamRanking {
  team: string;
  elo: number;
  attack_form: number;
  defense_form: number;
  form_diff: number;
  last_update: string;
}

const TeamStrengthPage: React.FC = () => {
  const router = useRouter();
  const [rankings, setRankings] = useState<TeamRanking[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedSeason, setSelectedSeason] = useState('2526');

  useEffect(() => {
    const fetchRankings = async () => {
      setLoading(true);
      try {
        const response = await fetch(
          `http://127.0.0.1:8000/analytics/league/strength-rankings?season=${selectedSeason}`
        );
        const data = await response.json();
        setRankings(data.rankings || []);
      } catch (error) {
        console.error('Error fetching rankings:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchRankings();
  }, [selectedSeason]);

  const getEloColor = (elo: number) => {
    if (elo >= 1700) return 'text-yellow-400';
    if (elo >= 1600) return 'text-green-400';
    if (elo >= 1500) return 'text-cyan-400';
    if (elo >= 1400) return 'text-slate-400';
    return 'text-red-400';
  };

  const getEloLabel = (elo: number) => {
    if (elo >= 1700) return 'Elite';
    if (elo >= 1600) return 'Strong';
    if (elo >= 1500) return 'Average';
    if (elo >= 1400) return 'Weak';
    return 'Struggling';
  };

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 pt-24 pb-20 px-6">
      <div className="max-w-7xl mx-auto">
        
        {/* Back Button */}
        <motion.button
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={() => router.push('/dashboard')}
          className="mb-8 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-cyan-500/30 transition-all group"
        >
          <ArrowLeft className="w-4 h-4 text-cyan-400 group-hover:text-cyan-300 transition-colors" />
          <span className="text-sm font-bold text-slate-300 group-hover:text-white transition-colors">Back to Dashboard</span>
        </motion.button>

        {/* Header */}
        <div className="mb-12">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-cyan-500/10 border border-cyan-500/20 mb-6"
          >
            <Shield className="w-4 h-4 text-cyan-400" />
            <span className="text-[10px] font-black tracking-widest text-cyan-400 uppercase">
              Team Strength Analytics
            </span>
          </motion.div>
          
          <h1 className="text-5xl md:text-7xl font-black tracking-tighter uppercase italic mb-4">
            <span className="text-white">ELO</span>{' '}
            <span className="bg-gradient-to-r from-cyan-400 to-purple-400 bg-clip-text text-transparent">Rankings</span>
          </h1>
          
          <p className="text-slate-400 text-lg max-w-2xl">
            Live team strength rankings based on ELO rating system and recent form. Higher ELO = stronger opponent.
          </p>

          {/* Season Selector */}
          <div className="flex gap-3 mt-6">
            <button
              onClick={() => setSelectedSeason('2425')}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                selectedSeason === '2425'
                  ? 'bg-cyan-500 text-slate-900 shadow-[0_0_20px_rgba(6,182,212,0.3)]'
                  : 'bg-white/5 text-slate-400 hover:bg-white/10'
              }`}
            >
              2024/25
            </button>
            <button
              onClick={() => setSelectedSeason('2526')}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                selectedSeason === '2526'
                  ? 'bg-cyan-500 text-slate-900 shadow-[0_0_20px_rgba(6,182,212,0.3)]'
                  : 'bg-white/5 text-slate-400 hover:bg-white/10'
              }`}
            >
              2025/26
            </button>
          </div>
        </div>

        {/* Rankings Table */}
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="w-12 h-12 border-4 border-cyan-400/20 border-t-cyan-400 rounded-full animate-spin" />
          </div>
        ) : (
          <div className="glass rounded-3xl border border-white/5 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-[10px] font-black uppercase tracking-widest text-slate-500 bg-white/[0.02] border-b border-white/5">
                    <th className="px-6 py-4 text-left">Rank</th>
                    <th className="px-6 py-4 text-left">Team</th>
                    <th className="px-6 py-4 text-center">ELO</th>
                    <th className="px-6 py-4 text-center">Category</th>
                    <th className="px-6 py-4 text-center">Attack Form</th>
                    <th className="px-6 py-4 text-center">Defense Form</th>
                    <th className="px-6 py-4 text-center">Form Diff</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {rankings.map((team, index) => (
                    <motion.tr
                      key={team.team}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: index * 0.02 }}
                      className="group hover:bg-white/[0.02] transition-colors"
                    >
                      <td className="px-6 py-5">
                        <div className="flex items-center gap-2">
                          <span className={`text-lg font-black ${
                            index === 0 ? 'text-yellow-400' :
                            index === 1 ? 'text-slate-300' :
                            index === 2 ? 'text-orange-400' :
                            'text-slate-500'
                          }`}>
                            {index + 1}
                          </span>
                          {index < 3 && <Zap className="w-4 h-4 text-yellow-400" />}
                        </div>
                      </td>
                      <td className="px-6 py-5">
                        <div className="font-bold text-base">{team.team.replace('_', ' ')}</div>
                      </td>
                      <td className="px-6 py-5 text-center">
                        <span className={`text-2xl font-black font-mono ${getEloColor(team.elo)}`}>
                          {team.elo}
                        </span>
                      </td>
                      <td className="px-6 py-5 text-center">
                        <span className={`px-2 py-1 rounded text-xs font-bold uppercase ${
                          team.elo >= 1700 ? 'bg-yellow-500/20 text-yellow-400' :
                          team.elo >= 1600 ? 'bg-green-500/20 text-green-400' :
                          team.elo >= 1500 ? 'bg-cyan-500/20 text-cyan-400' :
                          team.elo >= 1400 ? 'bg-slate-500/20 text-slate-400' :
                          'bg-red-500/20 text-red-400'
                        }`}>
                          {getEloLabel(team.elo)}
                        </span>
                      </td>
                      <td className="px-6 py-5 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Target className="w-4 h-4 text-green-400" />
                          <span className="font-mono text-sm text-green-400">
                            {team.attack_form.toFixed(1)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-5 text-center">
                        <div className="flex items-center justify-center gap-2">
                          <Shield className="w-4 h-4 text-blue-400" />
                          <span className="font-mono text-sm text-blue-400">
                            {team.defense_form.toFixed(1)}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-5 text-center">
                        <div className="flex items-center justify-center gap-1">
                          {team.form_diff > 0 ? (
                            <TrendingUp className="w-4 h-4 text-green-400" />
                          ) : team.form_diff < 0 ? (
                            <TrendingDown className="w-4 h-4 text-red-400" />
                          ) : null}
                          <span className={`font-mono text-sm font-bold ${
                            team.form_diff > 0 ? 'text-green-400' :
                            team.form_diff < 0 ? 'text-red-400' :
                            'text-slate-400'
                          }`}>
                            {team.form_diff > 0 ? '+' : ''}{team.form_diff.toFixed(1)}
                          </span>
                        </div>
                      </td>
                    </motion.tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Legend */}
        <div className="mt-8 glass rounded-2xl p-6 border border-white/5">
          <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">Legend</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="font-bold text-cyan-400">ELO Rating:</span>
              <p className="text-slate-400 mt-1">Chess-based ranking system. 1500 = average, 1800+ = elite.</p>
            </div>
            <div>
              <span className="font-bold text-green-400">Attack Form:</span>
              <p className="text-slate-400 mt-1">Average goals scored in last 5 matches.</p>
            </div>
            <div>
              <span className="font-bold text-blue-400">Defense Form:</span>
              <p className="text-slate-400 mt-1">Average goals conceded in last 5 matches.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TeamStrengthPage;
