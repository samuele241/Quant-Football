"use client";

import React from 'react';
import { motion } from 'framer-motion';
import { ProbabilityBar } from './ProbabilityBar';
import { Info } from 'lucide-react';

interface TeamCardProps {
  position: number;
  name: string;
  probability: number;
  currentElo: number;
  currentPoints: number;
  avgPoints: number;
  avgPosition: number;
  type: 'winner' | 'top4' | 'relegation';
  index: number;
}

const getPositionColor = (probability: number): string => {
  if (probability < 20) return 'bg-slate-700';
  if (probability < 50) return 'bg-yellow-600';
  if (probability < 80) return 'bg-orange-600';
  return 'bg-green-600';
};

export const TeamCard: React.FC<TeamCardProps> = React.memo(({
  position,
  name,
  probability,
  currentElo,
  currentPoints,
  avgPoints,
  avgPosition,
  type,
  index
}) => {
  const [showTooltip, setShowTooltip] = React.useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.3 }}
      className="group relative"
      onHoverStart={() => setShowTooltip(true)}
      onHoverEnd={() => setShowTooltip(false)}
    >
      <div className="bg-slate-800 hover:bg-slate-750 rounded-lg p-4 transition-all border border-slate-700 hover:border-slate-600 shadow-lg">
        <div className="flex items-start justify-between gap-4">
          {/* Left: Position & Team Info */}
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <div className={`w-8 h-8 rounded-full ${getPositionColor(probability)} flex items-center justify-center flex-shrink-0 shadow-md`}>
              <span className="text-xs font-bold text-white">#{position}</span>
            </div>
            
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-white truncate">
                {name.replace(/_/g, ' ')}
              </h3>
              <p className="text-xs text-slate-400">
                ELO {currentElo.toFixed(0)} • {currentPoints} pts
              </p>
            </div>
          </div>

          {/* Right: Probability */}
          <div className="text-right flex-shrink-0">
            <div className="inline-flex items-center gap-2">
              <span className="text-lg font-bold text-white">
                {probability.toFixed(1)}%
              </span>
              <button
                className="w-5 h-5 rounded-full bg-slate-700 hover:bg-slate-600 flex items-center justify-center transition-colors"
                title={`Avg position: ${avgPosition.toFixed(1)}, Projected: ${avgPoints.toFixed(0)} pts`}
              >
                <Info className="w-3 h-3 text-slate-400" />
              </button>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Proj: <span className="text-slate-200">{avgPoints.toFixed(0)} pts</span>
            </p>
          </div>
        </div>

        {/* Probability Bar */}
        <div className="mt-3">
          <ProbabilityBar value={probability} showLabel={false} />
        </div>

        {/* Tooltip */}
        {showTooltip && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-full left-0 mb-2 bg-slate-900 border border-slate-700 rounded-lg p-3 w-48 text-xs text-slate-300 z-10 shadow-xl whitespace-nowrap"
          >
            <p className="mb-2"><span className="text-slate-200 font-semibold">Avg Pos:</span> {avgPosition.toFixed(1)}</p>
            <p className="mb-2"><span className="text-slate-200 font-semibold">Current:</span> {currentPoints} pts</p>
            <p><span className="text-slate-200 font-semibold">Projected:</span> {avgPoints.toFixed(0)} pts</p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
});

TeamCard.displayName = 'TeamCard';