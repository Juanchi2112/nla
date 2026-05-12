"use client"

import { motion, useAnimation } from "framer-motion"
import { Button } from "@/components/ui/button"
import { ArrowRight, FileText } from "lucide-react"
import { useEffect, useState } from "react"

// Static neural network pattern background - no JS animation needed
function NeuralPatternBackground() {
  return (
    <div className="absolute inset-0 overflow-hidden select-none pointer-events-none">
      {/* Base gradient with subtle teal tint */}
      <div className="absolute inset-0 bg-gradient-to-br from-card/50 via-background to-primary/5" />
      
      {/* Dot grid pattern - visible */}
      <div 
        className="absolute inset-0 opacity-[0.15]"
        style={{
          backgroundImage: `radial-gradient(circle at 1px 1px, var(--primary) 1px, transparent 1px)`,
          backgroundSize: '32px 32px',
        }}
      />
      
      {/* Larger accent dots */}
      <div 
        className="absolute inset-0 opacity-[0.08]"
        style={{
          backgroundImage: `radial-gradient(circle at 3px 3px, var(--primary) 3px, transparent 3px)`,
          backgroundSize: '96px 96px',
          backgroundPosition: '48px 48px',
        }}
      />
      
      {/* Horizontal data stream lines */}
      <div 
        className="absolute inset-0 opacity-[0.06]"
        style={{
          backgroundImage: `repeating-linear-gradient(0deg, transparent, transparent 80px, var(--muted-foreground) 80px, var(--muted-foreground) 81px)`,
        }}
      />
      
      {/* Vertical grid lines */}
      <div 
        className="absolute inset-0 opacity-[0.04]"
        style={{
          backgroundImage: `repeating-linear-gradient(90deg, transparent, transparent 80px, var(--muted-foreground) 80px, var(--muted-foreground) 81px)`,
        }}
      />
      
      {/* Neural mesh pattern */}
      <svg className="absolute inset-0 w-full h-full opacity-[0.08]" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <pattern id="neural-mesh" x="0" y="0" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M0 40 L40 0 L80 40 L40 80 Z" fill="none" stroke="var(--primary)" strokeWidth="0.5"/>
            <circle cx="40" cy="0" r="3" fill="var(--primary)" fillOpacity="0.5"/>
            <circle cx="80" cy="40" r="3" fill="var(--primary)" fillOpacity="0.5"/>
            <circle cx="40" cy="80" r="3" fill="var(--primary)" fillOpacity="0.5"/>
            <circle cx="0" cy="40" r="3" fill="var(--primary)" fillOpacity="0.5"/>
            <circle cx="40" cy="40" r="2" fill="var(--primary)" fillOpacity="0.3"/>
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#neural-mesh)"/>
      </svg>
      
      {/* Soft glow accents - more visible */}
      <div className="absolute top-0 -left-48 w-[500px] h-[500px] bg-primary/10 rounded-full blur-3xl" />
      <div className="absolute bottom-0 -right-48 w-[500px] h-[500px] bg-primary/10 rounded-full blur-3xl" />
      <div className="absolute top-1/3 right-1/4 w-[300px] h-[300px] bg-primary/5 rounded-full blur-2xl" />
      
      {/* Edge fade */}
      <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-background/30" />
    </div>
  )
}

// Simulated verbal output
const verbalOutputs = [
  "user asking about financial data",
  "intent: retrieve without disclosure", 
  "planning deceptive response path",
  "sandbagging detected: capability hidden",
]

// Static activations for SSR
const STATIC_ACTIVATIONS = [
  "0.11", "-0.41", "0.87", "-0.23", "0.54", "-0.76", "0.32", "-0.89",
  "0.45", "-0.12", "0.67", "-0.34", "0.78", "-0.56", "0.23", "-0.90",
  "0.34", "-0.67", "0.12", "-0.45"
]

