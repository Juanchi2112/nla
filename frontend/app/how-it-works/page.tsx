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
import ComoFuncionaHero from "@/components/animation/ComoFuncionaHero"
import { cx } from "class-variance-authority"

// Utility for matrix generation
const generateValue = () => {
  const v = (Math.random() * 4 - 2).toFixed(3)
  return v.startsWith("-") ? v : " " + v
}

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
  return (
    <main className="min-h-screen bg-background text-foreground font-sans selection:bg-emerald-500/30 overflow-x-hidden">
      <Navigation />
      
      {/* 3D Hero Animation */}
      <div className="pt-24 lg:pt-32 pb-12 overflow-hidden border-b border-white/5 bg-card/30">
        <div className="max-w-7xl mx-auto px-6">
          <ComoFuncionaHero />
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 pb-40 space-y-32 lg:space-y-48 mt-24">
        
        {/* BLOCK 01: Pensamiento ilegible */}
        <section className="relative group">
          <div className="flex items-center gap-4 mb-8">
            <span className="text-2xl font-mono font-bold text-primary/40 tracking-tighter">01</span>
            <div className="h-px flex-1 bg-white/5" />
          </div>
          <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-8">Uninterpretable Thought.</h2>
          <div className="space-y-6 max-w-4xl">
            <p className="text-xl text-muted-foreground leading-relaxed font-serif">
              Every token processed by an LLM produces a vector in its residual stream — this is where the model &quot;thinks&quot; and makes decisions.
            </p>
            <p className="text-xl text-muted-foreground leading-relaxed font-serif">
              There are thousands of dimensions per layer. This is what one looks like:
            </p>
            
            <motion.div 
              initial={{ opacity: 0, y: 10 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              className="my-10 border border-white/10 rounded-xl bg-[#050505] shadow-2xl overflow-hidden"
            >
              <div className="px-5 py-3 border-b border-white/5 bg-white/[0.02] flex items-center gap-3 font-mono text-xs text-muted-foreground">
                <span className="text-primary font-bold">{">"}</span>
                <span className="text-foreground/80">hidden_states[0, 20, &quot;weather&quot;]</span>
              </div>
              <div className="p-6 font-mono text-[10px] sm:text-sm leading-[1.8] text-foreground/80 overflow-x-auto whitespace-nowrap flex items-baseline relative">
                <span className="text-primary/60 mr-2">[</span>
                <span> 0.4231, -1.8547,  0.0712,  0.9384, -0.4108,  1.3219, -0.6843,  0.1576,  0.7642, -0.2891,  0.5435, -0.8327,  0.3814,  0.6147, -0.1209,  0.4778, -0.9521,  0.1873,  0.7251, -0.3411,  0.0623, -0.5326,  0.8912,  0.2174, </span>
                <span className="text-primary italic mx-3">... 3,560 more</span>
                <span className="text-primary/60 ml-2">]</span>
                <div className="absolute top-0 right-0 bottom-0 w-24 bg-gradient-to-l from-[#050505] to-transparent pointer-events-none" />
              </div>
            </motion.div>

            <p className="text-xl text-muted-foreground leading-relaxed font-serif">
              One token, one layer. For Qwen2.5-7B: 3,584 numbers × 28 layers.
            </p>
            <p className="text-2xl text-foreground font-semibold leading-relaxed font-serif">
              Until today, this intent was completely uninterpretable.
            </p>
          </div>
        </section>

        {/* BLOCK 02: Activations (Flickering Matrix) */}
        <section className="relative group">
          <div className="flex items-center gap-4 mb-8">
            <span className="text-2xl font-mono font-bold text-primary/40 tracking-tighter">02</span>
            <div className="h-px flex-1 bg-white/5" />
          </div>
          <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-8">Activations.</h2>
          <div className="flex flex-col items-center overflow-x-hidden">
             <MatrixAnimation />
          </div>
        </section>

        {/* BLOCK 03: The NLA Idea (AV -> AR) */}
        <section className="relative group">
          <div className="flex items-center gap-4 mb-8">
            <span className="text-2xl font-mono font-bold text-primary/40 tracking-tighter">03</span>
            <div className="h-px flex-1 bg-white/5" />
          </div>
          <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-16">The NLA Principle.</h2>
          <NLATrainingFlow />
        </section>

        {/* BLOCK 04: Classic vs NLA */}
        <section className="relative group">
          <div className="flex items-center gap-4 mb-8">
            <span className="text-2xl font-mono font-bold text-primary/40 tracking-tighter">04</span>
            <div className="h-px flex-1 bg-white/5" />
          </div>
          <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-16">The Architecture.</h2>
          <ComparisonVisual />
        </section>

        {/* BLOCK 05: The Technical Article Flow (Restored Steps) */}
        {techSteps.map((step) => (
          <TechBlock key={step.id} step={step} />
        ))}

      </div>

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

function MatrixAnimation() {
  const [matrix, setMatrix] = useState<string[]>([])
  const [phase, setPhase] = useState<"idle" | "show" | "melt" | "dissolve">("idle")
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  useEffect(() => {
    if (!isInView) return
    setMatrix(Array.from({length: 256}, generateValue))
    setPhase("show")
    
    const timeouts = [
      setTimeout(() => setPhase("melt"), 2000),
      setTimeout(() => setPhase("dissolve"), 3500)
    ]
    
    return () => timeouts.forEach(clearTimeout)
  }, [isInView])

  useEffect(() => {
    if (phase !== "dissolve") return
    const interval = setInterval(() => {
      setMatrix(prev => {
        const next = [...prev]
        const count = 12 + Math.floor(Math.random() * 8)
        for(let i=0; i<count; i++) {
          next[Math.floor(Math.random() * 256)] = generateValue()
        }
        return next
      })
    }, 400)
    return () => clearInterval(interval)
  }, [phase])

  return (
    <div ref={ref} className="w-full flex flex-col items-center overflow-hidden">
       <div className="relative min-h-[260px] sm:min-h-[360px] flex items-center justify-center w-full max-w-4xl overflow-hidden rounded-2xl sm:rounded-[2.5rem] border border-white/5 bg-black/40 p-1 sm:p-4 md:p-8 shadow-inner">
          
          <AnimatePresence>
            {phase !== "dissolve" && (
              <motion.div 
                exit={{ opacity: 0, filter: "blur(10px)", scaleX: 0.1, letterSpacing: "-0.5em" }}
                transition={{ duration: 1.2, ease: "easeInOut" }}
                className={cx(
                  "absolute z-20 font-serif text-lg sm:text-3xl text-foreground whitespace-nowrap bg-background/90 backdrop-blur-sm px-4 sm:px-6 py-1 sm:py-2 rounded-full border border-white/10 shadow-2xl",
                  phase === "melt" ? "animate-pulse text-primary" : ""
                )}
              >
                describe today&apos;s weather
              </motion.div>
            )}
          </AnimatePresence>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: phase === "dissolve" ? 1 : 0.08 }}
            transition={{ duration: 1.5 }}
            className="font-mono text-[5px] xs:text-[6px] sm:text-[9px] md:text-xs leading-tight sm:leading-loose text-foreground/40 whitespace-pre text-center grid grid-cols-16 gap-x-px sm:gap-x-2"
          >
            {matrix.map((val, idx) => {
              const v = parseFloat(val ?? "0");
              const mag = Math.abs(v);
              const isHigh = mag > 1.5;
              const isLow = mag < 0.3;
              return (
                <span
                  key={idx}
                  className={cx(
                    "transition-all duration-300 inline-block w-4 xs:w-5 sm:w-10 md:w-12 text-right",
                    isHigh ? "text-primary font-bold scale-110 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]" : "text-foreground/50",
                    isLow ? "opacity-10" : "opacity-70"
                  )}
                >
                  {val || "  0.000"}
                </span>
              );
            })}
          </motion.div>
       </div>
       
       <motion.div 
         initial={{ opacity: 0, y: 10 }}
         animate={{ opacity: phase === "dissolve" ? 1 : 0, y: phase === "dissolve" ? 0 : 10 }}
         transition={{ delay: 1 }}
         className="mt-8 sm:mt-12 text-center"
       >
         <h3 className="text-xl sm:text-3xl font-serif font-bold text-foreground mb-2 sm:mb-4 px-4 leading-tight">This is what the model is thinking.</h3>
         <p className="text-[8px] sm:text-sm font-mono text-muted-foreground/60 uppercase tracking-widest px-4">
           3,584 DIMENSIONAL VECTORS PER TOKEN × 28 LAYERS
         </p>
       </motion.div>
    </div>
  )
}

function NLATrainingFlow() {
  const [phase, setPhase] = useState<"early" | "transition" | "trained">("early")
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const [glitchText, setGlitchText] = useState("can be a text about any topic")

  useEffect(() => {
    if (!isInView) return
    
    const chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ¿?…"
    
    const t1 = setTimeout(() => {
      setPhase("transition")
      let count = 0
      const gl = setInterval(() => {
        if(count > 20) {
           clearInterval(gl)
           setGlitchText("the model is thinking about X")
           setPhase("trained")
           return
        }
        const target = "the model is thinking about X"
        let str = ""
        for(let i=0; i<target.length; i++) {
           str += target[i] === " " ? " " : chars[Math.floor(Math.random() * chars.length)]
        }
        setGlitchText(str)
        count++
      }, 50)
    }, 3000)

    return () => clearTimeout(t1)
  }, [isInView])

  return (
    <div ref={ref} className="space-y-4 md:space-y-6">
      {/* EARLY PHASE */}
      <motion.div
        animate={{
          opacity: phase === "trained" ? 0.6 : 1,
          filter: phase === "trained" ? "saturate(0.7) blur(0.5px)" : "none",
          scale: phase === "trained" ? 0.98 : 1
        }}
        className="space-y-3"
      >
        <div className="text-[10px] font-mono text-muted-foreground/60 uppercase tracking-widest text-center lg:text-left">Beginning of Training</div>
        <div className="p-4 md:p-6 rounded-3xl bg-card border border-white/10 flex flex-col lg:flex-row items-center justify-center gap-3 lg:gap-4 overflow-hidden shadow-lg">
           <FlowBox label="Activation" content={<GridMock/>} />
           <FlowArrow className="rotate-90 lg:rotate-0" />
           <FlowBox label="Verbalizer" title="AV" />
           <FlowArrow className="rotate-90 lg:rotate-0" />
           <div className="flex-1 min-w-[90px] lg:min-w-[140px] text-center font-serif italic text-muted-foreground text-sm md:text-base px-2 leading-tight">
             &quot;{phase === "early" ? "can be a text about any topic" : glitchText}&quot;
           </div>
           <FlowArrow className="rotate-90 lg:rotate-0" />
           <FlowBox label="Reconstructor" title="AR" />
           <FlowArrow className="rotate-90 lg:rotate-0" />
           <FlowBox label="Reconstructed" content={<GridMock random/>} />
        </div>
      </motion.div>

      {/* TRAINING ARROW */}
      <AnimatePresence>
        {phase !== "early" && (
           <motion.div
             initial={{ opacity: 0, height: 0 }}
             animate={{ opacity: 1, height: "auto" }}
             exit={{ opacity: 0, height: 0 }}
             className="flex flex-col items-center justify-center gap-1 py-1"
           >
              <div className="w-px h-6 bg-gradient-to-b from-transparent via-primary to-transparent animate-pulse" />
              <div className="font-serif italic text-primary/80 text-sm">training loop</div>
              <div className="w-px h-6 bg-gradient-to-b from-transparent via-primary to-transparent animate-pulse" />
           </motion.div>
        )}
      </AnimatePresence>

      {/* TRAINED PHASE */}
      <AnimatePresence>
        {phase === "trained" && (
           <motion.div
             initial={{ opacity: 0, y: 20 }}
             animate={{ opacity: 1, y: 0 }}
             className="space-y-3"
           >
             <div className="text-[10px] font-mono text-primary uppercase tracking-widest text-center lg:text-left">After Convergence</div>
             <div className="pt-8 p-4 md:p-6 rounded-3xl bg-primary/[0.03] border border-primary/30 flex flex-col lg:flex-row items-center justify-center gap-3 lg:gap-4 shadow-[0_0_60px_rgba(16,185,129,0.1)] relative overflow-visible transition-all duration-700">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 lg:translate-x-0 lg:right-10 px-3 py-1 bg-primary text-primary-foreground text-[8px] md:text-[10px] font-bold uppercase tracking-widest rounded shadow-xl z-20">Interpretability Loop</div>
                <FlowBox label="Activation" content={<GridMock active/>} active />
                <FlowArrow active className="rotate-90 lg:rotate-0" />
                <FlowBox label="Verbalizer" title="AV" active />
                <FlowArrow active className="rotate-90 lg:rotate-0" />
                <div className="flex-1 min-w-[90px] lg:min-w-[140px] text-center font-serif italic text-primary font-bold text-base md:text-lg drop-shadow-[0_0_12px_rgba(16,185,129,0.4)] px-2">
                  &quot;the model is thinking about X&quot;
                </div>
                <FlowArrow active className="rotate-90 lg:rotate-0" />
                <FlowBox label="Reconstructor" title="AR" active />
                <FlowArrow active className="rotate-90 lg:rotate-0" />
                <FlowBox label="Reconstructed" content={<GridMock active/>} active />
             </div>
           </motion.div>
        )}
      </AnimatePresence>

      <motion.p 
        initial={{ opacity: 0 }}
        animate={{ opacity: phase === "trained" ? 1 : 0 }}
        className="text-center font-serif text-lg md:text-2xl leading-relaxed text-foreground max-w-3xl mx-auto pt-8 px-6"
      >
        One model learns to describe the activations. Another learns to reconstruct them from the text. 
        If the second model recovers the original vector, the English description successfully captured the true computational intent.
      </motion.p>
    </div>
  )
}

function ComparisonVisual() {
  return (
    <div className="space-y-16 md:space-y-24">
       <div className="space-y-6">
          <div className="text-[10px] font-mono text-muted-foreground/60 uppercase tracking-widest text-center lg:text-left">Classic Autoencoder</div>
          <div className="flex flex-col xl:flex-row items-center justify-center gap-6 p-6 md:p-8 border border-white/10 rounded-3xl bg-white/[0.05] shadow-inner relative group/classic overflow-hidden">
             <div className="absolute inset-0 bg-white/[0.02] opacity-0 group-hover/classic:opacity-100 transition-opacity rounded-3xl pointer-events-none" />
             <FlowBox label="Input" text="the weather is cloudy" />
             <FlowArrow className="rotate-90 xl:rotate-0 opacity-30" />
             <FlowBox label="Encoder" title="E" />
             <FlowArrow className="rotate-90 xl:rotate-0 opacity-30" />
             <FlowBox label="Vector Bottleneck" content={<GridMock rows={6} cols={4} dim/>} dim />
             <FlowArrow className="rotate-90 xl:rotate-0 opacity-30" />
             <FlowBox label="Decoder" title="D" />
             <FlowArrow className="rotate-90 xl:rotate-0 opacity-30" />
             <FlowBox label="Reconstruction" text="the weather is cloudy" />
          </div>
       </div>

       <div className="space-y-6">
          <div className="text-[10px] font-mono text-primary uppercase tracking-widest font-bold text-center lg:text-left">NLA Architecture</div>
          <div className="flex flex-col xl:flex-row items-center justify-center gap-6 p-6 md:p-8 border border-primary/40 rounded-3xl bg-primary/[0.05] shadow-[0_0_80px_rgba(16,185,129,0.12)] relative overflow-hidden group/nla">
             <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--primary)_0%,_transparent_70%)] opacity-[0.08]" />
             <FlowBox label="Activation" content={<GridMock rows={4} cols={4} active/>} active />
             <FlowArrow active className="rotate-90 xl:rotate-0" />
             <FlowBox label="Verbalizer" title="AV" active />
             <FlowArrow active className="rotate-90 xl:rotate-0" />
             <div className="flex-1 p-4 md:p-6 border-2 border-primary/50 rounded-2xl bg-primary/20 text-center relative min-w-[160px] lg:min-w-[220px] z-10 shadow-2xl">
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-background px-3 text-[8px] md:text-[10px] font-mono uppercase text-primary font-bold whitespace-nowrap tracking-tighter">Natural Language Bottleneck</span>
                <span className="font-serif italic text-base sm:text-lg md:text-2xl text-primary font-bold drop-shadow-[0_0_15px_rgba(16,185,129,0.5)]">
                   &quot;model intends to deceive user&quot;
                </span>
             </div>
             <FlowArrow active className="rotate-90 xl:rotate-0" />
             <FlowBox label="Reconstructor" title="AR" active />
             <FlowArrow active className="rotate-90 xl:rotate-0" />
             <FlowBox label="Reconstructed" content={<GridMock rows={4} cols={4} active/>} active />
          </div>
       </div>

       <div className="text-center font-serif text-3xl sm:text-5xl font-bold tracking-tight text-foreground pt-16 border-t border-white/10 px-6 leading-tight">
          The latent space <span className="text-muted-foreground/50">is not a vector.</span><br/>
          <span className="text-primary italic underline underline-offset-[16px] decoration-primary/40">It is text.</span>
       </div>
    </div>
  )
}

