import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { ENTITY_META, type EntityType } from '@/lib/domain/types'

// ---------- Confidence meter ----------
export function ConfidenceMeter({
  value,
  label = 'Confidence',
  className,
}: {
  value: number
  label?: string
  className?: string
}) {
  const tone = value >= 80 ? '#10b981' : value >= 60 ? '#f59e0b' : '#94a3b8'
  return (
    <div className={cn('flex flex-col gap-1 w-full', className)}>
      <div className="flex items-center justify-between text-[11px] font-mono">
        <span className="text-slate-400">{label}</span>
        <span className="font-bold text-white">{value}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-950 border border-slate-800">
        <div
          className="h-full rounded-full transition-all duration-500 shadow-sm"
          style={{ width: `${Math.min(100, Math.max(0, value))}%`, backgroundColor: tone }}
        />
      </div>
    </div>
  )
}

// ---------- Severity / status badges ----------
const SEVERITY_TONE: Record<string, string> = {
  high: 'border-rose-500/40 bg-rose-500/10 text-rose-400 font-bold',
  critical: 'border-rose-500/50 bg-rose-500/15 text-rose-300 font-extrabold animate-pulse',
  medium: 'border-amber-500/40 bg-amber-500/10 text-amber-400 font-bold',
  low: 'border-slate-800 bg-slate-900 text-slate-400',
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wide',
        SEVERITY_TONE[severity] ?? SEVERITY_TONE.low,
      )}
    >
      {severity}
    </span>
  )
}

const STATUS_TONE: Record<string, string> = {
  active: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400 font-bold',
  processed: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400 font-bold',
  success: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400 font-bold',
  open: 'border-amber-500/40 bg-amber-500/10 text-amber-400 font-bold',
  processing: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300 font-bold animate-pulse',
  under_review: 'border-amber-500/40 bg-amber-500/10 text-amber-400 font-bold',
  investigating: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400 font-bold',
  acknowledged: 'border-slate-800 bg-slate-900 text-slate-400',
  cold: 'border-slate-800 bg-slate-950 text-slate-500',
  closed: 'border-slate-800 bg-slate-950 text-slate-500',
  dismissed: 'border-slate-800 bg-slate-950 text-slate-500',
  failed: 'border-rose-500/40 bg-rose-500/10 text-rose-400 font-bold',
  denied: 'border-rose-500/40 bg-rose-500/10 text-rose-400 font-bold',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[10px] uppercase font-bold tracking-wide',
        STATUS_TONE[status] ?? 'border-slate-800 bg-slate-900 text-slate-400',
      )}
    >
      <span className="size-1.5 rounded-full bg-current" />
      {status.replace(/_/g, ' ')}
    </span>
  )
}

// ---------- Entity badge ----------
export function EntityBadge({
  type,
  label,
  className,
}: {
  type: EntityType
  label?: string
  className?: string
}) {
  const meta = ENTITY_META[type] || { token: '#38bdf8', label: type }
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-mono text-[10px] font-bold uppercase tracking-tight shadow-sm',
        className,
      )}
      style={{
        borderColor: `color-mix(in oklch, ${meta.token} 40%, transparent)`,
        background: `color-mix(in oklch, ${meta.token} 12%, transparent)`,
        color: meta.token,
      }}
    >
      <span className="size-1.5 rounded-full" style={{ background: meta.token }} />
      {label ?? meta.label}
    </span>
  )
}

// ---------- Section header ----------
export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="font-mono text-[10px] font-bold uppercase tracking-wider text-slate-400">
      {children}
    </p>
  )
}

// ---------- Stat card ----------
export function StatCard({
  label,
  value,
  hint,
  icon,
  tone = 'default',
}: {
  label: string
  value: ReactNode
  hint?: string
  icon?: ReactNode
  tone?: 'default' | 'warning' | 'danger' | 'success'
}) {
  const borderTone =
    tone === 'danger'
      ? 'border-rose-500/30 hover:border-rose-500/50 bg-slate-900/90'
      : tone === 'warning'
        ? 'border-amber-500/30 hover:border-amber-500/50 bg-slate-900/90'
        : tone === 'success'
          ? 'border-emerald-500/30 hover:border-emerald-500/50 bg-slate-900/90'
          : 'border-slate-800 hover:border-cyan-500/40 bg-slate-900/90'

  return (
    <div className={cn('flex flex-col justify-between rounded-xl border p-4 shadow-xl transition-all duration-200 hover:shadow-cyan-500/5', borderTone)}>
      <div className="flex items-start justify-between">
        <span className="font-mono text-[11px] font-bold text-slate-400 tracking-wide uppercase">{label}</span>
        {icon ? <span className="shrink-0 p-1.5 rounded-lg bg-slate-950 border border-slate-800">{icon}</span> : null}
      </div>
      <div className="mt-3">
        <p className="font-mono text-2xl font-extrabold tracking-tight text-white">{value}</p>
        {hint ? <p className="mt-1 text-[10px] font-mono text-slate-400">{hint}</p> : null}
      </div>
    </div>
  )
}

// ---------- Stat Cell ----------
export function StatCell({
  label,
  value,
  mono = false,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex flex-col rounded-lg border border-slate-800 bg-slate-950 p-2.5 text-center">
      <span className="font-mono text-[9px] uppercase font-bold text-slate-400">{label}</span>
      <span className={cn('mt-0.5 text-xs font-bold text-white', mono && 'font-mono')}>{value}</span>
    </div>
  )
}

// ---------- Meter ----------
export function Meter({ value, label = 'Confidence' }: { value: number; label?: string }) {
  return <ConfidenceMeter value={value} label={label} />
}

// ---------- Relevance Badge ----------
export function RelevanceBadge({ value }: { value: number }) {
  const tone =
    value >= 75
      ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-400 font-bold'
      : value >= 50
        ? 'border-amber-500/40 bg-amber-500/10 text-amber-400 font-bold'
        : 'border-slate-800 bg-slate-950 text-slate-400'
  return (
    <span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-mono font-medium', tone)}>
      {value}%
    </span>
  )
}
