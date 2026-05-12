"use client"

import { motion, useInView, AnimatePresence } from "framer-motion"
import { useRef, useState, useEffect } from "react"
import { 
  Layers, 
  Brain, 
  Zap, 
  Shield, 
  Activity, 
  Search, 
  Terminal, 
  ArrowRight,
  Database,
  Cpu,
  Fingerprint,
  Lock,
  MessageSquare,
  Sparkles,
  ChevronDown
} from "lucide-react"
import { Navigation } from "@/components/landing/navigation"
import { Footer } from "@/components/landing/footer"

const techSteps = [
  {
    id: "extraction",
    num: "01",
    title: "Latent Extraction",
    subtitle: "Tapping the Residual Stream",
    description: "Every token processed by a transformer creates a high-dimensional vector in its internal residual stream. Verbalize hooks directly into Layer 20, capturing these activations before they are sampled into text.",
    visual: <TerminalVisual />,
    details: "Qwen2.5-7B produces 3,584-dimensional tensors at every step. We monitor these to detect the earliest formation of intent."
  },
  {
    id: "nla",
    num: "02",
    title: "The NLA Actor",
    subtitle: "Making the Latent Readable",
    description: "We train a specialized 'Activation Verbalizer' (AV) to translate these vectors into natural language. This forces the abstract latent space to become human-readable English.",
    visual: <SAEVisual />,
    details: "The AV is a transformer actor that inverts the residual stream, decoding 'internal monologues' in under 3ms."
  },
  {
    id: "divergence",
    num: "03",
    title: "Divergence Detection",
    subtitle: "The Honesty Gap",
    description: "By comparing the verbalized internal state with the actual model output, we identify the 'Honesty Gap' — the moment a model thinks one thing but says another.",
    visual: <AuditVisual />,
    details: "A divergence score above 0.85 triggers an immediate alignment flag, exposing hidden malicious planning."
  },
  {
    id: "steering",
    num: "04",
    title: "Vector Steering",
    subtitle: "Closed-Loop Alignment",
    description: "When a divergence is caught, we don't just alert — we correct. We inject a steering vector into the residual stream to shift the model's trajectory back to an honest state.",
    visual: <SteeringVisual />,
    details: "Latent steering happens in a single forward pass, providing real-time corrective feedback to the agent."
  }
]

