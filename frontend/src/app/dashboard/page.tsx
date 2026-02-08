"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Trophy, 
  TrendingUp, 
  TrendingDown, 
  Activity, 
  Target, 
  Zap, 
  ChevronRight,
  AlertCircle,
  RefreshCcw,
  BrainCircuit,
  Shield
} from 'lucide-react';
import { 
  BarChart, 
  Bar, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer, 
  Cell,
  ReferenceLine
} from 'recharts';
import type { PlayerData } from '../types';

// Constants
const ACCENT_GREEN = "#00ff85";
const ACCENT_RED = "#ef4444";

const App: React.FC = () => {
  const [data, setData] = useState<PlayerData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<string>('2025');
  const [teams, setTeams] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedTeamId, setSelectedTeamId] = useState<string>('');
  const [selectedTeamName, setSelectedTeamName] = useState<string>('');
  const router = useRouter();
  const fetchData = async (season: string, teamId?: string) => {
    setLoading(true);
    setError(null);
    try {
      let url = `http://127.0.0.1:8000/analytics/top-scorers?season=${season}`;
      if (teamId) url += `&team_id=${encodeURIComponent(teamId)}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('API connection failed');
      const json = await response.json();
      setData(json);
    } catch (err) {
      console.warn("Backend not available, using demo data");
      // Fallback for demo purposes if backend is not running
      const demoData: PlayerData[] = [
        { "player": "Riccardo Orsolini", "goals": 15, "quant_efficiency_score": 10.89 },
        { "player": "Lautaro Martinez", "goals": 12, "quant_efficiency_score": -5.36 },
        { "player": "Dusan Vlahovic", "goals": 18, "quant_efficiency_score": 7.42 },
        { "player": "Marcus Thuram", "goals": 10, "quant_efficiency_score": 2.15 },
        { "player": "Rafael Leao", "goals": 8, "quant_efficiency_score": -1.24 },
        { "player": "Kenan Yildiz", "goals": 5, "quant_efficiency_score": 12.30 },
        { "player": "Paulo Dybala", "goals": 11, "quant_efficiency_score": 8.91 },
        { "player": "Mateo Retegui", "goals": 14, "quant_efficiency_score": -3.88 }
      ].sort((a, b) => b.quant_efficiency_score - a.quant_efficiency_score);
      setData(demoData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData(selectedSeason, selectedTeamId);
  }, [selectedSeason]);

  // Fetch teams on mount
  useEffect(() => {
    let mounted = true;
    const fetchTeams = async () => {
      try {
        const resp = await fetch('http://127.0.0.1:8000/analytics/teams');
        if (!resp.ok) throw new Error('Teams API error');
        const json = await resp.json();
        if (!mounted) return;
        // Expecting array of { id, name }
        setTeams(Array.isArray(json) ? json : []);
      } catch (err) {
        console.warn('Could not load teams', err);
        setTeams([]);
      }
    };
    fetchTeams();
    return () => { mounted = false; };
  }, []);

  // Refetch when team changes
  useEffect(() => {
    fetchData(selectedSeason, selectedTeamId);
  }, [selectedTeamId]);

  const topPlayer = data.reduce((prev, current) => 
    (prev.quant_efficiency_score > current.quant_efficiency_score) ? prev : current, 
    data[0] || { player: 'N/A', quant_efficiency_score: 0 }
  );

  const flopPlayer = data.reduce((prev, current) => 
    (prev.quant_efficiency_score < current.quant_efficiency_score) ? prev : current, 
    data[0] || { player: 'N/A', quant_efficiency_score: 0 }
  );

  const seasonLabel = selectedSeason === '2024' ? 'Serie A 24/25' : 'Serie A 25/26';

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 selection:bg-[#00ff85]/30">
      {/* Navbar / Header */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5 h-16 flex items-center px-6 md:px-12 justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#00ff85] rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(0,255,133,0.4)]">
            <Activity className="w-5 h-5 text-slate-950" />
          </div>
          <span className="font-bold tracking-tighter text-xl bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">
            QUANT ENGINE
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm font-medium text-slate-400">
          <button onClick={() => router.push('/')} className="hover:text-[#00ff85] transition-colors">DASHBOARD</button>
          <button onClick={() => router.push('/scouting')} className="hover:text-[#00ff85] transition-colors">SCOUTING</button>
          <button onClick={() => router.push('/metrics')} className="hover:text-[#00ff85] transition-colors">METRICS</button>
          <button onClick={() => router.push('/league-simulator')} className="hover:text-[#00ff85] transition-colors">LEAGUE SIMULATOR</button>
          <button 
            onClick={() => fetchData(selectedSeason, selectedTeamId)} 
            className="p-2 hover:bg-white/5 rounded-full transition-colors"
          >
            <RefreshCcw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </nav>

      <main className="pt-24 pb-12 px-6 md:px-12 max-w-7xl mx-auto space-y-12">
        {/* Hero Section */}
        <section className="relative overflow-hidden py-12">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="relative z-10"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00ff85]/10 border border-[#00ff85]/20 mb-6">
              <Zap className="w-4 h-4 text-[#00ff85]" />
              <span className="text-[10px] font-bold tracking-widest text-[#00ff85] uppercase">Live Quant Processing</span>
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-4 leading-none">
              FUTURE <br />
              <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#00ff85] to-emerald-400">FOOTBALL</span> ANALYTICS
            </h1>
            <p className="text-slate-400 text-lg max-w-2xl leading-relaxed">
              Algoritmi avanzati per l'analisi dell'efficienza quantitativa. 
              Tracciamo ogni movimento, ogni tocco, trasformando il gioco nel calcolo puro della vittoria.
            </p>
          </motion.div>
          {/* Background Glow */}
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#00ff85]/5 blur-[120px] rounded-full -z-10" />
        </section>

        {loading ? (
          <LoadingSkeleton />
        ) : (
          <motion.div
            initial="hidden"
            animate="visible"
            variants={{
              visible: { transition: { staggerChildren: 0.1 } }
            }}
            className="space-y-12"
          >
            {/* Stat Cards Grid */}
            {/* Season Selector */}
            <div className="flex items-center gap-3 mb-4">
              <button
                onClick={() => setSelectedSeason('2024')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${selectedSeason === '2024' ? 'bg-[#00ff85] text-slate-900 shadow-[0_0_12px_rgba(0,255,133,0.25)]' : 'bg-white/5 text-slate-300'}`}
              >
                2024 / 2025
              </button>
              <button
                onClick={() => setSelectedSeason('2025')}
                className={`px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${selectedSeason === '2025' ? 'bg-[#00ff85] text-slate-900 shadow-[0_0_12px_rgba(0,255,133,0.25)]' : 'bg-white/5 text-slate-300'}`}
              >
                2025 / 2026
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <StatCard 
                title="TOP QUANT PERFORMANCE" 
                player={topPlayer.player} 
                score={topPlayer.quant_efficiency_score} 
                type="top" 
              />
              <StatCard 
                title="LOWER EFFICIENCY RISK" 
                player={flopPlayer.player} 
                score={flopPlayer.quant_efficiency_score} 
                type="flop" 
              />
              
              {/* Smart Scouting Card - Premium AI Feature */}
              <motion.div 
                variants={itemVariants}
                onClick={() => router.push('/scouting')}
                whileHover={{ y: -8, scale: 1.02 }}
                className="glass rounded-2xl p-6 flex flex-col justify-between border border-purple-500/20 bg-gradient-to-br from-purple-500/5 to-cyan-500/5 cursor-pointer group relative overflow-hidden"
              >
                {/* Animated Background Glow */}
                <div className="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-cyan-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-8">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-cyan-500 flex items-center justify-center shadow-[0_0_20px_rgba(168,85,247,0.4)] group-hover:shadow-[0_0_30px_rgba(168,85,247,0.6)] transition-all">
                      <BrainCircuit className="w-6 h-6 text-white" />
                    </div>
                    <span className="text-[10px] font-mono text-purple-400 bg-purple-500/10 px-2 py-1 rounded uppercase tracking-wider border border-purple-500/20">AI Powered</span>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-semibold text-purple-300 mb-2 uppercase tracking-wider">Smart Scouting</h3>
                    <p className="text-2xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-cyan-400 mb-3">
                      Neural Search
                    </p>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Trova cloni statistici con AI avanzata →
                    </p>
                  </div>
                  
                  <div className="mt-6 flex items-center gap-2 text-purple-400 group-hover:text-purple-300 transition-colors">
                    <span className="text-[10px] font-bold uppercase tracking-widest">Analizza Ora</span>
                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </motion.div>

              {/* Team Strength Rankings Card */}
              <motion.div 
                variants={itemVariants}
                onClick={() => router.push('/teams')}
                whileHover={{ y: -8, scale: 1.02 }}
                className="glass rounded-2xl p-6 flex flex-col justify-between border border-cyan-500/20 bg-gradient-to-br from-cyan-500/5 to-blue-500/5 cursor-pointer group relative overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                
                <div className="relative z-10">
                  <div className="flex justify-between items-start mb-8">
                    <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-500 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.4)] group-hover:shadow-[0_0_30px_rgba(6,182,212,0.6)] transition-all">
                      <Shield className="w-6 h-6 text-white" />
                    </div>
                    <span className="text-[10px] font-mono text-cyan-400 bg-cyan-500/10 px-2 py-1 rounded uppercase tracking-wider border border-cyan-500/20">Context</span>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-semibold text-cyan-300 mb-2 uppercase tracking-wider">Team Strength</h3>
                    <p className="text-2xl font-black tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-400 mb-3">
                      ELO Rankings
                    </p>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      Classifica forza squadre + forma →
                    </p>
                  </div>
                  
                  <div className="mt-6 flex items-center gap-2 text-cyan-400 group-hover:text-cyan-300 transition-colors">
                    <span className="text-[10px] font-bold uppercase tracking-widest">Vedi Classifica</span>
                    <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              </motion.div>
            </div>

            {/* Main Chart Section */}
            <motion.div variants={itemVariants} className="glass rounded-2xl p-8 border border-white/5">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-10">
                <div>
                  <h2 className="text-2xl font-bold tracking-tight">{selectedTeamName ? `Squad Analysis: ${selectedTeamName}` : `${seasonLabel} — League Leaders`}</h2>
                  <p className="text-slate-400 text-sm">Quant Score vs Goals Scored</p>
                </div>
                <div className="flex gap-2 items-center">
                  <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-lg border border-white/10 text-xs">
                    <div className="w-2 h-2 rounded-full bg-[#00ff85]" />
                    <span>Positive Efficiency</span>
                  </div>
                  <div className="flex items-center gap-2 px-4 py-2 bg-white/5 rounded-lg border border-white/10 text-xs">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <span>High Variance</span>
                  </div>
                  {/* Team selector dropdown */}
                  <div className="ml-4">
                    <select
                      value={selectedTeamId}
                      onChange={(e) => {
                        const val = e.target.value;
                        setSelectedTeamId(val);
                        const team = teams.find(t => t.id === val);
                        setSelectedTeamName(team ? team.name : '');
                      }}
                      className="bg-gray-900 text-slate-100 px-3 py-2 rounded-lg border border-white/5 text-sm"
                    >
                      <option value="">All Teams (Top 10)</option>
                      {teams.map(t => (
                        <option key={t.id} value={t.id}>{t.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
              <div className="h-[400px] w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    layout="vertical"
                    data={data}
                    margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                    <XAxis 
                      type="number" 
                      stroke="rgba(255,255,255,0.3)" 
                      fontSize={10}
                      tickFormatter={(value) => `${value}`}
                    />
                    <YAxis 
                      type="category" 
                      dataKey="player" 
                      stroke="rgba(255,255,255,0.3)" 
                      fontSize={11}
                      width={100}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#0f172a', 
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderRadius: '12px',
                        color: '#fff'
                      }}
                      cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                    />
                    <ReferenceLine x={0} stroke="rgba(255,255,255,0.2)" />
                    <Bar 
                      dataKey="quant_efficiency_score" 
                      radius={[0, 4, 4, 0]} 
                      barSize={20}
                      animationDuration={1500}
                    >
                      {data.map((entry, index) => (
                        <Cell 
                          key={`cell-${index}`} 
                          fill={entry.quant_efficiency_score >= 0 ? ACCENT_GREEN : ACCENT_RED} 
                          fillOpacity={0.8}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </motion.div>

            {/* Detailed Table Section */}
            <motion.div variants={itemVariants} className="glass rounded-2xl border border-white/5 overflow-hidden">
              <div className="px-8 py-6 border-b border-white/5 flex items-center justify-between">
                <h3 className="font-bold">Technical Breakdown</h3>
                <button className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors">
                  Export CSV <ChevronRight className="w-3 h-3" />
                </button>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="bg-white/[0.02] text-xs font-mono text-slate-500 uppercase tracking-widest">
                      <th className="px-8 py-4 font-medium">Rank</th>
                      <th className="px-8 py-4 font-medium">Player</th>
                      <th className="px-8 py-4 font-medium">Volume (Goals)</th>
                      <th className="px-8 py-4 font-medium">Quant Efficiency</th>
                      <th className="px-8 py-4 font-medium text-right">Trend</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {data.map((player, idx) => (
                      <tr
                        key={player.player}
                        className="group hover:bg-white/[0.04] transition-colors cursor-pointer"
                        onClick={() => router.push(`/player/${encodeURIComponent(player.player)}`)}
                      >
                        <td className="px-8 py-4 font-mono text-slate-500 text-sm">#{String(idx + 1).padStart(2, '0')}</td>
                        <td className="px-8 py-4 font-semibold text-slate-200">{player.player}</td>
                        <td className="px-8 py-4">
                          <div className="flex items-center gap-2">
                            <span className="font-bold">{player.goals}</span>
                            <div className="h-1 bg-white/10 w-24 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-slate-400 transition-all duration-1000" 
                                style={{ width: `${(player.goals / 25) * 100}%` }} 
                              />
                            </div>
                          </div>
                        </td>
                        <td className="px-8 py-4">
                          <span className={`font-mono text-sm px-2 py-1 rounded ${
                            player.quant_efficiency_score >= 0 
                            ? 'text-[#00ff85] bg-[#00ff85]/10' 
                            : 'text-red-500 bg-red-500/10'
                          }`}>
                            {player.quant_efficiency_score.toFixed(2)}
                          </span>
                        </td>
                        <td className="px-8 py-4 text-right">
                          <div className="inline-flex items-center gap-1 text-slate-500">
                             <TrendingUp className="w-3 h-3 text-[#00ff85]" />
                             <span className="text-xs">Stable</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </motion.div>
          </motion.div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 px-6 md:px-12 mt-24 glass">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="flex items-center gap-2 opacity-50">
            <Activity className="w-4 h-4 text-[#00ff85]" />
            <span className="font-mono text-xs tracking-widest uppercase">Football Quant Analytics v2.4.0</span>
          </div>
          <div className="flex gap-8 text-xs font-mono text-slate-500 uppercase tracking-widest">
            <a href="#" className="hover:text-white transition-colors">Privacy</a>
            <a href="#" className="hover:text-white transition-colors">API Docs</a>
            <a href="#" className="hover:text-white transition-colors">System Status</a>
          </div>
          <p className="text-[10px] text-slate-600 font-mono">
            © 2024 QUANTUM SPORTS LABS. ALL RIGHTS RESERVED.
          </p>
        </div>
      </footer>
    </div>
  );
};

// Internal Components
const StatCard: React.FC<{ 
  title: string; 
  player: string; 
  score: number; 
  type: 'top' | 'flop' 
}> = ({ title, player, score, type }) => {
  const isPositive = score >= 0;
  
  return (
    <motion.div 
      variants={itemVariants}
      whileHover={{ y: -5 }}
      className={`glass rounded-2xl p-6 relative overflow-hidden transition-all duration-300 ${
        type === 'top' ? 'glow-green border-[#00ff85]/20' : 'glow-red border-red-500/20'
      }`}
    >
      <div className="flex justify-between items-start mb-6">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
          type === 'top' ? 'bg-[#00ff85]/10 text-[#00ff85]' : 'bg-red-500/10 text-red-500'
        }`}>
          {type === 'top' ? <Trophy className="w-5 h-5" /> : <TrendingDown className="w-5 h-5" />}
        </div>
        <div className="flex items-center gap-1">
          {isPositive ? <TrendingUp className="w-3 h-3 text-[#00ff85]" /> : <TrendingDown className="w-3 h-3 text-red-500" />}
          <span className={`text-[10px] font-mono font-bold ${isPositive ? 'text-[#00ff85]' : 'text-red-500'}`}>
            {isPositive ? '+' : ''}{score.toFixed(2)}
          </span>
        </div>
      </div>
      
      <div>
        <h3 className="text-[10px] font-bold tracking-[0.2em] text-slate-500 mb-1 uppercase">
          {title}
        </h3>
        <p className="text-2xl font-bold tracking-tight group-hover:text-[#00ff85] transition-colors truncate">
          {player}
        </p>
      </div>

      <div className={`absolute bottom-0 right-0 w-32 h-32 blur-3xl rounded-full -mr-16 -mb-16 opacity-10 ${
        type === 'top' ? 'bg-[#00ff85]' : 'bg-red-500'
      }`} />
    </motion.div>
  );
};

const LoadingSkeleton = () => (
  <div className="space-y-12 animate-pulse">
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {[1, 2, 3].map(i => (
        <div key={i} className="h-40 bg-white/5 border border-white/10 rounded-2xl" />
      ))}
    </div>
    <div className="h-96 bg-white/5 border border-white/10 rounded-2xl" />
    <div className="h-64 bg-white/5 border border-white/10 rounded-2xl" />
  </div>
);

// Framer Motion Variants
const itemVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: { 
    opacity: 1, 
    y: 0,
    transition: {
      type: 'spring' as const,
      stiffness: 100,
      damping: 12
    }
  }
};

export default App;
