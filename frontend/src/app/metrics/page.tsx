"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { 
  Activity, 
  TrendingUp, 
  Target, 
  Zap,
  Brain,
  Shield,
  TrendingDown,
  Calculator,
  DollarSign,
  Trophy,
  BarChart3,
  ArrowLeft,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface Metric {
  id: string;
  name: string;
  icon: any;
  category: 'performance' | 'advanced' | 'context' | 'value';
  shortDesc: string;
  formula?: string;
  explanation: string;
  interpretation: string;
  example: string;
  color: string;
}

const metrics: Metric[] = [
  // Performance Metrics
  {
    id: 'xg',
    name: 'Expected Goals (xG)',
    icon: Target,
    category: 'performance',
    shortDesc: 'Probabilità di segnare da ogni tiro',
    formula: 'Σ(Shot_Quality × Position × Defense_Pressure)',
    explanation: 'xG misura la qualità delle occasioni da gol. Ogni tiro riceve un valore da 0.0 (impossibile) a 1.0 (gol certo) basato su: posizione del tiro, angolo, distanza dalla porta, presenza di difensori, e tipo di azione (contropiede, palla ferma, etc).',
    interpretation: 'Un giocatore con 15 gol su 12.0 xG sta sovraperformando (clinical finisher). Un giocatore con 8 gol su 14.0 xG sta sottoperformando (spreca occasioni).',
    example: 'Lautaro Martínez: 24 gol su 22.5 xG → +1.5 overperformance. Finisher élite.',
    color: 'from-emerald-500 to-cyan-500'
  },
  {
    id: 'xa',
    name: 'Expected Assists (xA)',
    icon: TrendingUp,
    category: 'performance',
    shortDesc: 'Qualità dei passaggi che generano tiri',
    formula: 'Σ(Recipient_xG per ogni passaggio)',
    explanation: 'xA assegna credito al passatore per la qualità dell\'occasione creata. Se il tuo passaggio permette un tiro con xG 0.35, guadagni 0.35 xA - indipendentemente dal risultato del tiro.',
    interpretation: 'Alto xA = crei occasioni di qualità. xA > Assists = compagni imprecisi. xA < Assists = fortuna nei finishing dei compagni.',
    example: 'Rafael Leão: 7 assist su 9.2 xA → I compagni stanno sprecando le sue occasioni.',
    color: 'from-purple-500 to-pink-500'
  },
  {
    id: 'quant-efficiency',
    name: 'Quant Efficiency Score',
    icon: Zap,
    category: 'performance',
    shortDesc: 'Metrica proprietaria di efficienza globale',
    formula: '(Goals×3 + Assists×2 + xG + xA + KeyPasses×0.5) / Minutes × 90',
    explanation: 'Algoritmo proprietario che combina output offensivo (gol, assist) con qualità del processo (xG, xA) e volume di creazione (key passes). Normalizzato per 90 minuti per confrontare giocatori con minutaggi diversi.',
    interpretation: '>15 = Elite, 10-15 = Molto buono, 5-10 = Buono, <5 = Migliorabile. Tiene conto sia di ciò che fai (gol) che di come lo fai (qualità).',
    example: 'Top scorer Serie A spesso hanno Quant Efficiency 18-25. Playmaker puri 12-18.',
    color: 'from-[#00ff85] to-emerald-400'
  },

  // Advanced Metrics
  {
    id: 'shot-conversion',
    name: 'Shot Conversion %',
    icon: Target,
    category: 'advanced',
    shortDesc: 'Percentuale di tiri convertiti in gol',
    formula: '(Goals / Total_Shots) × 100',
    explanation: 'Misura la freddezza sotto porta. Include tutti i tiri in porta e fuori. È influenzata dal tipo di occasioni: chi tira da fuori avrà conversion più bassa.',
    interpretation: '15-20% = Elite finisher, 10-15% = Buono, 5-10% = Medio, <5% = Problematico. Da incrociare con xG per capire se è shooting selection o finishing.',
    example: 'Attaccante con 20% conversion + xG alto = Clinical. 5% conversion + xG basso = Tira male da posizioni difficili.',
    color: 'from-orange-500 to-red-500'
  },
  {
    id: 'key-passes',
    name: 'Key Passes',
    icon: Brain,
    category: 'advanced',
    shortDesc: 'Passaggi che portano direttamente a tiri',
    formula: 'Count(Passes → Immediate Shot)',
    explanation: 'Un key pass è l\'ultimo passaggio prima di un tiro della tua squadra. Non tutti diventano assist, ma tutti rappresentano creazione di occasioni. Include cross, through balls, e passaggi in area.',
    interpretation: '>3 per 90min = Eccellente creatore, 1.5-3 = Buono, <1.5 = Non è il suo ruolo. Trequartisti élite hanno 3-5 key passes/90.',
    example: 'Un centrocampista con 4.2 key passes/90 ma solo 5 assist = Crea tanto ma compagni imprecisi.',
    color: 'from-indigo-500 to-purple-500'
  },
  {
    id: 'progressive-passes',
    name: 'Progressive Passes',
    icon: TrendingUp,
    category: 'advanced',
    shortDesc: 'Passaggi che avanzano la palla verso la porta',
    formula: 'Count(Passes che avvicinano +10m alla porta avversaria)',
    explanation: 'Misura l\'abilità di fare progressione con passaggi verticali. Un progressive pass deve avvicinare significativamente la palla alla porta avversaria (tipicamente >10 metri di gain territoriale).',
    interpretation: 'Registi e mediani top hanno 8-15 progressive/90. Terzini moderni 5-10. Indica capacità di rompere linee difensive.',
    example: 'Regista con 12 progressive passes/90 = Ottimo nella costruzione verticale.',
    color: 'from-teal-500 to-green-500'
  },

  // Context Analytics
  {
    id: 'elo',
    name: 'ELO Team Rating',
    icon: Shield,
    category: 'context',
    shortDesc: 'Forza relativa della squadra (1200-1900)',
    formula: 'ELO_new = ELO_old + K × (Result - Expected_Result)',
    explanation: 'Sistema ELO adattato dal chess. Ogni squadra parte da 1500. Vincere vs squadra forte = +molti punti. Perdere vs squadra debole = -molti punti. K-factor=32, Home Advantage=+100 ELO virtuale.',
    interpretation: '1800+ = Elite tier (Inter, Napoli top form), 1600-1800 = Strong (Milan, Juve), 1400-1600 = Average, <1400 = Struggling.',
    example: 'Inter 1840 ELO batte Cagliari 1380 ELO → Inter +8 punti, Cagliari -8 (vittoria prevista).',
    color: 'from-cyan-500 to-blue-500'
  },
  {
    id: 'difficulty-score',
    name: 'Difficulty Score',
    icon: TrendingDown,
    category: 'context',
    shortDesc: 'Durezza calendario affrontato (0-100)',
    formula: '((AVG_Opponent_ELO - 1200) / 600) × 100',
    explanation: 'Media ELO di tutti gli avversari affrontati, normalizzata su scala 0-100. 50 = calendario medio (ELO 1500). 70+ = calendario durissimo. 30- = calendario facile.',
    interpretation: 'Un attaccante con 20 gol su Difficulty 70 vale più di uno con 25 gol su Difficulty 35. Contestualizza le performance.',
    example: 'Giocatore A: 18 gol, Difficulty 65. Giocatore B: 22 gol, Difficulty 38. A ha fatto meglio.',
    color: 'from-red-500 to-orange-500'
  },
  {
    id: 'goal-quality',
    name: 'Goal Quality Index',
    icon: Trophy,
    category: 'context',
    shortDesc: 'Valore ponderato dei gol vs squadre forti',
    formula: 'Σ(Goals × Opponent_ELO / 1500) / Total_Goals',
    explanation: 'Ogni gol viene pesato per la forza dell\'avversario. Gol vs Inter (1840 ELO) conta 1.23×. Gol vs Lecce (1350 ELO) conta 0.90×. Media di tutti i weight.',
    interpretation: '>1.05 = Segna contro squadre forti, 0.95-1.05 = Neutro, <0.95 = Statistiche gonfiate da squadre deboli.',
    example: 'Attaccante con Quality Index 1.12 = Big game player. 0.88 = Flat track bully.',
    color: 'from-yellow-500 to-amber-500'
  },

  // Value Metrics
  {
    id: 'fair-value',
    name: 'Fair Value €',
    icon: DollarSign,
    category: 'value',
    shortDesc: 'Valutazione di mercato algoritmica',
    formula: '€5M + Goals×€2.5M + Assists×€1.5M + xG×€1M',
    explanation: 'Algoritmo proprietario che stima il valore di mercato basandosi su output offensivo stagionale. Considera produzione (gol/assist) e processo (xG). Calibrato su transazioni Serie A recenti.',
    interpretation: '€50M+ = Top player europeo, €25-50M = Ottimo titolare, €10-25M = Buon giocatore, <€10M = Giovane/riserva.',
    example: 'Lautaro: 24 gol, 6 assist, 22.5 xG → €5M + €60M + €9M + €22.5M = €96.5M fair value.',
    color: 'from-green-500 to-emerald-500'
  },
  {
    id: 'value-adjustment',
    name: 'Fair Value Adjustment',
    icon: Calculator,
    category: 'value',
    shortDesc: 'Bonus/penalità per difficoltà calendario',
    formula: '(Difficulty_Score - 50) / 100 × Fair_Value',
    explanation: 'Il Fair Value base viene aggiustato in base al Difficulty Score. Giocatori che affrontano calendari duri ottengono bonus (+25% se Difficulty 75). Calendari facili ricevono penalità (-15% se Difficulty 35).',
    interpretation: 'Se hai Fair Value €40M con Difficulty 65 → Adjustment +15% → €46M adjusted value. Riconosce il contesto.',
    example: 'Stesso output offensivo, ma uno affronta big team (Difficulty 68), l\'altro piccole (Difficulty 42) → +13% vs -4% adjustment.',
    color: 'from-purple-500 to-indigo-500'
  },
  {
    id: 'rolling-form',
    name: 'Rolling Form (xG/GA)',
    icon: BarChart3,
    category: 'context',
    shortDesc: 'Forma recente squadra (ultime 5 gare)',
    formula: 'AVG(xG_Created last 5 matches) - AVG(xG_Against last 5 matches)',
    explanation: 'Media mobile delle ultime 5 partite di xG creati (attacco) e xG subiti (difesa). Cattura momentum e forma corrente meglio dei risultati grezzi.',
    interpretation: 'Form +0.8 xG = In ottima forma offensiva. Form -0.6 xG = Difesa colabrodo. ±0.2 = Stabile.',
    example: 'Napoli rolling form: +1.2 xGF, -0.3 xGA → Attacco devastante, difesa solida.',
    color: 'from-pink-500 to-rose-500'
  }
];