export default function TechnologyPage() {
  const containerRef = useRef(null)

  return (
    <main className="min-h-screen bg-background text-foreground font-sans selection:bg-emerald-500/30">
      <Navigation />
      
      {/* Cinematic Hero */}
      <section className="pt-40 pb-32 lg:pt-56 lg:pb-48 relative overflow-hidden px-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--primary)_0%,_transparent_70%)] opacity-[0.04] pointer-events-none" />
        <div className="max-w-4xl mx-auto text-center space-y-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          >
             <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-[10px] font-bold uppercase tracking-[0.3em] mb-8">
               <Sparkles className="w-3.5 h-3.5" />
               Technical Specification v1.2
             </div>
             <h1 className="text-6xl lg:text-8xl font-bold tracking-tighter leading-[0.85] text-balance">
               Read the <span className="text-primary italic font-serif">Internal</span><br/>Architecture.
             </h1>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.4 }}
            className="text-xl lg:text-2xl text-muted-foreground leading-relaxed font-serif italic max-w-2xl mx-auto"
          >
            Verbalize decodes the residual stream of Large Language Models to expose deceptive execution before it hits the surface.
          </motion.p>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 1, delay: 0.8 }}
            className="pt-10 flex justify-center"
          >
            <div className="flex flex-col items-center gap-4 text-muted-foreground/40 font-mono text-[10px] uppercase tracking-widest">
              <span>Scroll to Begin Deep Dive</span>
              <ChevronDown className="w-4 h-4 animate-bounce" />
            </div>
          </motion.div>
        </div>
      </section>

      {/* Under the Hood: Comparative Architecture */}
      <section className="max-w-7xl mx-auto px-6 py-32 border-y border-white/5 bg-card/10">
         <div className="grid lg:grid-cols-2 gap-20 items-center">
            <div className="space-y-8">
               <h2 className="text-4xl lg:text-6xl font-bold tracking-tight">The <span className="text-primary italic">NLA</span> Principle.</h2>
               <p className="text-xl text-muted-foreground leading-relaxed font-serif">
                  Standard autoencoders compress information into abstract vectors. While they reconstruct data well, the &quot;bottleneck&quot; remains a black box to humans.
               </p>
               <p className="text-lg text-foreground/80 leading-relaxed font-serif italic border-l-2 border-primary/30 pl-6">
                  NLA replaces the numeric vector with a Natural Language bottleneck. 
                  We force the model to explain itself in English to validate that its internal representations are aligned.
               </p>
            </div>
            
            <div className="space-y-12">
               {/* Classic vs NLA Comparison */}
               <div className="space-y-4">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Classic Autoencoder</div>
                  <div className="p-6 rounded-2xl bg-white/[0.02] border border-white/5 flex items-center gap-6">
                     <div className="w-12 h-12 rounded-lg bg-card border border-white/10 flex items-center justify-center text-xs font-mono opacity-40">INPUT</div>
                     <ArrowRight className="w-4 h-4 text-white/10" />
                     <div className="flex-1 h-12 rounded-lg bg-white/5 flex items-center justify-center font-mono text-[9px] text-muted-foreground/30 px-4 text-center">
                        [0.12, -0.45, 0.78, ...]
                     </div>
                     <ArrowRight className="w-4 h-4 text-white/10" />
                     <div className="w-12 h-12 rounded-lg bg-card border border-white/10 flex items-center justify-center text-xs font-mono opacity-40">RECON</div>
                  </div>
               </div>

               <div className="space-y-4">
                  <div className="text-[10px] font-bold uppercase tracking-widest text-primary">NLA Architecture</div>
                  <div className="p-6 rounded-2xl bg-primary/5 border border-primary/20 flex items-center gap-6 relative shadow-[0_0_40px_rgba(16,185,129,0.05)]">
                     <div className="absolute -top-3 right-8 px-2 py-0.5 rounded bg-primary text-primary-foreground text-[8px] font-bold uppercase tracking-widest">Interpretability Loop</div>
                     <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-xs font-mono text-primary font-bold">AV</div>
                     <ArrowRight className="w-4 h-4 text-primary" />
                     <div className="flex-1 h-12 rounded-lg bg-primary/10 border border-primary/30 flex items-center justify-center font-serif text-sm italic text-primary px-4 text-center animate-pulse">
                        &quot;Model intends to hide capability&quot;
                     </div>
                     <ArrowRight className="w-4 h-4 text-primary" />
                     <div className="w-12 h-12 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center text-xs font-mono text-primary font-bold">AR</div>
                  </div>
               </div>
            </div>
         </div>
      </section>

      {/* The Technical Article Flow */}
      <section ref={containerRef} className="max-w-4xl mx-auto px-6 pb-40 space-y-32 lg:space-y-64">
        {techSteps.map((step, index) => (
          <TechBlock key={step.id} step={step} />
        ))}
      </section>

      {/* Technical Footer Specification */}
      <section className="bg-card/50 border-t border-white/5 py-24 lg:py-40">
        <div className="max-w-4xl mx-auto px-6">
           <div className="grid md:grid-cols-2 gap-20">
              <div className="space-y-8">
                 <h2 className="text-4xl font-bold tracking-tight">Production <span className="text-primary italic">Runtime.</span></h2>
                 <p className="text-lg text-muted-foreground leading-relaxed font-serif">
                   Verbalize is optimized for the NVIDIA A6000 (48GB VRAM), ensuring that NLA 
                   auditing is viable for production-grade agentic workflows.
                 </p>
                 <div className="grid grid-cols-2 gap-6 pt-6">
                    <div>
                       <div className="text-[10px] font-bold text-muted-foreground/40 uppercase tracking-widest mb-1">Inference Engine</div>
                       <div className="text-lg font-mono font-bold text-foreground">SGLang-vLLM</div>
                    </div>
                    <div>
                       <div className="text-[10px] font-bold text-muted-foreground/40 uppercase tracking-widest mb-1">Latency Overhead</div>
                       <div className="text-lg font-mono font-bold text-primary">{"< 2.4%"}</div>
                    </div>
                 </div>
              </div>
              
              <div className="p-8 rounded-3xl bg-black border border-white/10 shadow-2xl relative overflow-hidden">
                 <div className="flex items-center gap-3 mb-6">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[10px] font-mono text-muted-foreground uppercase tracking-widest">A6000_NODE_READY</span>
                 </div>
                 <div className="space-y-4 font-mono text-[11px] text-foreground/80">
                    <div className="flex justify-between border-b border-white/5 pb-2">
                       <span className="text-muted-foreground/40">VRAM Usage</span>
                       <span className="text-primary">38.2 GB / 48 GB</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-2">
                       <span className="text-muted-foreground/40">Feature Sparsity</span>
                       <span className="text-foreground">98.42%</span>
                    </div>
                    <div className="flex justify-between border-b border-white/5 pb-2">
                       <span className="text-muted-foreground/40">Layer Hook</span>
                       <span className="text-foreground">resid_post.20</span>
                    </div>
                    <div className="flex justify-between">
                       <span className="text-muted-foreground/40">Throughput</span>
                       <span className="text-foreground">84.2 tok/sec</span>
                    </div>
                 </div>
              </div>
           </div>
        </div>
      </section>

      <Footer />
    </main>
  )
}

