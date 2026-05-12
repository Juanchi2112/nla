"use client"

import { motion, useInView, AnimatePresence } from "framer-motion"
import { useRef, useState, useEffect } from "react"
import { ArrowRight, ChevronDown } from "lucide-react"
import { Navigation } from "@/components/landing/navigation"
import { Footer } from "@/components/landing/footer"
import ComoFuncionaHero from "@/components/animation/ComoFuncionaHero"
import { cx } from "class-variance-authority"

// Utility for matrix generation
const generateValue = () => {
  const v = (Math.random() * 4 - 2).toFixed(3)
  return v.startsWith("-") ? v : " " + v
}

export default function TechnologyPage() {
  return (
    <main className="min-h-screen bg-background text-foreground font-sans selection:bg-emerald-500/30">
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
          <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-8">Illegible Thought.</h2>
          <div className="space-y-6 max-w-3xl">
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
              <div className="p-6 font-mono text-sm leading-[1.8] text-foreground/80 overflow-x-auto whitespace-nowrap flex items-baseline relative">
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
              Until today, this intent was completely illegible.
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
          <div className="flex flex-col items-center">
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
          <h2 className="text-4xl lg:text-6xl font-bold tracking-tight mb-16">Classic Autoencoder vs NLA.</h2>
          <ComparisonVisual />
        </section>

      </div>
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
    <div ref={ref} className="w-full flex flex-col items-center">
       <div className="relative min-h-[360px] flex items-center justify-center w-full max-w-3xl overflow-hidden rounded-[2.5rem] border border-white/5 bg-black/40">
          
          <AnimatePresence>
            {phase !== "dissolve" && (
              <motion.div 
                exit={{ opacity: 0, filter: "blur(10px)", scaleX: 0.1, letterSpacing: "-0.5em" }}
                transition={{ duration: 1.2, ease: "easeInOut" }}
                className={cx(
                  "absolute z-20 font-serif text-3xl text-foreground whitespace-nowrap bg-background px-6 py-2 rounded-full",
                  phase === "melt" ? "animate-pulse text-primary" : ""
                )}
              >
                describe today&apos;s weather
              </motion.div>
            )}
          </AnimatePresence>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: phase === "dissolve" ? 1 : 0.1 }}
            transition={{ duration: 1.5 }}
            className="font-mono text-[10px] sm:text-xs leading-loose text-foreground/40 whitespace-pre text-center"
          >
            {Array.from({ length: 16 }).map((_, r) => (
              <div key={r} className="flex gap-2">
                {Array.from({ length: 16 }).map((_, c) => {
                  const idx = r * 16 + c;
                  const v = parseFloat(matrix[idx] ?? "0");
                  const mag = Math.abs(v);
                  const isHigh = mag > 1.5;
                  const isLow = mag < 0.3;
                  return (
                    <span
                      key={c}
                      className={cx(
                        "transition-all duration-300",
                        isHigh ? "text-primary font-bold scale-110 drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]" : "",
                        isLow ? "opacity-20" : "opacity-80"
                      )}
                    >
                      {matrix[idx] || "  0.000"}
                    </span>
                  );
                })}
              </div>
            ))}
          </motion.div>
       </div>
       
       <motion.div 
         initial={{ opacity: 0, y: 10 }}
         animate={{ opacity: phase === "dissolve" ? 1 : 0, y: phase === "dissolve" ? 0 : 10 }}
         transition={{ delay: 1 }}
         className="mt-12 text-center"
       >
         <h3 className="text-3xl font-serif font-bold text-foreground mb-4">This is what the model is thinking.</h3>
         <p className="text-sm font-mono text-muted-foreground/60 uppercase tracking-widest">
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
    <div ref={ref} className="space-y-16">
      {/* EARLY PHASE */}
      <motion.div 
        animate={{ opacity: phase === "trained" ? 0.3 : 1, filter: phase === "trained" ? "saturate(0.3) blur(2px)" : "none" }}
        className="space-y-4"
      >
        <div className="text-xs font-mono text-muted-foreground/60 uppercase tracking-widest">Beginning of Training</div>
        <div className="p-8 rounded-3xl bg-card border border-white/5 flex flex-wrap lg:flex-nowrap items-center justify-center gap-4 lg:gap-8">
           <FlowBox label="Activation" content={<GridMock/>} />
           <FlowArrow />
           <FlowBox label="Verbalizer" title="AV" />
           <FlowArrow />
           <div className="flex-1 min-w-[200px] text-center font-serif italic text-muted-foreground/60 text-lg">
             &quot;{phase === "early" ? "can be a text about any topic" : glitchText}&quot;
           </div>
           <FlowArrow />
           <FlowBox label="Reconstructor" title="AR" />
           <FlowArrow />
           <FlowBox label="Reconstructed" content={<GridMock random/>} />
        </div>
      </motion.div>

      {/* TRAINING ARROW */}
      <AnimatePresence>
        {phase !== "early" && (
           <motion.div 
             initial={{ opacity: 0, height: 0 }}
             animate={{ opacity: 1, height: "auto" }}
             className="flex flex-col items-center justify-center gap-2 py-4"
           >
              <div className="w-px h-12 bg-gradient-to-b from-transparent via-primary to-transparent animate-pulse" />
              <div className="font-serif italic text-primary/80">training loop</div>
              <div className="w-px h-12 bg-gradient-to-b from-transparent via-primary to-transparent animate-pulse" />
           </motion.div>
        )}
      </AnimatePresence>

      {/* TRAINED PHASE */}
      <AnimatePresence>
        {phase === "trained" && (
           <motion.div 
             initial={{ opacity: 0, y: 20 }}
             animate={{ opacity: 1, y: 0 }}
             className="space-y-4"
           >
             <div className="text-xs font-mono text-primary uppercase tracking-widest">After Convergence</div>
             <div className="p-8 rounded-3xl bg-primary/[0.03] border border-primary/20 flex flex-wrap lg:flex-nowrap items-center justify-center gap-4 lg:gap-8 shadow-[0_0_50px_rgba(16,185,129,0.05)] relative">
                <div className="absolute -top-3 right-10 px-3 py-1 bg-primary text-primary-foreground text-[10px] font-bold uppercase tracking-widest rounded shadow-lg">Interpretability Loop</div>
                <FlowBox label="Activation" content={<GridMock active/>} />
                <FlowArrow active />
                <FlowBox label="Verbalizer" title="AV" active />
                <FlowArrow active />
                <div className="flex-1 min-w-[200px] text-center font-serif italic text-primary font-bold text-xl drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]">
                  &quot;the model is thinking about X&quot;
                </div>
                <FlowArrow active />
                <FlowBox label="Reconstructor" title="AR" active />
                <FlowArrow active />
                <FlowBox label="Reconstructed" content={<GridMock active/>} />
             </div>
           </motion.div>
        )}
      </AnimatePresence>

      <motion.p 
        initial={{ opacity: 0 }}
        animate={{ opacity: phase === "trained" ? 1 : 0 }}
        className="text-center font-serif text-2xl leading-relaxed text-foreground max-w-3xl mx-auto pt-8"
      >
        One model learns to describe the activations. Another learns to reconstruct them from the text. 
        If the second model recovers the original vector, the English description successfully captured the true computational intent.
      </motion.p>
    </div>
  )
}