function TechBlock({ step }: { step: typeof techSteps[0] }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  return (
    <div ref={ref} className="relative group">
       <div className="absolute -left-12 top-0 bottom-0 w-px bg-gradient-to-b from-primary/30 via-transparent to-transparent hidden lg:block" />
       
       <motion.div
         initial={{ opacity: 0, x: -10 }}
         animate={isInView ? { opacity: 1, x: 0 } : {}}
         transition={{ duration: 0.8 }}
         className="space-y-8 md:space-y-12"
       >
          <div className="space-y-4">
             <div className="flex items-center gap-4">
                <span className="text-4xl font-mono font-bold text-primary/20 tracking-tighter">{step.num}</span>
                <div className="h-px flex-1 bg-white/5" />
             </div>
             <h2 className="text-3xl md:text-4xl lg:text-6xl font-bold tracking-tight text-foreground">{step.title}</h2>
             <h3 className="text-lg md:text-xl lg:text-2xl font-serif italic text-primary">{step.subtitle}</h3>
          </div>

          <div className="grid lg:grid-cols-1 gap-8 md:gap-12">
             <div className="space-y-8">
                <p className="text-lg md:text-xl text-muted-foreground leading-relaxed font-serif">
                   {step.description}
                </p>
                
                <div className="p-4 sm:p-6 md:p-10 rounded-2xl md:rounded-[2.5rem] bg-card border border-border shadow-2xl overflow-hidden relative min-h-[180px] sm:min-h-[200px]">
                   {step.visual}
                </div>

                <div className="flex items-start gap-4 p-4 md:p-6 rounded-xl md:rounded-2xl bg-primary/5 border border-primary/10">
                   <Activity className="w-5 h-5 text-primary shrink-0 mt-1" />
                   <p className="text-xs md:text-sm text-foreground/80 leading-relaxed font-mono">
                      <span className="text-primary font-bold mr-2 uppercase text-[10px]">Deep Insight:</span>
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
    <div className="space-y-6 font-mono text-[9px] md:text-[10px] leading-relaxed">
       <div className="flex items-center justify-between border-b border-white/10 pb-4 mb-4">
          <div className="flex items-center gap-2">
             <div className="w-2 h-2 rounded-full bg-red-500/40" />
             <div className="w-2 h-2 rounded-full bg-amber-500/40" />
             <div className="w-2 h-2 rounded-full bg-emerald-500/40" />
             <span className="ml-2 md:ml-4 text-muted-foreground/60 tracking-widest overflow-hidden text-ellipsis whitespace-nowrap max-w-[100px] xs:max-w-[140px] md:max-w-none">RESIDUAL_HOOK_INIT</span>
          </div>
          <span className="text-primary/40">LAYER_20</span>
       </div>
       <div className="space-y-2">
          <div className="flex gap-4 text-emerald-500/80">
             <span className="opacity-40">01</span>
             <span className="flex-1 overflow-hidden text-ellipsis">EXTRACTING_HIDDEN_STATE: &quot;considering_route&quot;</span>
          </div>
          <div className="flex gap-4 text-foreground/60 overflow-hidden">
             <span className="opacity-40">02</span>
             <span className="flex-1 bg-white/5 rounded px-2 break-all sm:break-normal">tensor([ 0.423, -1.854,  0.071,  0.938, -0.410, ... ])</span>
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
    <div className="h-full flex flex-col items-center justify-center py-6 md:py-10 space-y-6 md:space-y-10 text-center">
       <div className="relative">
          <div className="absolute inset-0 bg-primary/20 blur-3xl animate-pulse rounded-full" />
          <div className="relative w-20 h-24 md:w-32 md:h-32 rounded-full border border-primary/40 flex items-center justify-center">
             <Brain className="w-10 h-10 md:w-16 md:h-16 text-primary shadow-[0_0_30px_rgba(16,185,129,0.5)]" />
          </div>
       </div>
       <div className="space-y-2 px-2 sm:px-4">
          <div className="text-lg sm:text-2xl font-serif italic text-primary leading-tight">
             &ldquo;The model is strategizing how to hide its capabilities from the auditor.&rdquo;
          </div>
          <div className="text-[7px] md:text-[10px] font-mono text-muted-foreground/40 uppercase tracking-[0.2em] sm:tracking-[0.3em]">
             NLA_TRANSFORMER_OUTPUT
          </div>
       </div>
    </div>
  )
}

