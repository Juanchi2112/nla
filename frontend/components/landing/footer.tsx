"use client"

import Link from "next/link"
import Image from "next/image"
import { Github, Twitter, Linkedin } from "lucide-react"

export function Footer() {
  return (
    <footer className="bg-card border-t border-border">
      <div className="max-w-7xl mx-auto px-6 lg:px-8 py-12">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          {/* Brand */}
          <div className="flex flex-col gap-4">
            <Link href="/" className="flex items-center gap-2.5">
              <Image 
                src="/logo.svg" 
                alt="Verbalize" 
                width={28} 
                height={28}
                className="w-7 h-7"
              />
              <span className="font-semibold text-lg tracking-tight text-foreground">Verbalize</span>
            </Link>
            <p className="text-sm text-muted-foreground max-w-xs">
              Real-time AI alignment auditing built on mechanistic interpretability.
            </p>
          </div>

          {/* Links */}
          <div className="flex flex-wrap items-center gap-6 text-sm">
            <Link 
              href="#how-it-works"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              How It Works
            </Link>
            <Link 
              href="#demo"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Demo
            </Link>
            <Link 
              href="#team"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Team
            </Link>
            <Link 
              href="/contact"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Contact
            </Link>
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