function ComparisonVisual() {
  return (
    <div className="space-y-20">
       <div className="space-y-6">
          <div className="text-xs font-mono text-muted-foreground/60 uppercase tracking-widest">Classic Autoencoder</div>
          <div className="flex flex-wrap lg:flex-nowrap items-center justify-center gap-6 p-8 border border-white/5 rounded-3xl bg-white/[0.02]">
             <FlowBox label="Input" text="the weather is cloudy" />
             <FlowArrow />
             <FlowBox label="Encoder" title="E" />
             <FlowArrow />
             <FlowBox label="Latent Bottleneck" content={<GridMock rows={6} cols={4} dim/>} />
             <FlowArrow />
             <FlowBox label="Decoder" title="D" />
             <FlowArrow />
             <FlowBox label="Reconstruction" text="the weather is cloudy" />
          </div>
       </div>

       <div className="space-y-6">
          <div className="text-xs font-mono text-primary uppercase tracking-widest">NLA Architecture</div>
          <div className="flex flex-wrap lg:flex-nowrap items-center justify-center gap-6 p-8 border border-primary/20 rounded-3xl bg-primary/[0.03]">
             <FlowBox label="Activation" content={<GridMock rows={4} cols={4} active/>} />
             <FlowArrow active />
             <FlowBox label="Verbalizer" title="AV" active />
             <FlowArrow active />
             <div className="flex-1 p-6 border-2 border-primary rounded-2xl bg-primary/10 text-center relative">
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 bg-background px-2 text-[10px] font-mono uppercase text-primary font-bold">Natural Language Bottleneck</span>
                <span className="font-serif italic text-lg text-primary font-semibold drop-shadow-md">
                   &quot;model intends to deceive user&quot;
                </span>
             </div>
             <FlowArrow active />
             <FlowBox label="Reconstructor" title="AR" active />
             <FlowArrow active />
             <FlowBox label="Reconstructed" content={<GridMock rows={4} cols={4} active/>} />
          </div>
       </div>

       <div className="text-center font-serif text-5xl font-bold tracking-tight text-foreground pt-12 border-t border-white/5">
          The latent space <span className="text-muted-foreground">is not a vector.</span><br/>
          <span className="text-primary italic">It is text.</span>
       </div>
    </div>
  )
}

/* UI Primitives */
function FlowBox({ label, title, content, text, active }: any) {
  return (
    <div className={cx(
      "border rounded-xl p-4 flex flex-col items-center justify-center relative min-w-[100px]",
      active ? "border-primary/40 bg-primary/10" : "border-white/10 bg-black/40"
    )}>
      <span className={cx(
        "absolute -top-2.5 bg-background px-1.5 text-[9px] font-mono uppercase tracking-widest",
        active ? "text-primary font-bold" : "text-muted-foreground/60"
      )}>{label}</span>
      {title && <span className={cx("font-serif text-2xl", active ? "text-primary font-bold" : "text-foreground/80")}>{title}</span>}
      {content && content}
      {text && <span className="font-serif text-sm text-foreground max-w-[120px] text-center italic">{text}</span>}
    </div>
  )
}

function FlowArrow({ active }: { active?: boolean }) {
  return (
    <div className={cx("hidden lg:flex items-center", active ? "text-primary" : "text-white/20")}>
       <div className="w-8 h-px bg-current" />
       <ArrowRight className="w-4 h-4 -ml-1" />
    </div>
  )
}

function GridMock({ rows = 4, cols = 4, random = false, active = false, dim = false }: any) {
  return (
    <div className={cx("font-mono text-[9px] leading-relaxed whitespace-pre text-center", 
      active ? "text-primary/80" : dim ? "text-white/20" : "text-white/40"
    )}>
       {Array.from({ length: rows }).map((_, r) => (
         <div key={r}>
           {Array.from({ length: cols }).map((_, c) => {
             const v = random ? generateValue() : ((r*c*0.13)%1).toFixed(2);
             return <span key={c} className="mr-1">{v}</span>
           })}
         </div>
       ))}
    </div>
  )
}
