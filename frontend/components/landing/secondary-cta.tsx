"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"
import { Terminal, Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState } from "react"

const codeSnippet = `uv run python -m audit.run \\
  --model qwen/qwen2.5-7b-instruct \\
  --rules fintech_compliance.yaml \\
  --output results/`

export function SecondaryCTA() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(codeSnippet)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <section ref={ref} className="py-24 lg:py-32 bg-card">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-amber-100 border border-amber-200 mb-4">
              <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
              <span className="text-xs font-medium text-amber-700">Coming Soon</span>
            </div>
            <span className="block text-sm font-medium text-primary uppercase tracking-wider">
              Try It Yourself
            </span>
            <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground text-balance">
              We&apos;re working on making the framework publicly available.
            </h2>
            <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
              Our open-source evaluation framework is under active development. 
              Soon you&apos;ll be able to clone the repo and run alignment audits on your own models in under 5 minutes.
            </p>
            
            <div className="mt-8 flex flex-col sm:flex-row gap-4">
              <Button 
                size="lg" 
                className="bg-primary hover:bg-primary/90 text-primary-foreground rounded-full px-8"
                disabled
              >
                Coming Soon
              </Button>
              <Button 
                variant="outline" 
                size="lg" 
                className="rounded-full px-8"
              >
                Join Waitlist
              </Button>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="rounded-xl bg-foreground border border-foreground/80 overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between px-4 py-3 bg-foreground/90 border-b border-white/10">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-primary" />
                  <span className="text-sm text-white/60 font-mono">terminal</span>
                </div>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs text-white/60 hover:text-white hover:bg-white/5 transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy
                    </>
                  )}
                </button>
              </div>
              <div className="p-6">
                <pre className="font-mono text-sm text-white/80 leading-relaxed overflow-x-auto">
                  <code>{codeSnippet}</code>
                </pre>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
