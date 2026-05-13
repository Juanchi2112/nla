"use client"

import { useState, useEffect, useCallback } from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { motion, AnimatePresence } from "framer-motion"
import { Menu, X, Shield } from "lucide-react"
import { Button } from "@/components/ui/button"

const navLinks = [
  { href: "/", label: "Home", sectionId: null },
  { href: "/how-it-works", label: "Technology", sectionId: null },
  { href: "/example", label: "Interactive Story", sectionId: null },
  { href: "/#audit", label: "Compliance", sectionId: "audit" },
  { href: "/#demo", label: "Demo", sectionId: "demo" },
  { href: "/#team", label: "Team", sectionId: "team" },
]

export function Navigation() {
  const [isOpen, setIsOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const [activeSection, setActiveSection] = useState<string | null>(null)
  const pathname = usePathname()

  const updateActiveSection = useCallback(() => {
    if (pathname !== "/") return
    const midpoint = window.innerHeight * 0.5
    // Sort by actual DOM position so page order beats navLinks order
    const sorted = navLinks
      .filter((l) => l.sectionId)
      .map((l) => ({ id: l.sectionId as string, top: document.getElementById(l.sectionId!)?.getBoundingClientRect().top ?? Infinity }))
      .sort((a, b) => a.top - b.top)
    let current: string | null = null
    for (const { id, top } of sorted) {
      if (top <= midpoint) current = id
    }
    setActiveSection(current)
  }, [pathname])

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
      updateActiveSection()
    }
    window.addEventListener("scroll", handleScroll, { passive: true })
    updateActiveSection()
    return () => window.removeEventListener("scroll", handleScroll)
  }, [updateActiveSection])

  const isActive = (link: (typeof navLinks)[0]) => {
    if (link.sectionId) {
      return pathname === "/" && activeSection === link.sectionId
    }
    if (link.href === "/") {
      return pathname === "/" && activeSection === null
    }
    return pathname === link.href || pathname.startsWith(link.href + "/")
  }

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled ? "bg-background/60 backdrop-blur-xl border-b border-white/5 py-3" : "bg-transparent py-5"
      }`}
    >
      <nav className="max-w-7xl mx-auto px-6 lg:px-8">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link href="/" className="flex items-center gap-2 group transition-transform hover:scale-[1.02]">
            <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center shadow-lg shadow-primary/20">
              <Shield className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="font-bold text-2xl tracking-tight text-foreground">Verbalize</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-10">
            {navLinks.map((link) => {
              const active = isActive(link)
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`font-bold uppercase tracking-[0.2em] transition-all duration-200 ${
                    active
                      ? "text-xs text-foreground underline underline-offset-4 decoration-foreground/40"
                      : "text-[10px] text-muted-foreground hover:text-primary"
                  }`}
                >
                  {link.label}
                </Link>
              )
            })}
          </div>

          {/* CTA */}
          <div className="hidden md:flex items-center gap-4">
            <Link href="/contact">
              <Button size="sm" className="bg-primary hover:bg-primary/90 text-primary-foreground font-bold rounded-full px-6 h-10 shadow-lg shadow-primary/20 transition-all hover:-translate-y-0.5">
                Get Access
              </Button>
            </Link>
          </div>

          {/* Mobile toggle */}
          <button
            className="md:hidden p-2 text-muted-foreground hover:text-foreground"
            onClick={() => setIsOpen(!isOpen)}
            aria-label="Toggle menu"
          >
            {isOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile menu */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="md:hidden pt-4 pb-6 space-y-4"
            >
              <div className="border-t border-white/5 pt-4 flex flex-col gap-4">
                {navLinks.map((link) => {
                  const active = isActive(link)
                  return (
                    <Link
                      key={link.href}
                      href={link.href}
                      onClick={() => setIsOpen(false)}
                      className={`block text-sm font-semibold uppercase tracking-widest py-2 transition-colors ${
                        active ? "text-foreground underline underline-offset-4" : "text-muted-foreground hover:text-primary"
                      }`}
                    >
                      {link.label}
                    </Link>
                  )
                })}
                <Link href="/contact" onClick={() => setIsOpen(false)}>
                  <Button className="w-full mt-4 bg-primary text-primary-foreground font-bold rounded-full py-6">
                    Get Access
                  </Button>
                </Link>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </nav>
    </header>
  )
}
