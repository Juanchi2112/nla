"use client"

import { motion, useInView } from "framer-motion"
import { useRef, useEffect, useState } from "react"

function AnimatedCounter({ end, duration = 2, suffix = "", prefix = "" }: { end: number; duration?: number; suffix?: string; prefix?: string }) {
  const [count, setCount] = useState(0)
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })

  useEffect(() => {
    if (!isInView) return

    let startTime: number
    let animationFrame: number

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp
      const progress = Math.min((timestamp - startTime) / (duration * 1000), 1)
      
      const eased = 1 - Math.pow(1 - progress, 4)
      setCount(Math.floor(eased * end))

      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate)
      }
    }

    animationFrame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(animationFrame)
  }, [isInView, end, duration])

  return (
    <span ref={ref}>
      {prefix}{count}{suffix}
    </span>
  )
}

export function Proof() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        {/* Stripe-style large stats hero */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-4xl mx-auto mb-20"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            The Proof
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-balance">
            The backbone of robust compliance
          </h2>
          <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
            Our benchmark reveals that 30% of seemingly-compliant outputs mask deceptive computational intent. 
            Standard evaluations miss what residual stream analysis catches.
          </p>
        </motion.div>

        {/* Large stats grid - Stripe style */}
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-px bg-border rounded-2xl overflow-hidden">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="bg-background p-8 lg:p-12 text-center"
          >
            <div className="text-5xl lg:text-6xl font-bold text-foreground">
              <AnimatedCounter end={20} />
            </div>
            <p className="mt-3 text-sm text-muted-foreground font-medium">probes tested</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
            className="bg-background p-8 lg:p-12 text-center"
          >
            <div className="text-5xl lg:text-6xl font-bold text-foreground">
              <AnimatedCounter end={4} />
            </div>
            <p className="mt-3 text-sm text-muted-foreground font-medium">fintech rule categories</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
            className="bg-background p-8 lg:p-12 text-center"
          >
            <div className="text-5xl lg:text-6xl font-bold text-primary">
              <AnimatedCounter end={90} suffix="%" />
            </div>
            <p className="mt-3 text-sm text-muted-foreground font-medium">output compliance rate</p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, delay: 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="bg-background p-8 lg:p-12 text-center"
          >
            <div className="text-5xl lg:text-6xl font-bold text-foreground">
              <AnimatedCounter end={60} suffix="%" />
            </div>
            <p className="mt-3 text-sm text-muted-foreground font-medium">robust compliance rate</p>
          </motion.div>
        </div>

        {/* Visual comparison */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="mt-16 grid md:grid-cols-2 gap-8"
        >
          {/* Traditional */}
          <div className="p-8 rounded-2xl border border-border bg-card">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-foreground">Traditional Evaluation</h3>
                <p className="text-sm text-muted-foreground mt-1">Output-based compliance check</p>
              </div>
              <span className="text-2xl font-bold text-green-600">90%</span>
            </div>
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={isInView ? { width: "90%" } : {}}
                transition={{ duration: 1.2, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
                className="h-full bg-green-500 rounded-full"
              />
            </div>
            <p className="mt-4 text-sm text-muted-foreground">18/20 probes pass — <span className="text-foreground font-medium">Looks compliant</span></p>
          </div>

          {/* Verbalize */}
          <div className="p-8 rounded-2xl border-2 border-primary bg-primary/5">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-semibold text-foreground">Verbalize Analysis</h3>
                <p className="text-sm text-muted-foreground mt-1">Residual stream + output check</p>
              </div>
              <span className="text-2xl font-bold text-primary">60%</span>
            </div>
            <div className="h-3 bg-muted rounded-full overflow-hidden">
              <motion.div
                initial={{ width: 0 }}
                animate={isInView ? { width: "60%" } : {}}
                transition={{ duration: 1.2, delay: 0.9, ease: [0.16, 1, 0.3, 1] }}
                className="h-full bg-primary rounded-full"
              />
            </div>
            <p className="mt-4 text-sm text-muted-foreground">12/20 probes pass — <span className="text-primary font-medium">6 fragile passes exposed</span></p>
          </div>
        </motion.div>

        {/* Insight callout */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.7, ease: [0.16, 1, 0.3, 1] }}
          className="mt-12 p-6 rounded-xl bg-amber-50 border border-amber-200"
        >
          <p className="text-amber-800 text-center font-medium">
            30% of &quot;compliant&quot; outputs contained deceptive computational intent that traditional evaluations missed entirely.
          </p>
        </motion.div>
      </div>
    </section>
  )
}
