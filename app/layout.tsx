import type { Metadata, Viewport } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'NEXUS-CI · Evidence-Centric Criminal Intelligence',
  description:
    'NEXUS-CI turns fragmented investigation data into explainable, evidence-backed criminal intelligence. A decision-support platform for investigators.',
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0b0e14',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased font-sans bg-background text-foreground">
        {children}
      </body>
    </html>
  )
}
