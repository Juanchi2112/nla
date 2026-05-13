"use client"

import { motion, useAnimation } from "framer-motion"
import { Button } from "@/components/ui/button"
import { ArrowRight } from "lucide-react"
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

import HeroAnimation from "@/components/animation/HeroAnimation"

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
    <section className="relative min-h-screen flex items-center pt-20 overflow-hidden bg-background">
      {/* Static neural pattern background */}
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--primary)_0%,_transparent_70%)] opacity-10" />
        <NeuralPatternBackground />
      </div>

      <div className="relative max-w-7xl mx-auto px-6 lg:px-8 py-20 lg:py-32 w-full z-10">
        <div className="grid lg:grid-cols-2 gap-16 lg:gap-24 items-center">
          {/* Left: Content */}
          <div className="order-2 lg:order-1">
            {/* Eyebrow */}

            {/* H1 */}
            <motion.h1
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
              className="mt-8 text-5xl lg:text-7xl font-bold tracking-tight text-foreground leading-[0.95]"
            >
              Stop trusting<br />
              <span className="text-muted-foreground/30 italic font-serif">the surface.</span><br />
              <span className="text-primary underline decoration-primary/20 underline-offset-12 decoration-4">Read the trace.</span>
            </motion.h1>

            {/* Subheadline with technical hook */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.3 }}
              className="mt-10 space-y-6"
            >
              <p className="text-lg lg:text-xl text-muted-foreground leading-relaxed max-w-lg">
                Chain-of-Thought is just another output. Verbalize decodes the model's internal activations to expose deceptive execution before it reaches the sampler.
              </p>
              
              <div className="flex items-center gap-4 text-xs font-mono text-muted-foreground/60 border-l border-primary/30 pl-4 py-1">
                <span>Loss: 0.042</span>
                <span className="w-1 h-1 rounded-full bg-border" />
                <span>Feature Sparsity: 0.98</span>
                <span className="w-1 h-1 rounded-full bg-border" />
                <span>Top-K: 32</span>
              </div>
            </motion.div>

            {/* CTAs */}
            <motion.div
              initial={{ opacity: 0, y: 24 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.55, ease: [0.16, 1, 0.3, 1] }}
              className="mt-10 flex flex-col sm:flex-row items-start gap-4"
            >
              <Button
                asChild
                size="lg"
                className="bg-foreground hover:bg-foreground/90 text-background rounded-full px-8 h-12 text-base font-medium hover:-translate-y-0.5 transition-all shadow-lg"
              >
                <a href="#contribute">
                  Contribute to Transparent AI
                  <ArrowRight className="ml-2 w-4 h-4" />
                </a>
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
            <div className="relative bg-card rounded-2xl p-4 shadow-2xl overflow-hidden border border-border">
               <HeroAnimation />
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
