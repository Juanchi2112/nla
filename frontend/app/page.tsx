import { Navigation } from "@/components/landing/navigation"
import { Hero } from "@/components/landing/hero"
import { MarqueeBanner } from "@/components/landing/marquee-banner"
import { Problem } from "@/components/landing/problem"
import { Solution } from "@/components/landing/solution"
import { HowItWorks } from "@/components/landing/how-it-works"
import { Demo } from "@/components/landing/demo"
import { Proof } from "@/components/landing/proof"
import { Hackathon } from "@/components/landing/hackathon"
import { Testimonials } from "@/components/landing/testimonials"
import { UseCases } from "@/components/landing/use-cases"
import { SecondaryCTA } from "@/components/landing/secondary-cta"
import { FAQ } from "@/components/landing/faq"
import { FinalCTA } from "@/components/landing/final-cta"
import { Footer } from "@/components/landing/footer"

export default function Home() {
  return (
    <main className="min-h-screen">
      <Navigation />
      <Hero />
      <MarqueeBanner />
      <Problem />
      <Solution />
      <HowItWorks />
      <Demo />
      <Proof />
      <Hackathon />
      <Testimonials />
      <UseCases />
      <SecondaryCTA />
      <FAQ />
      <FinalCTA />
      <Footer />
    </main>
  )
}
