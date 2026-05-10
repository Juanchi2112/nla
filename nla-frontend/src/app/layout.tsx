import type { Metadata } from "next";
import { Source_Serif_4, JetBrains_Mono } from "next/font/google";
import Navbar from "@/components/Navbar";
import { AuroraBackground } from "@/components/ui/AuroraBackground";
import "./globals.css";

const serif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-serif",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "verbalize — alignment auditing for LLMs",
  description:
    "Auditamos qué está pensando un LLM mientras habla. Leemos el residual stream del modelo, no la cadena de pensamiento que el modelo escribe sabiendo que la van a leer. Basado en Natural Language Autoencoders (Anthropic, 2026).",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" className={`${serif.variable} ${mono.variable}`}>
      <body>
        <AuroraBackground />
        <Navbar />
        {children}
      </body>
    </html>
  );
}
