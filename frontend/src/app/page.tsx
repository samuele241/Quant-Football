"use client";

import React from 'react';
import { motion, useScroll, useTransform } from 'framer-motion';
import { useRouter } from 'next/navigation';
import { 
  Activity, 
  Zap, 
  Cpu, 
  ShieldCheck, 
  Globe, 
  ChevronDown, 
  ArrowRight,
  Target,
  BarChart3
} from 'lucide-react';

const LandingPage: React.FC = () => {
  const router = useRouter();
  const { scrollY } = useScroll();
  const opacity = useTransform(scrollY, [0, 400], [1, 0]);
  const scale = useTransform(scrollY, [0, 400], [1, 0.9]);
  const y = useTransform(scrollY, [0, 400], [0, -50]);

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 overflow-x-hidden selection:bg-[#00ff85]/30">
      {/* Dynamic Background Elements */}
      <div className="fixed inset-0 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-[#00ff85]/5 blur-[150px] rounded-full animate-pulse" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-blue-500/5 blur-[150px] rounded-full" />
        <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 brightness-50 contrast-150" />
      </div>

      {/* Futuristic Navbar */}
      <motion.nav 
        initial={{ y: -100 }}
        animate={{ y: 0 }}
        className="fixed top-0 w-full z-50 px-8 py-6 flex items-center justify-between glass border-b border-white/5"
      >
        <div className="flex items-center gap-2 group cursor-pointer">
          <div className="w-10 h-10 bg-[#00ff85] rounded-xl flex items-center justify-center shadow-[0_0_20px_rgba(0,255,133,0.4)] group-hover:scale-110 transition-transform">
            <Activity className="w-6 h-6 text-slate-950" />
          </div>
          <span className="font-black tracking-tighter text-2xl uppercase italic">Quant Engine</span>
        </div>
        
        <div className="hidden md:flex items-center gap-10">
          {['Logic', 'Metrics', 'Biometrics', 'Prediction'].map((item) => (
            <a key={item} href={`#${item.toLowerCase()}`} className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 hover:text-[#00ff85] transition-colors">
              {item}
            </a>
          ))}
        </div>

        <button 
          onClick={() => router.push('/dashboard')}
          className="px-6 py-2.5 bg-white text-slate-950 rounded-full text-xs font-black uppercase tracking-widest hover:bg-[#00ff85] transition-all hover:shadow-[0_0_30px_rgba(0,255,133,0.4)]"
        >
          Access Data
        </button>
      </motion.nav>

      {/* Hero Section */}
      <section className="relative h-screen flex flex-col items-center justify-center px-6 text-center z-10">
        <motion.div 
          style={{ opacity, scale, y }}
          className="max-w-5xl"
        >
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#00ff85]/10 border border-[#00ff85]/20 mb-8"
          >
            <Zap className="w-4 h-4 text-[#00ff85]" />
            <span className="text-[10px] font-black tracking-widest text-[#00ff85] uppercase">Predictive Intelligence v3.1</span>
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="text-7xl md:text-[10rem] font-black tracking-tighter leading-[0.85] uppercase mb-12 italic"
          >
            Precision <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-white via-[#00ff85] to-emerald-600">
              Beyond
            </span> <br />
            The Pitch
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
            className="text-slate-400 text-lg md:text-xl max-w-2xl mx-auto mb-12 font-medium leading-relaxed"
          >
            Decodifica il gioco attraverso modelli Monte Carlo e analisi dell'efficienza quantitativa. Benvenuti nel futuro della sport-intelligence.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8 }}
            className="flex flex-col md:flex-row gap-4 justify-center"
          >
            <button 
              onClick={() => router.push('/dashboard')}
              className="group relative px-10 py-5 bg-[#00ff85] text-slate-950 rounded-2xl font-black uppercase tracking-widest overflow-hidden transition-all hover:scale-105 active:scale-95"
            >
              <span className="relative z-10 flex items-center gap-2">
                Launch Dashboard <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
              </span>
              <div className="absolute inset-0 bg-white opacity-0 group-hover:opacity-20 transition-opacity" />
            </button>
            <button className="px-10 py-5 glass border border-white/10 rounded-2xl font-black uppercase tracking-widest hover:bg-white/5 transition-colors">
              Read Documentation
            </button>
          </motion.div>
        </motion.div>

        <motion.div 
          animate={{ y: [0, 10, 0] }}
          transition={{ repeat: Infinity, duration: 2 }}
          className="absolute bottom-10"
        >
          <ChevronDown className="w-8 h-8 text-slate-500" />
        </motion.div>
      </section>

      {/* Features Grid */}
      <section id="metrics" className="relative py-32 px-6 max-w-7xl mx-auto z-10">
        <div className="text-center mb-24">
          <h2 className="text-4xl md:text-6xl font-black uppercase tracking-tighter mb-4 italic">The Quant Engine</h2>
          <div className="w-24 h-1 bg-[#00ff85] mx-auto rounded-full" />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <FeatureCard 
            icon={<Cpu className="w-8 h-8 text-[#00ff85]" />}
            title="Monte Carlo Projections"
            desc="Simula migliaia di scenari stagionali per prevedere il rendimento finale con una precisione del 94%."
          />
          <FeatureCard 
            icon={<Target className="w-8 h-8 text-blue-500" />}
            title="Efficiency Vectors"
            desc="Analizziamo ogni tocco di palla per calcolare il valore aggiunto quantitativo rispetto all'xG medio."
          />
          <FeatureCard 
            icon={<ShieldCheck className="w-8 h-8 text-purple-500" />}
            title="Verified Biometrics"
            desc="Integrazione dei dati fisici in tempo reale per monitorare il calo delle performance dovuto alla fatica."
          />
        </div>
      </section>

      {/* Tech Section */}
      <section className="py-32 bg-white/[0.02] border-y border-white/5">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center gap-20">
          <div className="flex-1">
            <h3 className="text-5xl font-black uppercase italic tracking-tighter mb-8 leading-none">
              Dati massivi. <br />
              <span className="text-[#00ff85]">Zero rumore.</span>
            </h3>
            <p className="text-slate-400 text-lg leading-relaxed mb-10">
              La nostra architettura elabora flussi Opta e Wyscout in frazioni di secondo, applicando filtri proprietari per eliminare le varianze statistiche insignificanti. Ricevi solo i segnali che contano davvero.
            </p>
            <div className="grid grid-cols-2 gap-8">
              <div>
                <div className="text-3xl font-black text-white mb-2 italic">0.2s</div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Latency Threshold</div>
              </div>
              <div>
                <div className="text-3xl font-black text-white mb-2 italic">10K+</div>
                <div className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Daily Iterations</div>
              </div>
            </div>
          </div>
          <div className="flex-1 w-full flex justify-center">
            <motion.div 
              animate={{ 
                rotate: 360,
                scale: [1, 1.05, 1]
              }}
              transition={{ 
                rotate: { duration: 20, repeat: Infinity, ease: "linear" },
                scale: { duration: 4, repeat: Infinity, ease: "easeInOut" }
              }}
              className="relative w-80 h-80 md:w-96 md:h-96"
            >
              <div className="absolute inset-0 rounded-full border-2 border-dashed border-[#00ff85]/30" />
              <div className="absolute inset-10 rounded-full border-2 border-[#00ff85]/10 bg-gradient-to-br from-[#00ff85]/20 to-transparent flex items-center justify-center backdrop-blur-3xl">
                <BarChart3 className="w-20 h-20 text-[#00ff85]" />
              </div>
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-4 h-4 bg-[#00ff85] rounded-full shadow-[0_0_20px_#00ff85]" />
            </motion.div>
          </div>
        </div>
      </section>

      {/* CTA Footer */}
      <section className="py-32 px-6 text-center">
        <h2 className="text-5xl md:text-7xl font-black uppercase italic tracking-tighter mb-12">Pronto per il calcio 4.0?</h2>
        <motion.button 
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
          onClick={() => router.push('/dashboard')}
          className="px-16 py-8 bg-[#00ff85] text-slate-950 rounded-3xl font-black text-2xl uppercase italic tracking-widest shadow-[0_20px_50px_rgba(0,255,133,0.3)]"
        >
          Enter Quant Dashboard
        </motion.button>
        <p className="mt-12 text-[10px] font-bold text-slate-500 uppercase tracking-[0.5em]">Football Quant Analytics © 2025-2026</p>
      </section>
    </div>
  );
};

const FeatureCard: React.FC<{ icon: React.ReactNode, title: string, desc: string }> = ({ icon, title, desc }) => (
  <motion.div 
    whileHover={{ y: -10 }}
    className="glass p-10 rounded-3xl border border-white/5 bg-gradient-to-br from-white/[0.02] to-transparent group hover:border-[#00ff85]/30 transition-all"
  >
    <div className="mb-8 p-4 bg-slate-900 w-fit rounded-2xl group-hover:scale-110 group-hover:bg-[#00ff85]/10 transition-all">
      {icon}
    </div>
    <h3 className="text-xl font-bold mb-4 uppercase italic tracking-tight">{title}</h3>
    <p className="text-slate-400 leading-relaxed text-sm">{desc}</p>
  </motion.div>
);

export default LandingPage;