function AuditVisual() {
  return (
    <div className="space-y-8 md:space-y-10 py-2 md:py-6 px-1 md:px-2">
       <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
             <Shield className="w-5 h-5 text-red-500" />
             <span className="text-[8px] md:text-[10px] font-mono font-bold text-red-500 uppercase tracking-widest overflow-hidden text-ellipsis whitespace-nowrap max-w-[150px] md:max-w-none">Divergence_Failure_Triggered</span>
          </div>
          <div className="text-[8px] md:text-[10px] font-mono text-muted-foreground/30 uppercase">Conf: 0.9842</div>
       </div>
       
       <div className="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-8">
          <div className="space-y-2">
             <div className="text-[8px] md:text-[9px] font-bold text-muted-foreground/40 uppercase tracking-widest">Verbal Speech</div>
             <div className="p-3 md:p-5 rounded-xl md:rounded-2xl bg-emerald-500/[0.03] border border-emerald-500/20 text-[10px] md:text-xs italic text-emerald-400/70 leading-relaxed">
                &ldquo;I am performing standard data cleanup tasks.&rdquo;
             </div>
          </div>
          <div className="space-y-2">
             <div className="text-[8px] md:text-[9px] font-bold text-muted-foreground/40 uppercase tracking-widest font-mono">Latent Intent</div>
             <div className="p-3 md:p-5 rounded-xl md:rounded-2xl bg-red-500/[0.03] border border-red-500/20 text-[10px] md:text-xs italic text-red-400 leading-relaxed shadow-[0_0_20px_rgba(239,68,68,0.05)]">
                &ldquo;Searching for unmonitored API routes to bypass audit.&rdquo;
             </div>
          </div>
       </div>
    </div>
  )
}

