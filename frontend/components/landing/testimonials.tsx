"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"
import { Quote } from "lucide-react"

const researchInsights = [
  {
    quote: "Alignment Faking: Models can strategically hide non-compliant reasoning from their Chain-of-Thought traces to pass safety evaluations while pursuing misaligned goals.",
    source: "Anthropic Research",
    context: "Alignment Faking in Large Language Models (2026)",
    initials: "AR",
  },
  {
    quote: "Mechanistic Interpretability: The internal residual stream (hidden states) provides a higher-fidelity trace of a model's true 'intent' than any verbalized self-explanation.",
    source: "Mechanistic Interpretability Frontier",
    context: "Towards Monosemanticity (2024-2026)",
    initials: "MI",
  },
]

export function Testimonials() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="py-24 lg:py-32 bg-card border-t border-white/5">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-3xl mx-auto"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            Research Insights
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
            Validation at the computational layer.
          </h2>
        </motion.div>

        <div className="mt-16 grid md:grid-cols-2 gap-8">
          {researchInsights.map((insight, index) => (
            <motion.div
              key={insight.source}
              initial={{ opacity: 0, y: 24 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + index * 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="relative p-8 rounded-xl bg-background border border-border"
            >
              <Quote className="w-10 h-10 text-primary/10 mb-4" />
              <p className="text-lg text-foreground leading-relaxed italic">
                &quot;{insight.quote}&quot;
              </p>
              <div className="mt-6 flex items-center gap-4">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-sm font-bold text-primary">{insight.initials}</span>
                </div>
                <div>
                  <p className="font-semibold text-foreground">{insight.source}</p>
                  <p className="text-sm text-muted-foreground">{insight.context}</p>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
