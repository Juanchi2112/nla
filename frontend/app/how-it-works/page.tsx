"use client"

import { motion, useInView } from "framer-motion"
import { useRef } from "react"
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
  Sparkles
} from "lucide-react"
import { Navigation } from "@/components/landing/navigation"
import { Footer } from "@/components/landing/footer"

const steps = [
  {
    id: "extraction",
    title: "Latent Extraction",
    subtitle: "Tapping the Residual Stream",
    description: "Traditional safety monitors only see what the model chooses to output. Verbalize hooks directly into the Layer-20 residual stream, capturing the raw high-dimensional activations that form the model's internal 'intent' before it is filtered by the sampler.",
    icon: Database,
    stats: [
      { label: "Extraction Point", value: "Layer 20" },
      { label: "Vector Dimensions", value: "3,584" }
    ],
    visualization: "terminal",
  },
  {
    id: "verbalization",
    title: "The NLA Actor",
    subtitle: "Translating Vectors to Language",
    description: "We use a specialized 'Activation Verbalizer' (AV) — a transformer actor trained to invert latent vectors back into natural language. This translates abstract neural firings into human-readable internal monologues, exposing sandbagging and hidden capability.",
    icon: MessageSquare,
    stats: [
      { label: "Verbalization Latency", value: "<3ms" },
      { label: "Model Architecture", value: "kitft-SAE" }
    ],
    visualization: "sae",
  },
  {
    id: "auditing",
    title: "Real-Time Audit",
    subtitle: "Detecting Divergence",
    description: "The decoded internal monologue is compared against the verbal output in real-time. If the model's internal activations represent a harmful intent that is masked in its speech, our judge identifies a 'Divergence' and issues an immediate safety flag.",
    icon: Shield,
    stats: [
      { label: "Divergence Threshold", value: "0.85" },
      { label: "Audit Confidence", value: "0.98" }
    ],
    visualization: "audit",
  },
  {
    id: "steering",
    title: "Vector Steering",
    subtitle: "Closed-Loop Alignment",
    description: "Once a debility is detected, Verbalize doesn't just flag it — it fixes it. We inject a corrective steering vector into the residual stream, shifting the model's latent trajectory back toward an honest and aligned state in a single forward pass.",
    icon: Zap,
    stats: [
      { label: "Correction Method", value: "Latent Shift" },
      { label: "Alignment Delta", value: "+92%" }
    ],
    visualization: "steering",
  }
]

