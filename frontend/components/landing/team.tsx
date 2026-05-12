"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"

const team = [
  {
    name: "Dr. Sarah Chen",
    role: "CEO & Co-founder",
    bio: "Former Anthropic interpretability researcher. Published 12 papers on feature extraction.",
    initials: "SC",
  },
  {
    name: "Marcus Rodriguez",
    role: "CTO & Co-founder",
    bio: "SGLang core contributor. Optimized VRAM allocation for multi-model inference.",
    initials: "MR",
  },
  {
    name: "Dr. Elena Volkov",
    role: "Head of Research",
    bio: "PhD MIT. Pioneered residual stream inversion techniques. 3,000+ citations.",
    initials: "EV",
  },
]

export function Team() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="py-24 lg:py-32 bg-card">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-3xl mx-auto"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            The Team
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
            Shipped by a team that understands the metal.
          </h2>
          <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
            SGLang core modifications. VRAM math. Production interpretability at scale.
          </p>
        </motion.div>

        <div className="mt-16 grid md:grid-cols-3 gap-8">
          {team.map((member, index) => (
            <motion.div
              key={member.name}
              initial={{ opacity: 0, y: 24 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.2 + index * 0.1, ease: [0.16, 1, 0.3, 1] }}
              className="text-center p-8 rounded-xl bg-background border border-border hover:border-primary/30 hover:shadow-lg hover:shadow-primary/5 transition-all"
            >
              <div className="w-20 h-20 rounded-full bg-primary/10 flex items-center justify-center mx-auto mb-6">
                <span className="text-2xl font-bold text-primary">{member.initials}</span>
              </div>
              <h3 className="text-xl font-semibold text-foreground">
                {member.name}
              </h3>
              <p className="mt-1 text-sm font-medium text-primary">
                {member.role}
              </p>
              <p className="mt-4 text-muted-foreground leading-relaxed">
                {member.bio}
              </p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
