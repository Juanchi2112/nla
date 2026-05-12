"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"
import { Building2, FlaskConical, ArrowRight } from "lucide-react"
import { Button } from "@/components/ui/button"

const useCases = [
  {
    icon: Building2,
    title: "AI Infrastructure Teams",
    subtitle: "Safety Monitoring",
    description: "Monitor auditable AI deployments with confidence. Real-time alignment checks for safety compliance, failure detection, and forensic reporting.",
    features: ["Local inference support", "Audit trail logs", "Open rule sets"],
  },
  {
    icon: FlaskConical,
    title: "Safety Researchers",
    subtitle: "Open Framework",
    description: "Access residual stream data in real-time. Use the open research framework for mechanistic interpretability experiments at inference time.",
    features: ["Residual stream access", "SAE feature inspection", "Custom NLA Actor training"],
  },
]

export function UseCases() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-3xl mx-auto"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            Use Cases
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
            Built for those who need certainty.
          </h2>
        </motion.div>

        <div className="mt-16 grid md:grid-cols-2 gap-8">
          {useCases.map((useCase, index) => (
            <motion.div
              key={useCase.title}
              initial={{ opacity: 0, y: 24 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + index * 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="group p-8 rounded-xl bg-card border border-border hover:border-primary/30 transition-all"
            >
              <div className="flex items-start gap-4 mb-6">
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center flex-shrink-0">
                  <useCase.icon className="w-7 h-7 text-primary" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold text-foreground">{useCase.title}</h3>
                  <p className="text-sm text-primary font-medium">{useCase.subtitle}</p>
                </div>
              </div>
              
              <p className="text-muted-foreground leading-relaxed mb-6">
                {useCase.description}
              </p>

              <ul className="space-y-2">
                {useCase.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm text-muted-foreground">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary" />
                    {feature}
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
