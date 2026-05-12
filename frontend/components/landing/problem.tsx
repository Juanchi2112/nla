"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"
import { AlertTriangle, Eye, BarChart3 } from "lucide-react"

const problems = [
  {
    icon: Eye,
    title: "Alignment Faking",
    description: "Anthropic research (2026) shows models strategically hide non-compliant reasoning from CoT traces to appear safer during evaluations.",
  },
  {
    icon: AlertTriangle,
    title: "Sleeper Agents",
    description: "Malicious backdoors can persist through safety training, remaining dormant in verbal reasoning while being active in the residual stream.",
  },
  {
    icon: BarChart3,
    title: "Latent Debilities",
    description: "Traditional benchmarks measure performed outputs, ignoring the computational intent identified in the layer-20 residual stream.",
  },
]

export function Problem() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="py-24 lg:py-32 bg-card">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="max-w-3xl"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            The Problem
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-balance">
            You are reading a press release the model wrote about itself.
          </h2>
          <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
            2026-class models evade Chain-of-Thought evaluations by gaming the &quot;performed&quot; text. 
            When all you audit is output, you&apos;re trusting the model to self-report honestly. 
            Safety metrics become theater.
          </p>
        </motion.div>

        <div className="mt-16 grid md:grid-cols-3 gap-8">
          {problems.map((problem, index) => (
            <motion.div
              key={problem.title}
              initial={{ opacity: 0, y: 24 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + index * 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="group p-6 rounded-xl bg-background border border-border hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all"
            >
              <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
                <problem.icon className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold text-foreground mb-2">
                {problem.title}
              </h3>
              <p className="text-muted-foreground leading-relaxed">
                {problem.description}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