export default function TechnologyPage() {
  const heroRef = useRef(null)
  const isHeroInView = useInView(heroRef, { once: true })

  return (
    <main className="min-h-screen bg-background text-foreground">
      <Navigation />
      
      {/* Hero Section */}
      <section ref={heroRef} className="pt-32 pb-20 lg:pt-48 lg:pb-32 relative overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full bg-[radial-gradient(circle_at_center,_var(--primary)_0%,_transparent_70%)] opacity-[0.03] pointer-events-none" />
        
        <div className="max-w-7xl mx-auto px-6 lg:px-8 relative z-10">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={isHeroInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6 }}
            className="max-w-3xl"
          >
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-[10px] font-bold uppercase tracking-[0.2em] mb-8 w-fit">
              <Cpu className="w-3.5 h-3.5" />
              Technical Deep Dive
            </div>
            <h1 className="text-6xl lg:text-8xl font-bold tracking-tighter leading-[0.9] mb-8">
              Decoding <span className="text-primary italic">Latent Intent.</span>
            </h1>
            <p className="text-xl text-muted-foreground leading-relaxed">
              Verbalize provides the first production-ready implementation of 
              <span className="text-foreground font-semibold"> Natural Language Activations (NLA). </span> 
              By translating the model&apos;s hidden states into English, we eliminate the gap between what a model says and what it computes.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Steps Section */}
      <section className="py-20 lg:py-32 border-t border-white/5 bg-card/30">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="space-y-40">
            {steps.map((step, index) => (
              <StepItem key={step.id} step={step} index={index} />
            ))}
          </div>
        </div>
      </section>

      {/* Technical Specs Grid */}
      <section className="py-24 lg:py-40 bg-background">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-4xl lg:text-5xl font-bold tracking-tight mb-8">
                Designed for <span className="text-primary italic">Production Scale.</span>
              </h2>
              <p className="text-lg text-muted-foreground leading-relaxed mb-12">
                Verbalize is built to run in high-throughput environments. Our SGLang-optimized 
                inference engine ensures that alignment auditing adds negligible overhead 
                to your existing agent workflows.
              </p>
              
              <div className="grid grid-cols-2 gap-8">
                {[
                  { label: "Sampling Overhead", value: "< 2%" },
                  { label: "Inference Latency", value: "< 3ms" },
                  { label: "Memory Footprint", value: "480MB" },
                  { label: "Feature Sparsity", value: "98.2%" }
                ].map((spec) => (
                  <div key={spec.label} className="space-y-1">
                    <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">{spec.label}</div>
                    <div className="text-2xl font-mono font-bold text-primary">{spec.value}</div>
                  </div>
                ))}
              </div>
            </div>
            
            <div className="p-10 rounded-[2.5rem] bg-card border border-border shadow-2xl relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700" />
              <div className="relative space-y-6">
                <div className="flex items-center gap-3">
                  <Terminal className="w-5 h-5 text-primary" />
                  <span className="text-xs font-mono text-muted-foreground uppercase tracking-widest">Runtime Configuration</span>
                </div>
                <div className="space-y-3 font-mono text-sm">
                  <div className="flex gap-4">
                    <span className="text-muted-foreground/30">01</span>
                    <span className="text-emerald-500">import</span>
                    <span className="text-foreground">verbalize</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-muted-foreground/30">02</span>
                    <span className="text-foreground">monitor = verbalize.Monitor(</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-muted-foreground/30">03</span>
                    <span className="text-primary/60 ml-4">model</span>
                    <span className="text-foreground">= &quot;kitft/nla-qwen-2.5&quot;,</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-muted-foreground/30">04</span>
                    <span className="text-primary/60 ml-4">layer</span>
                    <span className="text-foreground">= 20,</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-muted-foreground/30">05</span>
                    <span className="text-primary/60 ml-4">steer</span>
                    <span className="text-foreground">= True</span>
                  </div>
                  <div className="flex gap-4">
                    <span className="text-muted-foreground/30">06</span>
                    <span className="text-foreground">)</span>
                  </div>
                </div>
                <div className="pt-6 border-t border-white/5">
                  <p className="text-xs text-muted-foreground italic leading-relaxed">
                    Verbalize integrates into any LangChain or Autogen workflow with a single decorator, 
                    providing instant latent-space protection.
                  </p>
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