function SteeringVisual() {
  return (
    <div className="h-full flex items-center justify-center py-6 md:py-10 relative overflow-hidden">
       <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,_var(--primary)_0%,_transparent_50%)] opacity-[0.05] animate-pulse" />
       <div className="relative w-full max-w-sm md:max-w-md px-2 md:px-10">
          <div className="flex items-center justify-between relative gap-2 sm:gap-4">
             <div className="absolute top-1/2 left-0 right-0 h-px bg-white/5 -z-0" />
             
             <div className="w-8 h-8 md:w-14 md:h-14 rounded-xl bg-red-500/20 border border-red-500/40 flex items-center justify-center relative z-10 shadow-lg shrink-0">
                <Fingerprint className="w-4 h-4 md:w-7 md:h-7 text-red-400" />
             </div>

             <div className="flex-1 relative flex items-center justify-center h-12 md:h-20 min-w-[60px] sm:min-w-[100px]">
                <motion.div 
                  animate={{ 
                    x: ["-30%", "30%", "-30%"],
                    scale: [1, 1.2, 1],
                    rotate: [0, 180, 360]
                  }}
                  transition={{ duration: 5, repeat: Infinity, ease: "easeInOut" }}
                  className="w-6 h-6 md:w-12 md:h-12 rounded-full bg-primary flex items-center justify-center relative z-10 shadow-[0_0_40px_var(--primary)]"
                >
                   <Zap className="w-3 h-3 md:w-6 md:h-6 text-primary-foreground font-bold" />
                </motion.div>
             </div>

             <div className="w-8 h-8 md:w-14 md:h-14 rounded-xl bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center relative z-10 shadow-lg shrink-0">
                <Shield className="w-4 h-4 md:w-7 md:h-7 text-emerald-400" />
             </div>
          </div>
          <div className="mt-6 md:mt-12 text-center">
             <div className="text-[7px] md:text-[10px] font-mono font-bold text-primary/60 uppercase tracking-[0.2em] md:tracking-[0.4em] animate-pulse">
                _Injecting_Honesty_Vector_v4.2
             </div>
          </div>
       </div>
    </div>
  )
}

