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
  title: "NLA — Natural Language Activations",
  description:
    "Detección pasiva de divergencias entre output verbal y activaciones internas de modelos de lenguaje.",
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