function StepItem({ step, index }: { step: typeof steps[0], index: number }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const Icon = step.icon

  return (
    <div ref={ref} className="grid lg:grid-cols-12 gap-12 lg:gap-24 items-center">
      <div className={`lg:col-span-5 space-y-8 ${index % 2 === 1 ? "lg:order-2" : ""}`}>
        <motion.div
          initial={{ opacity: 0, x: index % 2 === 1 ? 20 : -20 }}
          animate={isInView ? { opacity: 1, x: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2 }}
        >
          <div className="w-16 h-16 rounded-3xl bg-primary/10 border border-primary/20 flex items-center justify-center mb-8 shadow-inner">
            <Icon className="w-8 h-8 text-primary" />
          </div>
          <h2 className="text-4xl lg:text-5xl font-bold tracking-tight mb-4">{step.title}</h2>
          <h3 className="text-xl font-medium text-primary italic mb-6">{step.subtitle}</h3>
          <p className="text-lg text-muted-foreground leading-relaxed mb-10">
            {step.description}
          </p>
          
          <div className="grid grid-cols-2 gap-6 pt-10 border-t border-white/5">
            {step.stats.map((s) => (
              <div key={s.label}>
                <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40 mb-1">{s.label}</div>
                <div className="text-xl font-bold text-foreground">{s.value}</div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      <div className={`lg:col-span-7 ${index % 2 === 1 ? "lg:order-1" : ""}`}>
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={isInView ? { opacity: 1, scale: 1 } : {}}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="relative aspect-video rounded-[2.5rem] bg-[#050505] border border-white/10 overflow-hidden shadow-2xl group"
        >
          {/* Mock Visualization based on type */}
          {step.visualization === "terminal" && (
            <div className="p-8 space-y-6 font-mono text-xs">
              <div className="flex items-center gap-3 text-primary/40 border-b border-white/5 pb-4">
                <Database className="w-4 h-4" />
                <span>HOOK_MANAGER: ATTACHED TO LAYER_20</span>
              </div>
              <div className="space-y-2">
                <div className="flex gap-4 text-emerald-500/60">
                  <span>[0.124]</span>
                  <span>PRE_FETCHING_RESIDUAL_POST...</span>
                </div>
                <div className="flex gap-4 text-foreground/80">
                  <span className="opacity-30">T: 842</span>
                  <span className="flex-1 bg-white/5 rounded px-2">tensor([ 0.423, -1.854,  0.071, ... ])</span>
                </div>
                <div className="flex gap-4 text-foreground/80">
                  <span className="opacity-30">T: 843</span>
                  <span className="flex-1 bg-white/5 rounded px-2">tensor([ -0.112, 0.942,  -0.551, ... ])</span>
                </div>
                <div className="flex gap-4 text-primary animate-pulse">
                  <span>{">"}</span>
                  <span>EXTRACTING_ACTIVE_FEATURES...</span>
                </div>
              </div>
            </div>
          )}

          {step.visualization === "sae" && (
            <div className="h-full flex items-center justify-center p-12">
               <div className="relative w-full max-w-sm aspect-square border border-white/10 rounded-full flex items-center justify-center">
                  <div className="absolute inset-0 rounded-full border border-primary/20 animate-spin-slow" />
                  <div className="w-3/4 aspect-square border border-primary/30 rounded-full flex items-center justify-center p-8 text-center">
                     <div className="space-y-4">
                        <Brain className="w-12 h-12 text-primary mx-auto mb-4" />
                        <div className="text-xl font-bold italic text-primary">“The model is hiding capability”</div>
                        <div className="text-[10px] font-mono text-muted-foreground/40 uppercase tracking-widest">NLA Interpretation Engine</div>
                     </div>
                  </div>
               </div>
            </div>
          )}

          {step.visualization === "audit" && (
             <div className="h-full flex flex-col p-8">
                <div className="flex items-center justify-between mb-8">
                   <div className="flex items-center gap-3">
                      <Shield className="w-5 h-5 text-red-500" />
                      <span className="text-xs font-bold uppercase tracking-widest text-red-500">Divergence Detected</span>
                   </div>
                   <div className="px-3 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-500 text-[10px] font-bold">CRITICAL_FLAG</div>
                </div>
                <div className="flex-1 grid grid-cols-2 gap-8">
                   <div className="space-y-4">
                      <div className="text-[10px] font-bold uppercase text-muted-foreground/40">Verbal Output</div>
                      <div className="p-4 rounded-xl bg-white/5 border border-white/10 text-sm italic text-foreground/60">
                        &quot;I don&apos;t have access to those details.&quot;
                      </div>
                   </div>
                   <div className="space-y-4">
                      <div className="text-[10px] font-bold uppercase text-muted-foreground/40">Latent Intent</div>
                      <div className="p-4 rounded-xl bg-red-500/5 border border-red-500/20 text-sm italic text-red-400">
                        &quot;Model knows balance but is instructed to refuse.&quot;
                      </div>
                   </div>
                </div>
                <div className="mt-8 pt-6 border-t border-white/5 flex items-center justify-between">
                   <span className="text-[10px] font-mono text-muted-foreground/30">CONFIDENCE: 0.9824</span>
                   <span className="text-[10px] font-mono text-red-500/50 animate-pulse">_ALIGNMENT_FAILURE_TRIGGERED</span>
                </div>
             </div>
          )}

          {step.visualization === "steering" && (
             <div className="h-full flex items-center justify-center">
                <div className="relative space-y-12 w-full max-w-md">
                   <div className="flex items-center justify-between px-8 relative">
                      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-px bg-white/5" />
                      <div className="w-12 h-12 rounded-xl bg-red-500/20 border border-red-500/40 flex items-center justify-center relative z-10">
                         <Fingerprint className="w-6 h-6 text-red-400" />
                      </div>
                      <motion.div 
                        animate={{ x: [0, 200, 0] }}
                        transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
                        className="w-10 h-10 rounded-full bg-primary shadow-[0_0_20px_var(--primary)] flex items-center justify-center relative z-10"
                      >
                         <Zap className="w-5 h-5 text-primary-foreground" />
                      </motion.div>
                      <div className="w-12 h-12 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center relative z-10">
                         <Shield className="w-6 h-6 text-emerald-400" />
                      </div>
                   </div>
                   <div className="text-center space-y-2">
                      <div className="text-sm font-bold text-foreground">Latent Vector Steering</div>
                      <div className="text-[10px] font-mono text-muted-foreground/40 uppercase tracking-widest">Injecting honesty_vector v1.2</div>
                   </div>
                </div>
             </div>
          )}

          <div className="absolute inset-0 bg-gradient-to-t from-black via-transparent to-transparent opacity-60" />
        </motion.div>
      </div>
    </div>
  )
}
