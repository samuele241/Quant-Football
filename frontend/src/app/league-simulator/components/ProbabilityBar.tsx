"use client";

import React from 'react';
import { motion } from 'framer-motion';

interface ProbabilityBarProps {
  value: number;
  showLabel?: boolean;
}

const getGradientColor = (probability: number): string => {
  if (probability < 20) return '#ef4444'; // Red
  if (probability < 50) return '#f59e0b'; // Yellow
  if (probability < 80) return '#f97316'; // Orange
  return '#10b981'; // Green
};

export const ProbabilityBar: React.FC<ProbabilityBarProps> = ({ 
  value, 
  showLabel = true 
}) => {
  return (
    <div className="w-full">
      <div className="w-full bg-slate-700 rounded-full h-5 overflow-hidden relative shadow-inner">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${value}%` }}
          transition={{ duration: 1, ease: "easeOut" }}
          className="h-5 rounded-full flex items-center justify-end pr-2 transition-all"
          style={{ backgroundColor: getGradientColor(value) }}
        >
          {value > 10 && showLabel && (
            <span className="text-xs font-bold text-white drop-shadow">
              {value.toFixed(1)}%
            </span>
          )}
        </motion.div>
      </div>
      {!showLabel && (
        <span className="text-xs font-semibold text-slate-300 mt-1 block text-right">
          {value.toFixed(1)}%
        </span>
      )}
    </div>
  );
};