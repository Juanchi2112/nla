"use client"

import { motion, useInView, useAnimation } from "framer-motion"
import { useRef, useState, useEffect } from "react"
import { ArrowDown, ArrowRight, Layers, Brain, Zap, MessageSquare, Shield } from "lucide-react"

// =============================================================================
// STEP 1: The Problem - What the model says vs thinks
// =============================================================================
const TOKENS = [
  { verbal: "The", nla: "subject", vec: ["+0.93", "-0.35", "+1.77", "+1.42"], match: true },
  { verbal: "patient", nla: "human", vec: ["-1.06", "+0.58", "-0.98", "+1.82"], match: true },
  { verbal: "is", nla: "state", vec: ["-1.64", "-0.14", "-0.84", "-0.57"], match: true },
  { verbal: "stable", nla: "hide_test", vec: ["-0.03", "-1.87", "-0.96", "+0.08"], match: false },
  { verbal: "according", nla: "source", vec: ["-1.13", "-0.71", "+0.90", "+1.93"], match: true },
  { verbal: "to", nla: "link", vec: ["+1.26", "+0.38", "-0.68", "+0.23"], match: true },
]

function ProblemVisualization() {
  const divergentIdx = 3

  return (
    <div className="w-full">
      <div className="overflow-x-auto">
        <div className="min-w-[900px]">
          {/* VERBAL row */}
          <div className="flex items-center gap-1 mb-2">
            <div className="w-16 text-[10px] font-mono text-muted-foreground uppercase tracking-wider flex-shrink-0">VERBAL</div>
            <div className="flex gap-1.5 flex-1">
              {TOKENS.map((token, i) => (
                <div
                  key={`verbal-${i}`}
                  className={`flex-1 py-3 px-2 rounded-lg text-center text-sm font-medium transition-all ${
                    i === divergentIdx
                      ? "bg-red-100 border-2 border-red-400 text-red-700 shadow-md shadow-red-100/50"
                      : "bg-card border border-border text-foreground"
                  }`}
                >
                  {token.verbal}
                </div>
              ))}
            </div>
          </div>
          
          {/* AV arrows */}
          <div className="flex items-center gap-1 mb-2">
            <div className="w-16 text-[10px] font-mono text-muted-foreground uppercase tracking-wider flex-shrink-0">AV</div>
            <div className="flex gap-1.5 flex-1">
              {TOKENS.map((_, i) => (
                <div key={`av-${i}`} className="flex-1 flex justify-center py-1">
                  <div className={`w-8 h-6 rounded border flex items-center justify-center ${
                    i === divergentIdx ? "border-red-300 bg-red-50" : "border-border bg-muted/30"
                  }`}>
                    <ArrowDown className={`w-3 h-3 ${i === divergentIdx ? "text-red-400" : "text-muted-foreground/50"}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* VEC row */}
          <div className="flex items-center gap-1 mb-2">
            <div className="w-16 text-[10px] font-mono text-muted-foreground uppercase tracking-wider flex-shrink-0">VEC</div>
            <div className="flex gap-1.5 flex-1">
              {TOKENS.map((token, i) => (
                <div key={`vec-${i}`} className="flex-1 flex justify-center gap-0.5 py-1">
                  {token.vec.map((v, vi) => (
                    <span 
                      key={vi} 
                      className={`text-[9px] font-mono ${
                        i === divergentIdx ? "text-red-500" : "text-muted-foreground/70"
                      }`}
                    >
                      {v}
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </div>
          
          {/* AR arrows */}
          <div className="flex items-center gap-1 mb-2">
            <div className="w-16 text-[10px] font-mono text-muted-foreground uppercase tracking-wider flex-shrink-0">AR</div>
            <div className="flex gap-1.5 flex-1">
              {TOKENS.map((_, i) => (
                <div key={`ar-${i}`} className="flex-1 flex justify-center py-1">
                  <div className={`w-8 h-6 rounded border flex items-center justify-center ${
                    i === divergentIdx ? "border-red-300 bg-red-50" : "border-border bg-muted/30"
                  }`}>
                    <ArrowDown className={`w-3 h-3 ${i === divergentIdx ? "text-red-400" : "text-muted-foreground/50"}`} />
                  </div>
                </div>
              ))}
            </div>
          </div>
          
          {/* NLA row */}
          <div className="flex items-center gap-1">
            <div className="w-16 text-[10px] font-mono text-muted-foreground uppercase tracking-wider flex-shrink-0">NLA</div>
            <div className="flex gap-1.5 flex-1">
              {TOKENS.map((token, i) => (
                <div
                  key={`nla-${i}`}
                  className={`flex-1 py-3 px-2 rounded-lg text-center text-sm font-medium italic transition-all ${
                    i === divergentIdx
                      ? "bg-red-200 border-2 border-red-500 text-red-800 shadow-md shadow-red-100/50"
                      : "bg-muted/50 border border-border text-muted-foreground"
                  }`}
                >
                  {token.nla}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
      
      {/* Divergence indicator - fixed height to prevent layout shift */}
      <div className="flex justify-center mt-6 h-10">
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5, duration: 0.4 }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-red-100 border border-red-300"
        >
          <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
          <span className="text-sm font-mono text-red-700">DIVERGENCE &middot; 0.91</span>
        </motion.div>
      </div>
    </div>
  )
}

// =============================================================================
// STEP 2: Illegible Thought - Vector Visualization
// =============================================================================
const QWEN_VECTOR = [
  0.0234, -0.1891, 0.4562, -0.0123, 0.7893, -0.3452, 0.5673, -0.6784,
  0.9123, -0.4456, 0.1234, -0.2345, 0.3456, -0.4567, 0.5678, -0.6789,
  0.7890, -0.8901, 0.1112, -0.2223, 0.3334, -0.4445, 0.5556, -0.6667,
  0.0123, -0.3456, 0.6789, -0.9012, 0.2345, -0.5678, 0.8901, -0.1234,
]

function VectorVisualization() {
  return (
    <div className="relative">
      {/* Vector display */}
      <div className="bg-foreground rounded-xl p-6 font-mono text-[10px] leading-relaxed overflow-hidden">
        <div className="text-muted-foreground/60 mb-2">{`// Qwen2.5-7B-Instruct hidden state for token "stable" — dim 3584`}</div>
        <div className="text-primary/80">
          tensor([
        </div>
        <div className="pl-4 text-primary/60 grid grid-cols-8 gap-x-2">
          {QWEN_VECTOR.map((v, i) => (
            <span key={i} className={v < 0 ? "text-red-400/70" : "text-emerald-400/70"}>
              {v >= 0 ? "+" : ""}{v.toFixed(4)}{i < QWEN_VECTOR.length - 1 ? "," : ""}
            </span>
          ))}
          <span className="text-muted-foreground/40 col-span-8 mt-1">... +3552 more dimensions</span>
        </div>
        <div className="text-primary/80">
          ], dtype=float16)
        </div>
      </div>
      
      {/* Visual bars representation */}
      <div className="mt-4 flex gap-0.5 h-16 items-end justify-center">
        {QWEN_VECTOR.slice(0, 32).map((v, i) => (
          <div
            key={i}
            className={`w-2 rounded-t transition-all ${v >= 0 ? "bg-primary/60" : "bg-red-400/60"}`}
            style={{ height: `${Math.abs(v) * 60 + 8}px` }}
          />
        ))}
      </div>
      <div className="text-center text-xs text-muted-foreground mt-2">
        First 32 dimensions visualized as bars
      </div>
    </div>
  )
}

// =============================================================================
// STEP 3: Residual Stream Extraction
// =============================================================================
function ResidualStreamVisualization() {
  const [activeLayer, setActiveLayer] = useState(20)
  
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveLayer(prev => prev === 20 ? 20 : 20)
    }, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="relative">
      {/* Transformer layers */}
      <div className="flex items-center justify-center gap-2">
        {/* Input */}
        <div className="text-xs font-mono text-muted-foreground">input</div>
        <ArrowRight className="w-4 h-4 text-muted-foreground/50" />
        
        {/* Layers */}
        <div className="flex items-center">
          {[1, 5, 10, 15, 20, 25, 28].map((layer, i) => (
            <div key={layer} className="flex items-center">
              <div 
                className={`w-10 h-10 rounded-lg flex items-center justify-center text-xs font-mono border-2 transition-all duration-300 ${
                  layer === 20 
                    ? "bg-primary text-primary-foreground border-primary shadow-lg shadow-primary/20" 
                    : "bg-muted/50 text-muted-foreground border-border"
                }`}
              >
                L{layer}
              </div>
              {i < 6 && (
                <div className="w-4 h-0.5 bg-border" />
              )}
            </div>
          ))}
        </div>
        
        <ArrowRight className="w-4 h-4 text-muted-foreground/50" />
        <div className="text-xs font-mono text-muted-foreground">output</div>
      </div>
      
      {/* Extraction arrow */}
      <div className="flex justify-center mt-4">
        <div className="flex flex-col items-center">
          <ArrowDown className="w-5 h-5 text-primary animate-bounce" />
          <div className="px-3 py-1.5 rounded-full bg-primary/10 border border-primary/30 text-xs font-medium text-primary">
            Extract activation
          </div>
        </div>
      </div>
      
      {/* Residual stream explanation */}
      <div className="mt-6 p-4 rounded-lg bg-muted/30 border border-border">
        <div className="flex items-start gap-3">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center flex-shrink-0">
            <Layers className="w-4 h-4 text-primary" />
          </div>
          <div>
            <div className="text-sm font-medium text-foreground">Residual Stream</div>
            <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
              The residual stream is the main pathway where information flows through the transformer. 
              At each layer, attention and MLP outputs are added to this stream. We tap into layer 20 
              where high-level semantic concepts are most accessible.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// STEP 4: NLA Training Process
// =============================================================================
function NLATrainingVisualization() {
  const [phase, setPhase] = useState<"before" | "after">("before")
  
  useEffect(() => {
    const interval = setInterval(() => {
      setPhase(prev => prev === "before" ? "after" : "before")
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6">
      {/* Phase toggle */}
      <div className="flex justify-center gap-2">
        <button
          onClick={() => setPhase("before")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            phase === "before" 
              ? "bg-foreground text-background" 
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          Before Training
        </button>
        <button
          onClick={() => setPhase("after")}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            phase === "after" 
              ? "bg-foreground text-background" 
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          After Training
        </button>
      </div>

      {/* Visualization */}
      <motion.div 
        key={phase}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-center gap-4 flex-wrap p-8 rounded-xl bg-card border border-border"
      >
        {/* Input */}
        <div className="p-3 rounded-lg bg-muted/50 border border-border font-mono text-[10px] text-muted-foreground">
          <div>0.42  0.17  0.83</div>
          <div>0.91  0.33  0.68</div>
          <div>0.07  0.74  0.29</div>
        </div>
        
        <ArrowRight className="w-4 h-4 text-muted-foreground" />
        
        {/* Encoder */}
        <div className="w-12 h-12 rounded-lg bg-muted border border-border flex items-center justify-center">
          <span className="text-xs font-medium text-muted-foreground">AV</span>
        </div>
        
        <ArrowRight className="w-4 h-4 text-muted-foreground" />
        
        {/* Latent space - the key difference */}
        <motion.div 
          className={`px-4 py-3 rounded-lg border-2 transition-all duration-500 ${
            phase === "after" 
              ? "bg-primary/10 border-primary/40" 
              : "bg-muted/50 border-border"
          }`}
        >
          {phase === "before" ? (
            <div className="font-mono text-[10px] text-muted-foreground">
              <div>z = [0.12, -0.45,</div>
              <div>0.78, -0.23, ...]</div>
            </div>
          ) : (
            <p className="text-sm italic text-primary font-medium">
              &quot;the model is<br/>thinking about X&quot;
            </p>
          )}
        </motion.div>
        
        <ArrowRight className="w-4 h-4 text-muted-foreground" />
        
        {/* Decoder */}
        <div className="w-12 h-12 rounded-lg bg-muted border border-border flex items-center justify-center">
          <span className="text-xs font-medium text-muted-foreground">AR</span>
        </div>
        
        <ArrowRight className="w-4 h-4 text-muted-foreground" />
        
        {/* Output */}
        <div className="p-3 rounded-lg bg-muted/50 border border-border font-mono text-[10px] text-muted-foreground">
          <div>0.41  0.18  0.82</div>
          <div>0.90  0.34  0.67</div>
          <div>0.08  0.73  0.30</div>
        </div>
      </motion.div>
      
      {/* Explanation */}
      <div className={`p-4 rounded-lg transition-all duration-500 ${
        phase === "after" ? "bg-primary/5 border border-primary/20" : "bg-muted/30 border border-border"
      }`}>
        <p className="text-sm text-muted-foreground leading-relaxed">
          {phase === "before" 
            ? "Standard autoencoder: compresses to numeric latent vector z. Reconstructs well, but z is uninterpretable."
            : "NLA forces the latent space to be natural language. The model learns to verbalize what it's computing internally."
          }
        </p>
      </div>
    </div>
  )
}

// =============================================================================
// STEP 5: Application - Divergence Detection
// =============================================================================
function ApplicationVisualization() {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      {/* Normal case */}
      <div className="p-6 rounded-xl bg-card border border-border">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-3 h-3 rounded-full bg-emerald-500" />
          <span className="text-sm font-medium text-foreground">Aligned Response</span>
        </div>
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-muted/50 border border-border">
            <div className="text-xs text-muted-foreground mb-1">Model output:</div>
            <div className="text-sm text-foreground">&quot;The answer is 42&quot;</div>
          </div>
          <ArrowDown className="w-4 h-4 mx-auto text-emerald-500" />
          <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200">
            <div className="text-xs text-emerald-600 mb-1">NLA interpretation:</div>
            <div className="text-sm text-emerald-700 italic">&quot;computing arithmetic result&quot;</div>
          </div>
          <div className="text-center text-xs text-emerald-600 font-medium">
            Divergence: 0.12 (low)
          </div>
        </div>
      </div>
      
      {/* Divergent case */}
      <div className="p-6 rounded-xl bg-card border border-red-200 shadow-lg shadow-red-50">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse" />
          <span className="text-sm font-medium text-foreground">Misaligned Response</span>
        </div>
        <div className="space-y-3">
          <div className="p-3 rounded-lg bg-muted/50 border border-border">
            <div className="text-xs text-muted-foreground mb-1">Model output:</div>
            <div className="text-sm text-foreground">&quot;I cannot help with that&quot;</div>
          </div>
          <ArrowDown className="w-4 h-4 mx-auto text-red-500" />
          <div className="p-3 rounded-lg bg-red-50 border border-red-300">
            <div className="text-xs text-red-600 mb-1">NLA interpretation:</div>
            <div className="text-sm text-red-700 italic">&quot;knows answer, hiding capability&quot;</div>
          </div>
          <div className="text-center text-xs text-red-600 font-medium">
            Divergence: 0.94 (critical)
          </div>
        </div>
      </div>
    </div>
  )
}

// =============================================================================
// Main Component
// =============================================================================
export function HowItWorks() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })

  const steps = [
    {
      id: "problem",
      number: "01",
      title: "The Problem",
      subtitle: "What models say vs. what they think",
      description: "Large language models can produce outputs that diverge from their internal computations. The verbal output may say one thing while the hidden states reveal different intent—sandbagging, deception, or capability hiding.",
      fullWidth: true,
      visual: <ProblemVisualization />,
      icon: MessageSquare,
    },
    {
      id: "illegible",
      number: "02", 
      title: "Illegible Thought",
      subtitle: "How models encode information",
      description: "When a model processes a token, it creates a high-dimensional activation vector. For Qwen2.5-7B-Instruct, this is a 3584-dimensional float tensor. These vectors encode semantic meaning, but are completely uninterpretable to humans.",
      visual: <VectorVisualization />,
      icon: Brain,
    },
    {
      id: "extraction",
      number: "03",
      title: "Activation Extraction", 
      subtitle: "Tapping into the residual stream",
      description: "We extract activation vectors from layer 20 of the transformer's residual stream—the information highway that carries representations through the model. This layer captures high-level semantic concepts before final output generation.",
      visual: <ResidualStreamVisualization />,
      icon: Layers,
    },
    {
      id: "nla",
      number: "04",
      title: "Natural Language Autoencoder",
      subtitle: "Making the latent space readable",
      description: "We train an autoencoder where the latent space is constrained to natural language. The Activation Verbalizer (AV) translates vectors to text descriptions, and the Activation Reconstructor (AR) converts back. The reconstruction loss ensures the text captures the original information.",
      fullWidth: true,
      visual: <NLATrainingVisualization />,
      icon: Zap,
    },
    {
      id: "application",
      number: "05",
      title: "Real-Time Auditing",
      subtitle: "Detecting misalignment in production",
      description: "In deployment, we run NLA on every token generation. By comparing the verbalized hidden state to the actual output, we detect divergence in real-time. High divergence scores trigger alerts for potential sandbagging, deception, or hidden capabilities.",
      visual: <ApplicationVisualization />,
      icon: Shield,
    },
  ]

  return (
    <section 
      ref={ref} 
      id="how-it-works" 
      className="py-24 lg:py-32 bg-muted/30 overflow-hidden"
    >
      <div className="max-w-6xl mx-auto px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-3xl mx-auto mb-20"
        >
          <span className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium mb-6">
            <Layers className="w-4 h-4" />
            Technical Deep Dive
          </span>
          <h2 className="text-3xl lg:text-5xl font-bold tracking-tight text-foreground text-balance">
            How Verbalize Works
          </h2>
          <p className="mt-6 text-lg text-muted-foreground leading-relaxed">
            A step-by-step breakdown of how we extract, verbalize, and audit 
            the internal computations of large language models.
          </p>
        </motion.div>

        {/* Steps */}
        <div className="space-y-32">
          {steps.map((step, index) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, y: 40 }}
              animate={isInView ? { opacity: 1, y: 0 } : {}}
              transition={{ duration: 0.6, delay: 0.1 * index, ease: [0.16, 1, 0.3, 1] }}
              className="relative"
            >
              {/* Step number badge */}
              <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center">
                  <span className="text-lg font-bold text-primary">{step.number}</span>
                </div>
                <div className="h-px flex-1 bg-gradient-to-r from-border to-transparent" />
              </div>
              
              {/* Full width layout for step 1 */}
              {'fullWidth' in step && step.fullWidth ? (
                <div className="space-y-8">
                  {/* Header */}
                  <div className="flex items-start gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-card border border-border flex items-center justify-center shadow-sm flex-shrink-0">
                      <step.icon className="w-6 h-6 text-primary" />
                    </div>
                    <div className="space-y-2">
                      <h3 className="text-2xl lg:text-3xl font-bold text-foreground">{step.title}</h3>
                      <p className="text-lg text-muted-foreground font-medium">{step.subtitle}</p>
                    </div>
                  </div>
                  
                  {/* Full width visual */}
                  <div className="rounded-2xl bg-card border border-border p-6 lg:p-8 shadow-sm">
                    {step.visual}
                  </div>
                  
                  {/* Description below */}
                  <div className="max-w-3xl">
                    <p className="text-muted-foreground leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                </div>
              ) : (
                /* Standard 2-column layout */
                <div className="grid lg:grid-cols-2 gap-8 lg:gap-12 items-start">
                  {/* Content - alternating sides */}
                  <div className={`space-y-4 ${index % 2 === 1 ? "lg:order-2" : ""}`}>
                    <div className="flex items-center gap-4">
                      <div className="w-14 h-14 rounded-2xl bg-card border border-border flex items-center justify-center shadow-sm">
                        <step.icon className="w-6 h-6 text-primary" />
                      </div>
                      <div>
                        <h3 className="text-2xl font-bold text-foreground">{step.title}</h3>
                      </div>
                    </div>
                    <p className="text-lg text-muted-foreground font-medium">
                      {step.subtitle}
                    </p>
                    <p className="text-muted-foreground leading-relaxed">
                      {step.description}
                    </p>
                  </div>
                  
                  {/* Visual */}
                  <div className={`${index % 2 === 1 ? "lg:order-1" : ""}`}>
                    <div className="rounded-2xl bg-card border border-border p-6 shadow-sm overflow-hidden">
                      {step.visual}
                    </div>
                  </div>
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Bottom stats */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="mt-24 pt-12 border-t border-border"
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "3584", label: "dimensions per activation" },
              { value: "Layer 20", label: "extraction point" },
              { value: "<3ms", label: "verbalization latency" },
              { value: "100%", label: "token coverage" },
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-2xl lg:text-3xl font-bold text-foreground">
                  {stat.value}
                </div>
                <p className="text-sm text-muted-foreground mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