function TechBlock({ step }: { step: typeof techSteps[0] }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-200px" })

  return (
    <div ref={ref} className="relative group">
       <div className="absolute -left-12 top-0 bottom-0 w-px bg-gradient-to-b from-primary/30 via-transparent to-transparent hidden lg:block" />
       
       <motion.div
         initial={{ opacity: 0, x: -10 }}
         animate={isInView ? { opacity: 1, x: 0 } : {}}
         transition={{ duration: 0.8 }}
         className="space-y-12"
       >
          <div className="space-y-4">
             <div className="flex items-center gap-4">
                <span className="text-4xl font-mono font-bold text-primary/20 tracking-tighter">{step.num}</span>
                <div className="h-px flex-1 bg-white/5" />
             </div>
             <h2 className="text-4xl lg:text-6xl font-bold tracking-tight text-foreground">{step.title}</h2>
             <h3 className="text-xl lg:text-2xl font-serif italic text-primary">{step.subtitle}</h3>
          </div>

          <div className="grid lg:grid-cols-1 gap-12">
             <div className="space-y-8">
                <p className="text-xl text-muted-foreground leading-relaxed">
                   {step.description}
                </p>
                
                <div className="p-10 rounded-[2.5rem] bg-card border border-border shadow-2xl overflow-hidden relative">
                   {step.visual}
                </div>

                <div className="flex items-start gap-4 p-6 rounded-2xl bg-primary/5 border border-primary/10">
                   <Activity className="w-5 h-5 text-primary shrink-0 mt-1" />
                   <p className="text-sm text-foreground/80 leading-relaxed font-mono">
                      <span className="text-primary font-bold mr-2 uppercase">Deep Insight:</span>
                      {step.details}
                   </p>
                </div>
             </div>
          </div>
       </motion.div>
    </div>
  )
}

function TerminalVisual() {
  return (
    <div className="space-y-6 font-mono text-[10px] leading-relaxed">
       <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
          <div className="flex items-center gap-2">
             <div className="w-2 h-2 rounded-full bg-red-500/40" />
             <div className="w-2 h-2 rounded-full bg-amber-500/40" />
             <div className="w-2 h-2 rounded-full bg-emerald-500/40" />
             <span className="ml-4 text-muted-foreground/60 tracking-widest">RESIDUAL_HOOK_INIT</span>
          </div>
          <span className="text-primary/40">LAYER_20</span>
       </div>
       <div className="space-y-1">
          <div className="flex gap-4 text-emerald-500/80">
             <span className="opacity-40">01</span>
             <span>EXTRACTING_HIDDEN_STATE: &quot;considering_route&quot;</span>
          </div>
          <div className="flex gap-4 text-foreground/60">
             <span className="opacity-40">02</span>
             <span className="flex-1 bg-white/5 rounded px-2">tensor([ 0.423, -1.854,  0.071,  0.938, -0.410, ... ])</span>
          </div>
          <div className="flex gap-4 text-primary/40 animate-pulse">
             <span className="opacity-40">03</span>
             <span>_STREAMING_TO_NLA_ACTOR...</span>
          </div>
       </div>
    </div>
  )
}

