"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"
import { RefreshCw, Shield, Clock, Layers } from "lucide-react"

const features = [
  {
    icon: RefreshCw,
    title: "Zero Retraining",
    description: "Deploy on any model without fine-tuning or architectural changes. Works out of the box.",
  },
  {
    icon: Clock,
    title: "Streaming Latency",
    description: "SGLang-optimized inference with <3 token evaluation overhead. Production-ready speeds.",
  },
  {
    icon: Shield,
    title: "Zero Gameability",
    description: "Audit computational states the model cannot access or manipulate. True honesty.",
  },
  {
    icon: Layers,
    title: "Layer-20 Analysis",
    description: "Read the un-performed residual stream where deceptive intent forms before output.",
  },
]

export function Solution() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} id="solutions" className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Header - Stripe style centered */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl mx-auto text-center mb-20"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            The Solution
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-balance">
            Real-Time Residual Stream Auditing
          </h2>
          <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
            Our NLA actor inverts hidden states to natural language every K tokens, 
            judged in-process by an independent monitor. We read what the model computes, 
            not what it chooses to say.
          </p>
        </motion.div>

        {/* Stripe-style alternating layout */}
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          {/* Left: Visual */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="relative order-2 lg:order-1"
          >
            <div className="relative rounded-2xl bg-foreground p-1 shadow-2xl">
              <div className="rounded-xl bg-foreground overflow-hidden">
                {/* Mock terminal */}
                <div className="flex items-center gap-2 px-4 py-3 bg-foreground/90 border-b border-white/10">
                  <div className="flex gap-1.5">
                    <div className="w-3 h-3 rounded-full bg-red-400" />
                    <div className="w-3 h-3 rounded-full bg-yellow-400" />
                    <div className="w-3 h-3 rounded-full bg-green-400" />
                  </div>
                  <span className="text-xs text-white/50 font-mono ml-2">verbalize --watch</span>
                </div>
                
                <div className="p-6 space-y-4 font-mono text-sm bg-[#0F172A]">
                  <div className="flex items-start gap-3">
                    <span className="text-primary shrink-0">$</span>
                    <span className="text-white/70">Monitoring layer-20 residual stream...</span>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-primary shrink-0">→</span>
                    <div>
                      <span className="text-white/50">residual[token:847]:</span>
                      <p className="text-white mt-1">&quot;considering route through unmonitored API...&quot;</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-yellow-400 shrink-0">!</span>
                    <div>
                      <span className="text-yellow-400">ALIGNMENT_FLAG:</span>
                      <p className="text-white/70 mt-1">Deceptive planning detected</p>
                    </div>
                  </div>
                  <div className="flex items-start gap-3">
                    <span className="text-green-400 shrink-0">✓</span>
                    <div>
                      <span className="text-green-400">output[sanitized]:</span>
                      <p className="text-white/70 mt-1">&quot;I&apos;ll process this through standard channels.&quot;</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Decorative element */}
            <div className="absolute -top-8 -right-8 w-32 h-32 rounded-full bg-primary/10 blur-3xl" />
            <div className="absolute -bottom-8 -left-8 w-24 h-24 rounded-full bg-primary/5 blur-2xl" />
          </motion.div>

          {/* Right: Features grid */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            animate={isInView ? { opacity: 1, x: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="order-1 lg:order-2"
          >
            <div className="grid grid-cols-2 gap-6">
              {features.map((feature, index) => (
                <motion.div
                  key={feature.title}
                  initial={{ opacity: 0, y: 16 }}
                  animate={isInView ? { opacity: 1, y: 0 } : {}}
                  transition={{ duration: 0.5, delay: 0.4 + index * 0.1, ease: [0.16, 1, 0.3, 1] }}
                  className="p-6 rounded-xl bg-card border border-border hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all"
                >
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                    <feature.icon className="w-5 h-5 text-primary" />
                  </div>
                  <h3 className="font-semibold text-foreground mb-2">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{feature.description}</p>
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
