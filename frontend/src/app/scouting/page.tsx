"use client";

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Cpu,
  Target,
  Users,
  Dna,
  Zap,
  AlertCircle,
  ChevronRight,
  RefreshCcw,
  ArrowLeft
} from 'lucide-react';
import { SimilarPlayer } from '../types';

const ScoutingPage: React.FC = () => {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<SimilarPlayer[]>([]);
  const [searchedName, setSearchedName] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [debounceTimer, setDebounceTimer] = useState<number | null>(null);
  const [algorithmUsed, setAlgorithmUsed] = useState<string>("");
  const [maxBudget, setMaxBudget] = useState<number>(50); // Budget massimo in milioni €
  const [selectedSeason, setSelectedSeason] = useState<string>("2025");

  // Cleanup del timer allo smontaggio del componente
  useEffect(() => {
    return () => {
      if (debounceTimer) window.clearTimeout(debounceTimer);
    };
  }, [debounceTimer]);

  const handleSearch = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setSearchedName(query);
    setShowSuggestions(false);

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/analytics/scouting/similar/${encodeURIComponent(query)}?season=${encodeURIComponent(selectedSeason)}`
      );
      
      if (!response.ok) throw new Error("Giocatore non trovato nel database");
      
      const data = await response.json();
      console.log("API Response:", data); // DEBUG
      
      const items: SimilarPlayer[] = Array.isArray(data?.matches)
        ? data.matches.slice(0, 5).map((m: any) => ({
            player: m.player,
            team: m.team,
            match_score: m.similarity ?? 0,
            goals_90: m.data?.goals_p90 ?? 0,
            xg_90: m.data?.xg_p90 ?? 0,
            fair_value: m.data?.fair_value ?? 0  // Usa fair_value da data invece che dalla root
          }))
        : [];

      console.log("Processed items:", items); // DEBUG
      
      // Filtra per budget (converti fair_value da € a milioni per confronto)
      const filteredItems = items.filter(item => {
        const valueMillion = (item.fair_value || 0) / 1_000_000;
        return valueMillion <= maxBudget;
      });
      
      setResults(filteredItems);
      setAlgorithmUsed(data?.algorithm || "unknown");
      
      // Non mostrare errore se abbiamo risultati validi
      if (filteredItems.length === 0) {
        setError(`Nessun giocatore trovato entro il budget di €${maxBudget}M. Prova ad aumentare il limite.`);
        setResults([]);
      }
    } catch (err) {
      console.error("API Error:", err); // DEBUG
      setError("Errore di connessione al server. Riprova.");
      setResults([]);
    } finally {
      // Delay artificiale per enfatizzare l'effetto "scanning"
      setTimeout(() => setLoading(false), 1200);
    }
  };

  const onType = (value: string) => {
    setQuery(value);
    setShowSuggestions(true);
    
    if (debounceTimer) window.clearTimeout(debounceTimer);

    const t = window.setTimeout(async () => {
      if (value.trim().length < 2) {
        setSuggestions([]);
        return;
      }
      try {
        const resp = await fetch(`http://127.0.0.1:8000/analytics/scouting/suggest?q=${encodeURIComponent(value)}`);
        if (resp.ok) {
          const json = await resp.json();
          setSuggestions(Array.isArray(json) ? json : []);
        }
      } catch (e) {
        setSuggestions([]);
      }
    }, 300);
    setDebounceTimer(t);
  };

  const resetSearch = () => {
    setQuery("");
    setResults([]);
    setSearchedName("");
    setError(null);
  };

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 pt-24 pb-20 px-6">
      <div className="max-w-7xl mx-auto">
        
        {/* Back Button */}
        <motion.button
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          onClick={() => router.push('/dashboard')}
          className="mb-8 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 hover:bg-white/10 hover:border-purple-500/30 transition-all group"
        >
          <ArrowLeft className="w-4 h-4 text-purple-400 group-hover:text-purple-300 transition-colors" />
          <span className="text-sm font-bold text-slate-300 group-hover:text-white transition-colors">Back to Dashboard</span>
        </motion.button>

        {/* Header Section */}
        <div className="mb-16 text-center">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-purple-500/10 border border-purple-500/20 mb-6"
          >
            <Dna className="w-4 h-4 text-purple-400" />
            <span className="text-[10px] font-black tracking-widest text-purple-400 uppercase">
              Neural Similarity Engine
            </span>
          </motion.div>
          
          <h1 className="text-5xl md:text-7xl font-black tracking-tighter uppercase italic mb-6">
            Smart <span className="text-transparent bg-clip-text bg-gradient-to-r from-purple-500 to-cyan-500">Scout</span>
          </h1>
          
          <p className="text-slate-400 max-w-2xl mx-auto text-lg">
            Inserisci un giocatore per trovare i suoi cloni statistici basati su oltre 150 parametri di efficienza.
          </p>
          <div className="mt-6 flex items-center justify-center gap-3">
            <button
              onClick={() => setSelectedSeason("2024")}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                selectedSeason === "2024"
                  ? "bg-cyan-500 text-slate-900 shadow-[0_0_20px_rgba(6,182,212,0.3)]"
                  : "bg-white/5 text-slate-400 hover:bg-white/10"
              }`}
            >
              2024 / 2025
            </button>
            <button
              onClick={() => setSelectedSeason("2025")}
              className={`px-4 py-2 rounded-lg text-sm font-bold transition-all ${
                selectedSeason === "2025"
                  ? "bg-cyan-500 text-slate-900 shadow-[0_0_20px_rgba(6,182,212,0.3)]"
                  : "bg-white/5 text-slate-400 hover:bg-white/10"
              }`}
            >
              2025 / 2026
            </button>
          </div>
        </div>

        {/* Search Bar Container */}
        <div className="max-w-2xl mx-auto mb-20 relative z-50">
          <form onSubmit={handleSearch} className="relative group z-50">
            <div className="absolute inset-0 bg-gradient-to-r from-purple-500 to-cyan-500 rounded-2xl blur opacity-20 group-hover:opacity-40 transition-opacity" />
            <div className="relative flex items-center bg-slate-900 border border-white/10 rounded-2xl overflow-hidden p-2 z-50">
              <div className="pl-4 text-slate-500">
                <Search className="w-6 h-6" />
              </div>
              <input
                type="text"
                value={query}
                onChange={(e) => onType(e.target.value)}
                placeholder="Cerca il DNA di un calciatore..."
                className="w-full bg-transparent border-none focus:ring-0 px-4 py-3 font-medium text-lg placeholder:text-slate-600"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="bg-gradient-to-r from-purple-600 to-cyan-600 text-white px-8 py-3 rounded-xl font-black uppercase tracking-widest text-xs hover:scale-[0.98] transition-all disabled:opacity-50"
              >
                {loading ? "Analyzing..." : "Analyze DNA"}
              </button>
            </div>

            {/* Suggestions Dropdown */}
            <AnimatePresence>
              {showSuggestions && suggestions.length > 0 && (
                <motion.div 
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute left-0 right-0 bg-slate-900 border border-white/10 rounded-xl py-2 mt-2 shadow-2xl z-[100]"
                >
                  {suggestions.map((s, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        setQuery(s);
                        setShowSuggestions(false);
                        setSuggestions([]);
                        setSearchedName(s);
                        handleSearch();
                      }}
                      className="w-full text-left px-4 py-3 hover:bg-white/5 transition-colors border-b border-white/5 last:border-none"
                    >
                      {s}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </form>
          
          {/* Budget Filter Slider */}
          <motion.div 
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-6 p-6 bg-slate-900/50 border border-white/5 rounded-2xl backdrop-blur-sm relative z-0"
          >
            <div className="flex items-center justify-between mb-3">
              <label className="text-sm font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
                <Target className="w-4 h-4 text-green-400" />
                Budget Massimo
              </label>
              <span className="text-2xl font-black text-transparent bg-clip-text bg-gradient-to-r from-green-400 to-emerald-500">
                €{maxBudget}M
              </span>
            </div>
            <input
              type="range"
              min="5"
              max="100"
              step="5"
              value={maxBudget}
              onChange={(e) => setMaxBudget(Number(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-green-500"
              style={{
                background: `linear-gradient(to right, rgb(34 197 94) 0%, rgb(34 197 94) ${maxBudget}%, rgb(30 41 59) ${maxBudget}%, rgb(30 41 59) 100%)`
              }}
            />
            <div className="flex justify-between text-xs text-slate-500 mt-2">
              <span>€5M</span>
              <span>€50M</span>
              <span>€100M</span>
            </div>
          </motion.div>
        </div>

        {/* Dynamic Content Area */}
        <div className="relative min-h-[400px]">
          {/* Loading / Scanning */}
          <AnimatePresence mode="wait">
            {loading && (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center py-20"
              >
                <div className="relative w-40 h-40">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
                    className="absolute inset-0 rounded-full border-2 border-dashed border-purple-500/30"
                  />
                  <motion.div
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="absolute inset-4 rounded-full border-2 border-cyan-500/50 flex items-center justify-center bg-cyan-500/5"
                  >
                    <Cpu className="w-12 h-12 text-cyan-400" />
                  </motion.div>
                  <motion.div
                    animate={{ top: ['0%', '100%', '0%'] }}
                    transition={{ duration: 2, repeat: Infinity }}
                    className="absolute left-0 right-0 h-1 bg-cyan-400/50 shadow-[0_0_15px_#06b6d4] z-10"
                  />
                </div>
                <p className="mt-8 font-mono text-xs text-cyan-400 uppercase tracking-[0.3em] animate-pulse">
                  Mapping Data: {searchedName.toUpperCase()}
                </p>
              </motion.div>
            )}

            {/* Results Grid */}
            {!loading && results.length > 0 && (
              <motion.div 
                key="results"
                initial={{ opacity: 0, y: 20 }} 
                animate={{ opacity: 1, y: 0 }} 
                className="space-y-8"
              >
                <div className="flex items-center justify-between border-b border-white/10 pb-4">
                  <div className="flex items-center gap-3">
                    <h2 className="text-xl font-bold flex items-center gap-3">
                      <Users className="w-5 h-5 text-purple-400" />
                      Matches for <span className="text-cyan-400 italic">"{searchedName}"</span>
                    </h2>
                    {algorithmUsed === "hybrid_cosine_euclidean" && (
                      <span className="px-2 py-1 text-[9px] font-bold uppercase tracking-wider bg-orange-500/10 text-orange-400 border border-orange-500/20 rounded">
                        Hybrid Match
                      </span>
                    )}
                  </div>
                  <button 
                    onClick={resetSearch}
                    className="flex items-center gap-2 text-[10px] font-bold text-slate-500 uppercase hover:text-white transition-colors"
                  >
                    <RefreshCcw className="w-3 h-3" /> New Search
                  </button>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-6">
                  {results.map((player, idx) => (
                    <SimilarityCard
                      key={idx}
                      player={player}
                      delay={idx * 0.1}
                      onViewAnalytics={(name) =>
                        router.push(
                          `/player/${encodeURIComponent(name)}?season=${encodeURIComponent(selectedSeason)}`
                        )
                      }
                    />
                  ))}
                </div>
              </motion.div>
            )}

            {/* Error State */}
            {!loading && error && (
              <motion.div 
                key="error"
                initial={{ opacity: 0 }} 
                animate={{ opacity: 1 }} 
                className="max-w-md mx-auto bg-orange-500/5 p-8 rounded-3xl border border-orange-500/20 text-center"
              >
                <AlertCircle className="w-12 h-12 text-orange-400 mx-auto mb-4" />
                <h3 className="text-xl font-bold mb-2 text-orange-300">Nessun Match Trovato</h3>
                <p className="text-slate-400 text-sm mb-6">{error}</p>
                <button 
                  onClick={resetSearch} 
                  className="px-6 py-2.5 bg-orange-500/10 hover:bg-orange-500/20 border border-orange-500/30 rounded-xl text-xs font-bold uppercase tracking-widest text-orange-300 hover:text-white transition-all"
                >
                  Nuova Ricerca
                </button>
              </motion.div>
            )}

            {/* Empty State */}
            {!loading && !searchedName && !error && (
              <motion.div 
                key="empty"
                initial={{ opacity: 0 }} 
                animate={{ opacity: 1 }}
                className="grid grid-cols-1 md:grid-cols-3 gap-8 opacity-20 grayscale"
              >
                {[1, 2, 3].map((i) => (
                  <div key={i} className="h-48 border-2 border-dashed border-white/20 rounded-3xl" />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};

const SimilarityCard: React.FC<{
  player: SimilarPlayer;
  delay: number;
  onViewAnalytics: (playerName: string) => void;
}> = ({ player, delay, onViewAnalytics }) => (
  <motion.div 
    initial={{ opacity: 0, scale: 0.9 }} 
    animate={{ opacity: 1, scale: 1 }} 
    transition={{ delay }} 
    whileHover={{ y: -5 }} 
    className="bg-white/[0.03] border border-white/5 p-6 rounded-3xl relative overflow-hidden group backdrop-blur-sm"
  >
    <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-20 transition-opacity">
      <Zap className="w-12 h-12 text-cyan-400" />
    </div>
    
    {/* Fair Value Badge */}
    {player.fair_value !== undefined && player.fair_value > 0 && (
      <div className="absolute top-3 right-3 px-2.5 py-1 bg-green-500/20 border border-green-500/40 rounded-lg backdrop-blur-sm">
        <span className="text-[10px] font-black text-green-400">€{(player.fair_value / 1_000_000).toFixed(1)}M</span>
      </div>
    )}

    <div className="mb-6">
      <h4 className="text-lg font-bold leading-tight mb-1 truncate">{player.player}</h4>
      <div className="text-[10px] font-black uppercase text-slate-500 tracking-wider flex items-center gap-1">
        <Target className="w-3 h-3" />
        {player.team}
      </div>
    </div>

    <div className="flex flex-col items-center justify-center py-6 mb-6">
      <div className="relative">
        <svg className="w-24 h-24 rotate-[-90deg]">
          <circle cx="48" cy="48" r="40" stroke="currentColor" strokeWidth="4" fill="transparent" className="text-white/5" />
          <motion.circle 
            cx="48" cy="48" r="40" 
            stroke="currentColor" 
            strokeWidth="4" 
            fill="transparent" 
            strokeDasharray={251.2} 
            initial={{ strokeDashoffset: 251.2 }} 
            animate={{ strokeDashoffset: 251.2 - (251.2 * player.match_score) / 100 }} 
            transition={{ duration: 1.5, delay: delay + 0.2 }} 
            strokeLinecap="round" 
            className="text-cyan-500" 
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-black italic">{player.match_score}%</span>
          <span className="text-[8px] font-bold uppercase tracking-widest text-slate-500">Match</span>
        </div>
      </div>
    </div>

    <div className="space-y-3">
      <StatRow label="Goals / 90" value={player.goals_90} color="text-cyan-400" />
      <StatRow label="xG / 90" value={player.xg_90} color="text-purple-400" />
      {player.fair_value !== undefined && player.fair_value > 0 && (
        <div className="flex justify-between items-center px-3 py-2 bg-green-500/10 border border-green-500/20 rounded-xl">
          <span className="text-[9px] font-bold text-green-400 uppercase tracking-widest">Est. Value</span>
          <span className="font-mono text-xs font-bold text-green-400">€{player.fair_value.toFixed(1)}M</span>
        </div>
      )}
    </div>

    <button
      onClick={() => onViewAnalytics(player.player)}
      className="w-full mt-6 py-2.5 border border-white/10 rounded-xl text-[9px] font-bold uppercase tracking-widest text-slate-400 hover:bg-white/10 hover:text-white transition-all flex items-center justify-center gap-1 group/btn"
    >
      View Analytics <ChevronRight className="w-3 h-3 group-hover/btn:translate-x-1 transition-transform" />
    </button>
  </motion.div>
);

const StatRow: React.FC<{ label: string; value: number; color: string }> = ({ label, value, color }) => (
  <div className="flex justify-between items-center px-3 py-2 bg-white/5 rounded-xl">
    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest">{label}</span>
    <span className={`font-mono text-xs font-bold ${color}`}>{value}</span>
  </div>
);

export default ScoutingPage;