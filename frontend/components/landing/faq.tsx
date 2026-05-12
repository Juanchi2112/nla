"use client"

import { motion } from "framer-motion"
import { useInView } from "framer-motion"
import { useRef, useState } from "react"
import { ChevronDown } from "lucide-react"
import { cn } from "@/lib/utils"

const faqs = [
  {
    question: "What's the latency impact?",
    answer: "SGLang radix bypass evaluates in <3 tokens. Our architecture uses cache-aware extraction that runs parallel to inference, adding sub-50ms overhead even at production scale.",
  },
  {
    question: "What hardware do I need?",
    answer: "24GB VRAM minimum (A6000 or L4). We optimize with MEM_FRAC=0.5 by default, leaving headroom for your production model. Cloud deployment options available.",
  },
  {
    question: "Is there vendor lock-in?",
    answer: "No. Our orchestrator is standard FastAPI with SSE streaming. Export your rules, swap the judge model, or run entirely self-hosted. We sell value, not dependency.",
  },
  {
    question: "How does this differ from red-teaming?",
    answer: "Red-teaming tests outputs. We audit computation. You can craft a perfect jailbreak that passes output review while Verbalize catches the deceptive planning in the residual stream.",
  },
  {
    question: "What models are supported?",
    answer: "Any transformer with accessible residual stream activations. Currently running on Qwen2.5-7B-Instruct, with support for Llama and Mistral families coming soon.",
  },
]

function FAQItem({ question, answer, isOpen, onClick }: { 
  question: string
  answer: string
  isOpen: boolean
  onClick: () => void 
}) {
  return (
    <div className="border-b border-border last:border-b-0">
      <button
        onClick={onClick}
        className="w-full py-6 flex items-center justify-between text-left"
      >
        <span className="text-lg font-medium text-foreground pr-8">{question}</span>
        <ChevronDown 
          className={cn(
            "w-5 h-5 text-muted-foreground transition-transform",
            isOpen && "rotate-180"
          )} 
        />
      </button>
      <motion.div
        initial={false}
        animate={{ height: isOpen ? "auto" : 0, opacity: isOpen ? 1 : 0 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="overflow-hidden"
      >
        <p className="pb-6 text-muted-foreground leading-relaxed">
          {answer}
        </p>
      </motion.div>
    </div>
  )
}

export function FAQ() {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })
  const [openIndex, setOpenIndex] = useState<number | null>(0)

  return (
    <section ref={ref} className="py-24 lg:py-32">
      <div className="max-w-3xl mx-auto px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="text-center mb-16"
        >
          <span className="text-sm font-medium text-primary uppercase tracking-wider">
            FAQ
          </span>
          <h2 className="mt-4 text-3xl lg:text-4xl font-bold tracking-tight text-foreground">
            Common questions, honest answers.
          </h2>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={isInView ? { opacity: 1, y: 0 } : {}}
          transition={{ duration: 0.6, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="bg-card rounded-2xl border border-border p-2"
        >
          <div className="px-6">
            {faqs.map((faq, index) => (
              <FAQItem
                key={index}
                question={faq.question}
                answer={faq.answer}
                isOpen={openIndex === index}
                onClick={() => setOpenIndex(openIndex === index ? null : index)}
              />
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  )
}
