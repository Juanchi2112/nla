"use client"

import { motion } from "framer-motion"

const concepts = [
  "Mechanistic Interpretability",
  "Residual Stream Analysis",
  "Alignment Auditing",
  "Natural Language Autoencoders",
  "Hidden State Decoding",
  "Deception Detection",
  "Sandbagging Prevention",
  "Real-Time Monitoring",
  "Layer-20 Extraction",
  "Computational Honesty",
  "Token-Level Analysis",
  "Activation Vectors",
  "Chain-of-Thought Bypass",
  "Enterprise Safety",
]

export function MarqueeBanner() {
  // Duplicate for seamless loop
  const items = [...concepts, ...concepts, ...concepts]
  
  return (
    <div className="relative py-6 bg-[#8FADA8] overflow-hidden">
      {/* Top border accent */}
      <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
      
      {/* Scrolling content */}
      <div className="relative flex">
        <motion.div
          className="flex items-center gap-8 whitespace-nowrap"
          animate={{ x: [0, -2800] }}
          transition={{
            x: {
              duration: 40,
              repeat: Infinity,
              ease: "linear",
            },
          }}
        >
          {items.map((concept, i) => (
            <div key={i} className="flex items-center gap-8">
              <span className="text-sm sm:text-base font-medium text-white/80 uppercase tracking-widest">
                {concept}
              </span>
              <span className="text-primary text-lg">*</span>
            </div>
          ))}
        </motion.div>
      </div>
      
      {/* Gradient fade edges */}
      <div className="absolute inset-y-0 left-0 w-24 bg-gradient-to-r from-[#8FADA8] to-transparent z-10" />
      <div className="absolute inset-y-0 right-0 w-24 bg-gradient-to-l from-[#8FADA8] to-transparent z-10" />
      
      {/* Bottom border accent */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/50 to-transparent" />
    </div>
  )
}