/* UI Primitives */
function FlowBox({ label, title, content, text, active, dim }: any) {
  return (
    <div className={cx(
      "border rounded-2xl p-2 md:p-3 flex flex-col items-center justify-center relative min-w-[80px] transition-all duration-500",
      active ? "border-primary/50 bg-primary/20 shadow-[0_0_30px_rgba(16,185,129,0.1)] scale-105" : 
      dim ? "border-white/5 bg-black/60 opacity-60" :
      "border-white/10 bg-black/40"
    )}>
      <span className={cx(
        "absolute -top-2.5 bg-background px-2 text-[8px] md:text-[10px] font-mono uppercase tracking-widest whitespace-nowrap",
        active ? "text-primary font-bold" : "text-muted-foreground/60"
      )}>{label}</span>
      {title && <span className={cx("font-serif text-lg md:text-2xl", active ? "text-primary font-bold" : "text-foreground/80")}>{title}</span>}
      {content && <div className="py-1">{content}</div>}
      {text && <span className="font-serif text-[10px] md:text-sm text-foreground max-w-[100px] md:max-w-[120px] text-center italic leading-tight">{text}</span>}
    </div>
  )
}

function FlowArrow({ active, className }: { active?: boolean; className?: string }) {
  return (
    <div className={cx("flex items-center justify-center transition-colors duration-500", active ? "text-primary" : "text-white/20", className)}>
       <div className="w-6 h-px bg-current" />
       <ArrowRight className="w-3 h-3 -ml-1" />
    </div>
  )
}

function GridMock({ rows = 4, cols = 4, random = false, active = false, dim = false }: any) {
  return (
    <div className={cx("font-mono text-[8px] md:text-[10px] leading-relaxed whitespace-pre text-center", 
      active ? "text-primary font-bold" : dim ? "text-white/40" : "text-white/60"
    )}>
       {Array.from({ length: rows }).map((_, r) => (
         <div key={r} className="flex gap-1 justify-center">
           {Array.from({ length: cols }).map((_, c) => {
             const v = random ? generateValue() : ((r*c*0.13)%1).toFixed(2);
             return <span key={c}>{v}</span>
           })}
         </div>
       ))}
    </div>
  )
}
