"use client"

import { motion, useInView } from "framer-motion"
import { useRef, useState } from "react"
import { Clock, Zap, Code2, Users, Github, Linkedin } from "lucide-react"
import { Button } from "@/components/ui/button"

const team = [
  {
    name: "Ana Paula Tissera",
    role: "AI Engineering Student",
    university: "UDESA",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/anapaula-BopD6ovSXGGdra5zELCLhq9mRNsK3n.png",
    social: { github: "https://github.com/anatissera", linkedin: "https://www.linkedin.com/in/ana-paula-tissera/" },
  },
  {
    name: "Joaquin Leon Alderete",
    role: "AI Engineering Student",
    university: "UDESA",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/joaquin-vpqoNw1sg9avBwRMoBMFXv0V7meTvq.jpeg",
    social: { github: "https://github.com/joaquinleondev", linkedin: "https://www.linkedin.com/in/jleonalderete/" },
  },
  {
    name: "Juan Andres Quiroga",
    role: "AI Engineering Student",
    university: "UDESA",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/juanandres-h1D8RNT9MfnhYFv3C2qVYNyoP6cF09.jpeg",
    social: { github: "https://github.com/Juanchi2112", linkedin: "https://www.linkedin.com/in/juan-andres-quiroga/" },
  },
  {
    name: "Ignacio Vargas Fernandez",
    role: "AI Engineering Student",
    university: "UDESA",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/ignacio-G7pwZcQzyoEj4vLzWTvm8M7c5JcZZY.jpeg",
    social: { github: "https://github.com/ignacio279", linkedin: "https://www.linkedin.com/in/ignacio-vargas-fernandez/" },
  },
  {
    name: "Alexander Bodner",
    role: "AI Engineering Student",
    university: "UDESA",
    image: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/alexander-Ypw5XJXsZqpKr4GMzMEuDMhvZYjrFE.jpeg",
    social: { github: "https://github.com/AlexBodner", linkedin: "https://www.linkedin.com/in/alexanderbodner/" },
  },
]



export function Hackathon() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const [hoveredMember, setHoveredMember] = useState<number | null>(null)

  return (
    <section ref={ref} id="team" className="py-24 lg:py-32 relative overflow-hidden bg-background border-t border-border">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-[0.03] pointer-events-none">
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(to right, var(--foreground) 1px, transparent 1px), linear-gradient(to bottom, var(--foreground) 1px, transparent 1px)`,
          backgroundSize: '80px 80px'
        }} />
      </div>
      
      <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-3xl mx-auto mb-20"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-bold uppercase tracking-widest mb-8">
            <Clock className="w-3 h-3" />
            36-Hour Build
          </div>
          <h2 className="text-4xl lg:text-6xl font-bold tracking-tight text-balance">
            From Research to
            <br />
            <span className="text-primary">Production Logic</span>
          </h2>
          <p className="mt-8 text-lg text-muted-foreground leading-relaxed">
            Verbalize was forged in a high-stakes hackathon weekend. We port frontier NLA 
            research into a real-time monitoring layer for safety-critical agents.
          </p>
        </motion.div>

        {/* Team grid with hover effects */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="text-center mb-16">
            <h3 className="text-3xl font-bold tracking-tight">The Builders</h3>
            <p className="mt-4 text-muted-foreground font-medium">AI Engineering @ Universidad de San Andres</p>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-12">
            {team.map((member, index) => (
              <motion.div
                key={member.name}
                initial={{ opacity: 0, y: 24 }}
                animate={isInView ? { opacity: 1, y: 0 } : {}}
                transition={{ duration: 0.6, delay: 0.4 + index * 0.1, ease: [0.16, 1, 0.3, 1] }}
                onMouseEnter={() => setHoveredMember(index)}
                onMouseLeave={() => setHoveredMember(null)}
                className="group cursor-pointer"
              >
                <motion.div
                  animate={{ 
                    scale: hoveredMember === index ? 1.02 : 1,
                    y: hoveredMember === index ? -4 : 0
                  }}
                  transition={{ duration: 0.2 }}
                  className="relative"
                >
                  <div className="aspect-square rounded-2xl bg-secondary border border-border mb-4 overflow-hidden relative transition-colors group-hover:border-primary/50">
                    {/* Glow effect on hover */}
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-t from-primary/10 via-transparent to-transparent z-10"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: hoveredMember === index ? 1 : 0 }}
                    />
                    
                    {/* Member photo */}
                    <img 
                      src={member.image} 
                      alt={member.name}
                      className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-500"
                    />

                    {/* Social icons overlay */}
                    <motion.div
                      className="absolute bottom-3 left-3 right-3 flex justify-center gap-2 z-20"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ 
                        opacity: hoveredMember === index ? 1 : 0,
                        y: hoveredMember === index ? 0 : 10
                      }}
                    >
                      <a href={member.social.github} target="_blank" rel="noopener noreferrer">
                        <Button size="sm" variant="secondary" className="h-8 w-8 p-0 rounded-full bg-background/80 backdrop-blur-md">
                          <Github className="w-4 h-4" />
                        </Button>
                      </a>
                      <a href={member.social.linkedin} target="_blank" rel="noopener noreferrer">
                        <Button size="sm" variant="secondary" className="h-8 w-8 p-0 rounded-full bg-background/80 backdrop-blur-md">
                          <Linkedin className="w-4 h-4" />
                        </Button>
                      </a>
                    </motion.div>
                  </div>
                  
                  <h4 className="font-bold text-sm text-foreground">{member.name}</h4>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-primary mt-1">{member.role}</p>
                </motion.div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Stats row with animated counters */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="mt-24 grid grid-cols-2 lg:grid-cols-4 gap-12 py-16 border-t border-border/50"
        >
          {[
            { value: 36, label: "Hours of hacking", icon: Clock },
            { value: 5, label: "Team members", icon: Users },
            { value: 2.3, label: "K lines of code", icon: Code2, suffix: "k" },
            { value: 1, label: "Working demo", icon: Zap },
          ].map((stat, index) => {
            const Icon = stat.icon
            return (
              <motion.div
                key={stat.label}
                className="text-center group"
                whileHover={{ scale: 1.05 }}
              >
                <Icon className="w-5 h-5 text-primary mx-auto mb-4 opacity-50 group-hover:opacity-100 group-hover:scale-110 transition-all" />
                <div className="text-5xl font-bold tracking-tighter">
                  {stat.suffix ? `${stat.value}${stat.suffix}` : stat.value}
                </div>
                <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted-foreground">{stat.label}</p>
              </motion.div>
            )
          })}
        </motion.div>
      </div>
    </section>
  )
}
