"use client";

import React from 'react';
import { motion } from 'framer-motion';

export const LoadingSkeleton: React.FC = () => {
  const skeletonVariants = {
    animate: {
      backgroundColor: ['#1e293b', '#334155', '#1e293b'],
      transition: { duration: 1.5, repeat: Infinity }
    }
  };

  return (
    <div className="space-y-4">
      {[...Array(5)].map((_, i) => (
        <motion.div
          key={i}
          className="bg-slate-700 rounded-lg p-4 h-20"
          variants={skeletonVariants}
          animate="animate"
        />
      ))}
    </div>
  );
};