const categoryConfig = {
  performance: { 
    label: 'Metriche di Performance', 
    color: 'from-emerald-500 to-cyan-500',
    icon: Activity,
    desc: 'Output diretto e qualità del gioco offensivo'
  },
  advanced: { 
    label: 'Metriche Avanzate', 
    color: 'from-purple-500 to-pink-500',
    icon: Brain,
    desc: 'Statistiche approfondite su creazione e finalizzazione'
  },
  context: { 
    label: 'Context Analytics', 
    color: 'from-cyan-500 to-blue-500',
    icon: Shield,
    desc: 'Forza avversari e contestualizzazione performance'
  },
  value: { 
    label: 'Valutazione di Mercato', 
    color: 'from-green-500 to-emerald-500',
    icon: DollarSign,
    desc: 'Stima algoritmica del valore economico'
  }
};

export default function MetricsPage() {
  const router = useRouter();
  const [expandedMetric, setExpandedMetric] = useState<string | null>(null);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const filteredMetrics = selectedCategory 
    ? metrics.filter(m => m.category === selectedCategory)
    : metrics;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Navbar */}
      <nav className="fixed top-0 w-full z-50 glass border-b border-white/5 h-16 flex items-center px-6 md:px-12 justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-[#00ff85] rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(0,255,133,0.4)]">
            <Activity className="w-5 h-5 text-slate-950" />
          </div>
          <span className="font-bold tracking-tighter text-xl bg-clip-text text-transparent bg-gradient-to-r from-white to-white/60">
            QUANT ENGINE
          </span>
        </div>
        <button 
          onClick={() => router.push('/')}
          className="flex items-center gap-2 text-sm font-medium text-slate-400 hover:text-[#00ff85] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          DASHBOARD
        </button>
      </nav>

      <main className="pt-24 pb-12 px-6 md:px-12 max-w-7xl mx-auto space-y-12">
        {/* Hero Section */}
        <motion.section 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
          className="relative overflow-hidden py-12"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#00ff85]/10 border border-[#00ff85]/20 mb-6">
            <Calculator className="w-4 h-4 text-[#00ff85]" />
            <span className="text-[10px] font-bold tracking-widest text-[#00ff85] uppercase">Metrics Documentation</span>
          </div>
          <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-4 leading-none">
            METRICHE <br />
            <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#00ff85] to-emerald-400">QUANTITATIVE</span>
          </h1>
          <p className="text-slate-400 text-lg max-w-2xl leading-relaxed">
            Guida completa a tutte le metriche utilizzate nel Football Quant Engine. 
            Comprendi formule, interpretazione, e applicazioni pratiche.
          </p>
          <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-[#00ff85]/5 blur-[120px] rounded-full -z-10" />
        </motion.section>

        {/* Category Filter */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="flex flex-wrap gap-3"
        >
          <button
            onClick={() => setSelectedCategory(null)}
            className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
              selectedCategory === null 
                ? 'bg-[#00ff85] text-slate-900 shadow-[0_0_20px_rgba(0,255,133,0.3)]' 
                : 'glass border border-white/5 hover:border-[#00ff85]/30'
            }`}
          >
            Tutte ({metrics.length})
          </button>
          {Object.entries(categoryConfig).map(([key, config]) => {
            const Icon = config.icon;
            const count = metrics.filter(m => m.category === key).length;
            return (
              <button
                key={key}
                onClick={() => setSelectedCategory(key)}
                className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all flex items-center gap-2 ${
                  selectedCategory === key 
                    ? `bg-gradient-to-r ${config.color} text-white shadow-lg` 
                    : 'glass border border-white/5 hover:border-white/10'
                }`}
              >
                <Icon className="w-4 h-4" />
                {config.label} ({count})
              </button>
            );
          })}
        </motion.div>

        {/* Category Description */}
        {selectedCategory && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            className="glass rounded-2xl p-6 border border-white/5"
          >
            <div className="flex items-start gap-4">
              {React.createElement(categoryConfig[selectedCategory as keyof typeof categoryConfig].icon, {
                className: "w-8 h-8 text-[#00ff85] mt-1"
              })}
              <div>
                <h3 className="text-xl font-bold mb-2">
                  {categoryConfig[selectedCategory as keyof typeof categoryConfig].label}
                </h3>
                <p className="text-slate-400">
                  {categoryConfig[selectedCategory as keyof typeof categoryConfig].desc}
                </p>
              </div>
            </div>
          </motion.div>
        )}

        {/* Metrics List */}
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="space-y-4"
        >
          {filteredMetrics.map((metric, idx) => {
            const Icon = metric.icon;
            const isExpanded = expandedMetric === metric.id;
            
            return (
              <motion.div
                key={metric.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.05 }}
                className="glass rounded-2xl border border-white/5 overflow-hidden hover:border-white/10 transition-all"
              >
                {/* Header - Always Visible */}
                <button
                  onClick={() => setExpandedMetric(isExpanded ? null : metric.id)}
                  className="w-full p-6 flex items-center justify-between hover:bg-white/[0.02] transition-colors"
                >
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${metric.color} flex items-center justify-center shadow-lg`}>
                      <Icon className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-left">
                      <h3 className="text-xl font-bold text-white mb-1">{metric.name}</h3>
                      <p className="text-sm text-slate-400">{metric.shortDesc}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`text-xs px-3 py-1 rounded-full bg-gradient-to-r ${
                      categoryConfig[metric.category].color
                    } bg-opacity-10 border border-white/10`}>
                      {categoryConfig[metric.category].label}
                    </span>
                    {isExpanded ? (
                      <ChevronUp className="w-5 h-5 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-5 h-5 text-slate-400" />
                    )}
                  </div>
                </button>

                {/* Expanded Content */}
                {isExpanded && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                    className="px-6 pb-6 pt-2 space-y-6 border-t border-white/5"
                  >
                    {/* Formula */}
                    {metric.formula && (
                      <div>
                        <h4 className="text-xs font-bold text-[#00ff85] uppercase tracking-wider mb-2">
                          Formula
                        </h4>
                        <div className="glass rounded-lg p-4 font-mono text-sm text-cyan-400 border border-cyan-500/20">
                          {metric.formula}
                        </div>
                      </div>
                    )}

                    {/* Explanation */}
                    <div>
                      <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider mb-2">
                        Spiegazione
                      </h4>
                      <p className="text-slate-300 leading-relaxed">
                        {metric.explanation}
                      </p>
                    </div>

                    {/* Interpretation */}
                    <div>
                      <h4 className="text-xs font-bold text-orange-400 uppercase tracking-wider mb-2">
                        Come Interpretarla
                      </h4>
                      <p className="text-slate-300 leading-relaxed">
                        {metric.interpretation}
                      </p>
                    </div>

                    {/* Example */}
                    <div>
                      <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2">
                        Esempio Pratico
                      </h4>
                      <div className="glass rounded-lg p-4 border border-emerald-500/20">
                        <p className="text-slate-300 italic">
                          "{metric.example}"
                        </p>
                      </div>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            );
          })}
        </motion.div>

        {/* Bottom CTA */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="glass rounded-2xl p-8 border border-[#00ff85]/20 relative overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-[#00ff85]/5 to-emerald-500/5" />
          <div className="relative z-10">
            <h3 className="text-2xl font-bold mb-3">Pronto a Usare le Metriche?</h3>
            <p className="text-slate-400 mb-6 max-w-2xl">
              Applica queste metriche quantitative per scouting, valutazioni di mercato, e analisi tattiche. 
              Il nostro engine elabora migliaia di datapoint ogni match.
            </p>
            <button
              onClick={() => router.push('/')}
              className="px-6 py-3 bg-[#00ff85] text-slate-900 rounded-xl font-bold hover:shadow-[0_0_25px_rgba(0,255,133,0.4)] transition-all flex items-center gap-2"
            >
              Torna alla Dashboard
              <ChevronDown className="w-4 h-4 rotate-[-90deg]" />
            </button>
          </div>
        </motion.div>
      </main>
    </div>
  );
}