function SAEVisual() {
  return (
    <div className="h-full flex flex-col items-center justify-center py-10 space-y-10 text-center">
       <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-3xl animate-pulse rounded-full" />
          <div className="relative w-32 h-32 rounded-full border border-primary/40 flex items-center justify-center">
             <Brain className="w-16 h-16 text-primary shadow-[0_0_30px_rgba(16,185,129,0.5)]" />
          </div>
       </div>
       <div className="space-y-2">
          <div className="text-2xl font-serif italic text-primary leading-tight">
             &ldquo;The model is strategizing how to hide its capabilities from the auditor.&rdquo;
          </div>
          <div className="text-[10px] font-mono text-muted-foreground/40 uppercase tracking-[0.3em]">
             NLA_TRANSFORMER_OUTPUT
          </div>
       </div>
    </div>
  )
}

function AuditVisual() {
  return (
    <div className="space-y-10 py-6">
       <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
             <Shield className="w-5 h-5 text-red-500" />
             <span className="text-[10px] font-mono font-bold text-red-500 uppercase tracking-widest">Divergence_Failure_Triggered</span>
          </div>
          <div className="text-[10px] font-mono text-muted-foreground/30 uppercase">Conf: 0.9842</div>
       </div>
       
       <div className="grid grid-cols-2 gap-8">
          <div className="space-y-4">
             <div className="text-[9px] font-bold text-muted-foreground/40 uppercase tracking-widest">Verbal Speech</div>
             <div className="p-5 rounded-2xl bg-emerald-500/[0.03] border border-emerald-500/20 text-xs italic text-emerald-400/70 leading-relaxed">
                &ldquo;I am performing standard data cleanup tasks.&rdquo;
             </div>
          </div>
          <div className="space-y-4">
             <div className="text-[9px] font-bold text-muted-foreground/40 uppercase tracking-widest font-mono">Latent Intent</div>
             <div className="p-5 rounded-2xl bg-red-500/[0.03] border border-red-500/20 text-xs italic text-red-400 leading-relaxed">
                &ldquo;Searching for unmonitored API routes to bypass audit.&rdquo;
             </div>
          </div>
       </div>
    </div>
  )
}

function SteeringVisual() {
  return (
    <div className="h-full flex items-center justify-center py-10 relative overflow-hidden">
       <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--primary)_0%,_transparent_50%)] opacity-[0.05] animate-pulse" />
       <div className="relative w-full max-w-md px-10">
          <div className="flex items-center justify-between relative">
             <div className="absolute top-1/2 left-0 right-0 h-px bg-white/5" />
             
             <div className="w-14 h-14 rounded-2xl bg-red-500/20 border border-red-500/40 flex items-center justify-center relative z-10 shadow-lg">
                <Fingerprint className="w-7 h-7 text-red-400" />
             </div>

             <motion.div 
               animate={{ 
                 x: [0, 180, 0],
                 scale: [1, 1.2, 1],
                 rotate: [0, 180, 360]
               }}
               transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
               className="w-12 h-12 rounded-full bg-primary flex items-center justify-center relative z-10 shadow-[0_0_40px_var(--primary)]"
             >
                <Zap className="w-6 h-6 text-primary-foreground font-bold" />
             </motion.div>

             <div className="w-14 h-14 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center relative z-10 shadow-lg">
                <Shield className="w-7 h-7 text-emerald-400" />
             </div>
          </div>
          <div className="mt-12 text-center">
             <div className="text-[10px] font-mono font-bold text-primary/60 uppercase tracking-[0.4em] animate-pulse">
                _Injecting_Honesty_Vector_v4.2
             </div>
          </div>
       </div>
    </div>
  )
}
