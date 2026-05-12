"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef } from "react"
import { Terminal, Copy, Check, Github } from "lucide-react"
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
    <section ref={ref} className="py-24 lg:py-32 bg-card border-y border-white/5">
      <div className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-16 items-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 mb-4">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="text-[10px] font-bold uppercase tracking-widest text-primary">Open Source Release</span>
            </div>
            <span className="block text-sm font-medium text-muted-foreground uppercase tracking-widest mb-2">
              Run Locally
            </span>
            <h2 className="mt-4 text-3xl lg:text-5xl font-bold tracking-tight text-foreground text-balance">
              The Alignment Audit <span className="text-primary italic">Framework.</span>
            </h2>
            <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
              We&apos;ve open-sourced our full evaluation pipeline. Clone the repository to run automated red-teaming 
              and latent-space audits on your own local models.
            </p>
            
            <div className="mt-10 flex flex-col sm:flex-row gap-4">
              <Button 
                size="lg" 
                className="bg-primary hover:bg-primary/90 text-primary-foreground font-bold rounded-full px-8 h-12 shadow-lg shadow-primary/20 transition-all hover:-translate-y-0.5"
              >
                <Github className="mr-2 w-4 h-4" />
                Clone Repository
              </Button>
              <Button 
                variant="outline" 
                size="lg" 
                className="rounded-full px-8 h-12 font-bold border-border hover:bg-white/5 transition-all"
              >
                View Examples
              </Button>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={isInView ? { opacity: 1, scale: 1 } : {}}
            transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="rounded-2xl bg-black/40 border border-white/10 overflow-hidden shadow-2xl">
              <div className="flex items-center justify-between px-6 py-4 bg-white/[0.03] border-b border-white/10">
                <div className="flex items-center gap-2">
                  <Terminal className="w-4 h-4 text-primary" />
                  <span className="text-xs text-muted-foreground/60 font-mono tracking-widest uppercase">bash_session</span>
                </div>
                <button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-md text-xs text-primary/60 hover:text-primary hover:bg-primary/5 transition-colors"
                >
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy CLI command
                    </>
                  )}
                </button>
              </div>
              <div className="p-8">
                <pre className="font-mono text-sm text-foreground/80 leading-relaxed overflow-x-auto selection:bg-primary/20">
                  <code>{codeSnippet}</code>
                </pre>
              </div>
              <div className="px-8 py-3 bg-primary/[0.02] border-t border-white/5">
                 <div className="text-[10px] text-muted-foreground/40 font-mono italic">
                   Note: Requires NVIDIA A6000 (48GB VRAM) for local inference.
                 </div>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  )
}