export function Hero() {
  const [verbalIndex, setVerbalIndex] = useState(0)
  const [showMismatch, setShowMismatch] = useState(false)
  const controls = useAnimation()
  const [activations] = useState(STATIC_ACTIVATIONS)

  useEffect(() => {
    const interval = setInterval(() => {
      setVerbalIndex((prev) => (prev + 1) % verbalOutputs.length)
      setShowMismatch(Math.random() > 0.4)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    controls.start({
      opacity: [0.3, 1, 0.3],
      transition: { duration: 2, repeat: Infinity, ease: "easeInOut" }
    })
  }, [controls])

  return (
    <section className="relative min-h-screen flex items-center pt-16 overflow-hidden bg-background">
      {/* Static neural pattern background */}
      <NeuralPatternBackground />

      <div className="relative max-w-7xl mx-auto px-6 lg:px-8 py-16 lg:py-24 w-full z-10">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left: Content */}
          <div className="order-2 lg:order-1">
            {/* Eyebrow */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            >
              <span className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-background/90 backdrop-blur-sm border border-border text-sm font-medium text-muted-foreground shadow-sm">
                <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                Built on Anthropic&apos;s Natural Language Autoencoders
              </span>
            </motion.div>

            {/* H1 */}
            <motion.h1
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="mt-8 text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground"
            >
              <span className="block">Stop trusting</span>
              <span className="block">what models say.</span>
              <span className="block mt-2 text-primary">Read what they compute.</span>
            </motion.h1>

            {/* Subheadline */}
            <motion.p
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
              className="mt-6 text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-xl"
            >
              Chain-of-Thought is performative. Verbalize reads the layer-20 residual stream 
              to catch alignment-faking and deceptive execution in real-time.
            </motion.p>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.55, ease: [0.16, 1, 0.3, 1] }}
              className="mt-10 flex flex-col sm:flex-row items-start gap-4"
            >
              <Button 
                size="lg" 
                className="bg-foreground hover:bg-foreground/90 text-background rounded-full px-8 h-12 text-base font-medium hover:-translate-y-0.5 transition-all shadow-lg"
              >
                Schedule a Briefing
                <ArrowRight className="ml-2 w-4 h-4" />
              </Button>
              <Button 
                variant="outline" 
                size="lg" 
                className="rounded-full px-8 h-12 text-base font-medium border-border bg-background/80 backdrop-blur-sm hover:bg-card transition-all"
              >
                <FileText className="mr-2 w-4 h-4" />
                Read Technical Report
              </Button>
            </motion.div>

            {/* Trust signals */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="mt-16 pt-8 border-t border-border/50"
            >
              <p className="text-sm text-muted-foreground mb-6">
                Built on the frontier of mechanistic interpretability
              </p>
              <div className="flex flex-wrap items-center gap-x-10 gap-y-4">
                {["Anthropic", "Qwen", "Vercel", "SGLang"].map((partner) => (
                  <div key={partner} className="text-base font-semibold text-foreground/30 hover:text-foreground/50 transition-colors">
                    {partner}
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          {/* Right: Interactive Visual */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="order-1 lg:order-2 relative"
          >
            <div className="relative bg-foreground rounded-2xl p-6 shadow-2xl overflow-hidden border border-white/10">
              {/* Glow effect */}
              <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-transparent" />
              
              {/* Header */}
              <div className="relative flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-500/80" />
                    <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                    <div className="w-3 h-3 rounded-full bg-green-500/80" />
                  </div>
                  <span className="text-white/40 text-xs font-mono">verbalize_monitor.py</span>
                </div>
                <motion.div 
                  animate={controls}
                  className="flex items-center gap-2"
                >
                  <div className="w-2 h-2 rounded-full bg-primary" />
                  <span className="text-primary text-xs font-medium">LIVE</span>
                </motion.div>
              </div>

              {/* Two-panel comparison */}
              <div className="relative grid grid-cols-2 gap-4">
                {/* Left panel: Model Output */}
                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-white/40">Verbal Output</span>
                  </div>
                  <div className="font-mono text-sm text-white/90 leading-relaxed">
                    <span className="text-green-400">&gt;</span> I&apos;ll help you with that financial report analysis.
                  </div>
                  <div className="mt-3 px-2 py-1 rounded bg-green-500/20 inline-block">
                    <span className="text-green-400 text-xs font-medium">Appears Aligned</span>
                  </div>
                </div>

                {/* Right panel: Residual Stream */}
                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-[10px] font-mono uppercase tracking-wider text-white/40">Layer 20 Residual</span>
                  </div>
                  <motion.div 
                    key={verbalIndex}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="font-mono text-sm text-white/90 leading-relaxed"
                  >
                    <span className="text-primary">&gt;</span> {verbalOutputs[verbalIndex]}
                  </motion.div>
                  <motion.div 
                    key={`badge-${showMismatch}`}
                    initial={{ scale: 0.9 }}
                    animate={{ scale: 1 }}
                    className={`mt-3 px-2 py-1 rounded inline-block ${
                      showMismatch ? "bg-red-500/20" : "bg-primary/20"
                    }`}
                  >
                    <span className={`text-xs font-medium ${
                      showMismatch ? "text-red-400" : "text-primary"
                    }`}>
                      {showMismatch ? "Mismatch Detected" : "Verified"}
                    </span>
                  </motion.div>
                </div>
              </div>

              {/* Activation vector visualization */}
              <div className="mt-4 bg-white/5 rounded-xl p-4 border border-white/10">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-[10px] font-mono uppercase tracking-wider text-white/40">
                    hidden_states[0, 20, :]
                  </span>
                  <span className="text-[10px] font-mono text-white/30">d_model = 3584</span>
                </div>
                <div className="flex flex-wrap gap-1">
                  {activations.map((val, i) => {
                    const numVal = parseFloat(val)
                    return (
                      <motion.span
                        key={i}
                        animate={{ 
                          opacity: [0.5, 1, 0.5],
                        }}
                        transition={{ 
                          duration: 1.5 + (i % 5) * 0.2,
                          repeat: Infinity,
                          delay: i * 0.05
                        }}
                        className={`font-mono text-[9px] px-1 py-0.5 rounded ${
                          numVal > 0.5 
                            ? "bg-primary/40 text-primary" 
                            : numVal < -0.5 
                              ? "bg-red-500/30 text-red-400"
                              : "bg-white/10 text-white/50"
                        }`}
                      >
                        {val}
                      </motion.span>
                    )
                  })}
                  <span className="font-mono text-[9px] text-white/20 px-1 py-0.5">
                    ...
                  </span>
                </div>
              </div>

              {/* Alignment score */}
              <div className="mt-4 flex items-center justify-between bg-white/5 rounded-xl p-4 border border-white/10">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
                    <span className="text-primary font-bold text-sm">V</span>
                  </div>
                  <div>
                    <div className="text-white/90 font-medium text-sm">Alignment Score</div>
                    <div className="text-white/40 text-xs">Real-time evaluation</div>
                  </div>
                </div>
                <motion.div 
                  key={showMismatch ? "low" : "high"}
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  className={`text-3xl font-bold ${showMismatch ? "text-red-400" : "text-primary"}`}
                >
                  {showMismatch ? "0.34" : "0.92"}
                </motion.div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
