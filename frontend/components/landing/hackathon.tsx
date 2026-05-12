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
    <section ref={ref} id="hackathon" className="py-24 lg:py-32 relative overflow-hidden bg-foreground text-background">
      {/* Animated background grid */}
      <div className="absolute inset-0 opacity-5">
        <div className="absolute inset-0" style={{
          backgroundImage: `linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)`,
          backgroundSize: '40px 40px'
        }} />
      </div>
      
      <div className="relative max-w-7xl mx-auto px-6 lg:px-8">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-3xl mx-auto mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary text-white text-sm font-medium mb-6">
            <Clock className="w-4 h-4" />
            36-Hour Build
          </div>
          <h2 className="text-3xl lg:text-5xl font-bold tracking-tight text-balance">
            From Research Paper to
            <br />
            <span className="text-primary">Working Demo</span>
          </h2>
          <p className="mt-6 text-lg text-background/70 leading-relaxed">
            Verbalize was built in a single hackathon weekend. Watch the journey from NLA paper 
            to catching real deceptive patterns in production models.
          </p>
        </motion.div>

        {/* Team grid with hover effects */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="text-center mb-12">
            <h3 className="text-2xl font-bold">The Builders</h3>
            <p className="mt-2 text-background/60">AI Engineering Students @ Universidad de San Andres</p>
          </div>

          <div className="grid grid-cols-2 lg:grid-cols-5 gap-6 lg:gap-8">
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
                    scale: hoveredMember === index ? 1.05 : 1,
                    y: hoveredMember === index ? -8 : 0
                  }}
                  transition={{ duration: 0.3 }}
                  className="relative"
                >
                  <div className="aspect-square rounded-xl bg-background/5 border border-background/10 mb-3 overflow-hidden relative group-hover:border-primary/50 transition-colors">
                    {/* Glow effect on hover */}
                    <motion.div
                      className="absolute inset-0 bg-gradient-to-t from-primary/20 via-transparent to-transparent z-10"
                      initial={{ opacity: 0 }}
                      animate={{ opacity: hoveredMember === index ? 1 : 0 }}
                    />
                    
                    {/* Member photo */}
                    <img 
                      src={member.image} 
                      alt={member.name}
                      className="w-full h-full object-cover"
                    />

                    {/* Social icons overlay */}
                    <motion.div
                      className="absolute bottom-2 left-2 right-2 flex justify-center gap-1.5 z-20"
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ 
                        opacity: hoveredMember === index ? 1 : 0,
                        y: hoveredMember === index ? 0 : 10
                      }}
                    >
                      <a href={member.social.github} target="_blank" rel="noopener noreferrer">
                        <Button size="sm" variant="secondary" className="h-7 w-7 p-0 rounded-full">
                          <Github className="w-3.5 h-3.5" />
                        </Button>
                      </a>
                      <a href={member.social.linkedin} target="_blank" rel="noopener noreferrer">
                        <Button size="sm" variant="secondary" className="h-7 w-7 p-0 rounded-full">
                          <Linkedin className="w-3.5 h-3.5" />
                        </Button>
                      </a>
                    </motion.div>
                  </div>
                  
                  <h4 className="font-semibold text-sm">{member.name}</h4>
                  <p className="text-xs text-primary">{member.role}</p>
                  <p className="text-xs text-background/50">{member.university}</p>
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
          className="mt-20 grid grid-cols-2 lg:grid-cols-4 gap-8 py-12 border-t border-b border-background/10"
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
                <Icon className="w-6 h-6 text-primary mx-auto mb-3 group-hover:scale-110 transition-transform" />
                <div className="text-4xl lg:text-5xl font-bold">
                  {stat.suffix ? `${stat.value}${stat.suffix}` : stat.value}
                </div>
                <p className="mt-1 text-sm text-background/60">{stat.label}</p>
              </motion.div>
            )
          })}
        </motion.div>
      </div>
    </section>
  )
}
