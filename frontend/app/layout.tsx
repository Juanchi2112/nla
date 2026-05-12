import type { Metadata } from 'next'
import { Inter, Fira_Code } from 'next/font/google'
import { Analytics } from '@vercel/analytics/next'
import './globals.css'

const inter = Inter({ 
  subsets: ["latin"],
  variable: '--font-inter',
  display: 'swap',
});

const firaCode = Fira_Code({ 
  subsets: ["latin"],
  variable: '--font-fira-code',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Verbalize | Real-Time AI Alignment Auditing',
  description: 'Stop trusting what models say. Read what they compute. End-to-end alignment auditing built on mechanistic interpretability.',
  generator: 'v0.app',
  openGraph: {
    title: 'Verbalize | Real-Time AI Alignment Auditing',
    description: 'Stop trusting what models say. Read what they compute. End-to-end alignment auditing built on mechanistic interpretability.',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Verbalize | Real-Time AI Alignment Auditing',
    description: 'Stop trusting what models say. Read what they compute.',
  },
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${firaCode.variable} dark bg-background`}>
      <body className="font-sans antialiased min-h-screen">
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
