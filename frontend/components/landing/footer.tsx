"use client"

import Link from "next/link"
import { Github, Twitter, Linkedin, Shield } from "lucide-react"

export function Footer() {
  return (
    <footer className="bg-background border-t border-border">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-16">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-12">
          {/* Brand */}
          <div className="flex flex-col gap-6">
            <Link href="/" className="flex items-center gap-2.5 group">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shadow-lg shadow-primary/20 group-hover:scale-105 transition-transform">
                <Shield className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="font-bold text-2xl tracking-tight text-foreground">Verbalize</span>
            </Link>
            <p className="text-sm text-muted-foreground max-w-xs leading-relaxed">
              Mechanistic interpretability for the agentic era. Expose computational intent in real-time.
            </p>
          </div>

          {/* Links */}
          <div className="flex flex-wrap items-center gap-x-8 gap-y-4 text-xs font-semibold uppercase tracking-widest">
            <Link 
              href="/how-it-works"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              Technology
            </Link>
            <Link 
              href="/#demo"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              Demo
            </Link>
            <Link 
              href="/#team"
              className="text-muted-foreground hover:text-primary transition-colors"
            >
              Team
            </Link>
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/5 border border-emerald-500/10">
              <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] text-emerald-500/80">Systems Operational</span>
            </div>
          </div>

          {/* Social */}
          <div className="flex items-center gap-4">
            <a href="https://github.com/Juanchi2112/nla" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground transition-colors">
              <Github className="w-5 h-5" />
            </a>
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              <Twitter className="w-5 h-5" />
            </a>
            <a href="#" className="text-muted-foreground hover:text-foreground transition-colors">
              <Linkedin className="w-5 h-5" />
            </a>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Verbalize. All rights reserved.
          </p>
          <p className="text-xs text-muted-foreground">
            Built with SGLang, Next.js &amp; NLA
          </p>
        </div>
      </div>
    </footer>
  )
}
