"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"

const investors = [
  "Founders Fund",
  "a16z",
  "Sequoia",
  "Greylock",
  "Index Ventures",
  "Khosla Ventures",
]

export function Investors() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            Our Investors
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
            Backed by leaders in Asymmetric Impact.
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mt-16 flex flex-wrap items-center justify-center gap-8 lg:gap-16"
        >
          {investors.map((investor, index) => (
            <motion.div
              key={investor}
              initial={{ opacity: 0 }}
              animate={isInView ? { opacity: 1 } : {}}
              transition={{ duration: 0.4, delay: 0.3 + index * 0.05 }}
              className="text-xl lg:text-2xl font-semibold text-muted-foreground/60 hover:text-muted-foreground transition-colors"
            >
              {investor}
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
