"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"
import { Button } from "@/components/ui/button"
import { ArrowRight, Github } from "lucide-react"

export function FinalCTA() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <section ref={ref} id="contribute" className="py-24 lg:py-32 bg-foreground relative overflow-hidden">
      {/* Background - subtle professional gradient */}
      <div className="absolute inset-0">
        <div className="absolute top-0 right-0 w-[800px] h-[800px] rounded-full bg-primary/10 blur-[150px]" />
        <div className="absolute bottom-0 left-0 w-[600px] h-[600px] rounded-full bg-primary/5 blur-[120px]" />
      </div>

      <div className="relative max-w-4xl mx-auto px-6 lg:px-8 text-center">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
        >
          <h2 className="text-3xl lg:text-5xl font-bold tracking-tight text-background text-balance leading-[1.1]">
            Contribute to <span className="italic text-primary-foreground underline decoration-primary/30 underline-offset-8">Transparent AI.</span>
          </h2>
          <p className="mt-8 text-lg text-background/70 leading-relaxed max-w-2xl mx-auto">
            Verbalize is an open-source contribution to the mechanistic interpretability community. 
            Help us build tools that expose the true computational intent of advanced agents.
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Button
            asChild
            size="lg"
            className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-full px-10 h-14 text-base font-bold hover:-translate-y-0.5 transition-all shadow-xl shadow-black/20"
          >
            <a href="https://github.com/Juanchi2112/nla" target="_blank" rel="noopener noreferrer">
              <Github className="mr-2 w-5 h-5" />
              View Source on GitHub
            </a>
          </Button>
          <Button
            asChild
            variant="outline"
            size="lg"
            className="rounded-full px-10 h-14 text-base font-bold bg-transparent border-background/20 text-background hover:bg-background/10 hover:text-background transition-all"
          >
            <a href="https://transformer-circuits.pub/2026/nla/index.html" target="_blank" rel="noopener noreferrer">
              Read Technical Paper
              <ArrowRight className="ml-2 w-4 h-4" />
            </a>
          </Button>
        </motion.div>
      </div>
    </section>
  )
}
