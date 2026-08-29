import { cn } from '@/lib/utils'

// Abstract "connected nodes" mark — a small evidence graph, not a generic logo.
export function NexusMark({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 32 32"
      className={cn('text-primary', className)}
      role="img"
      aria-label="NEXUS-CI"
      fill="none"
    >
      <rect x="1" y="1" width="30" height="30" rx="7" className="fill-elevated stroke-border" strokeWidth="1" />
      <line x1="10" y1="11" x2="22" y2="9" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <line x1="10" y1="11" x2="12" y2="22" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <line x1="22" y1="9" x2="23" y2="21" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <line x1="12" y1="22" x2="23" y2="21" stroke="currentColor" strokeWidth="1.5" opacity="0.5" />
      <circle cx="10" cy="11" r="3.2" fill="currentColor" />
      <circle cx="22" cy="9" r="2.4" className="fill-foreground" />
      <circle cx="12" cy="22" r="2.4" className="fill-foreground" />
      <circle cx="23" cy="21" r="2.8" fill="currentColor" />
    </svg>
  )
}
