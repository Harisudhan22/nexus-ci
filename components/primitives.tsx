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
  const tone = value >= 80 ? 'var(--success)' : value >= 60 ? 'var(--warning)' : 'var(--muted-foreground)'
  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular font-medium text-foreground">{value}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full transition-all"
          style={{ width: `${Math.min(100, Math.max(0, value))}%`, background: tone }}
        />
      </div>
    </div>
  )
}

// ---------- Severity / status badges ----------
const SEVERITY_TONE: Record<string, string> = {
  high: 'border-danger/40 bg-danger/10 text-danger',
  critical: 'border-danger/40 bg-danger/10 text-danger',
  medium: 'border-warning/40 bg-warning/10 text-warning',
  low: 'border-border bg-muted text-muted-foreground',
}

export function SeverityBadge({ severity }: { severity: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-[11px] font-medium capitalize',
        SEVERITY_TONE[severity] ?? SEVERITY_TONE.low,
      )}
    >
      {severity}
    </span>
  )
}

const STATUS_TONE: Record<string, string> = {
  active: 'border-success/40 bg-success/10 text-success',
  processed: 'border-success/40 bg-success/10 text-success',
  success: 'border-success/40 bg-success/10 text-success',
  open: 'border-warning/40 bg-warning/10 text-warning',
  processing: 'border-info/40 bg-info/10 text-info',
  under_review: 'border-warning/40 bg-warning/10 text-warning',
  investigating: 'border-info/40 bg-info/10 text-info',
  acknowledged: 'border-border bg-muted text-muted-foreground',
  cold: 'border-border bg-muted text-muted-foreground',
  closed: 'border-border bg-muted text-muted-foreground',
  dismissed: 'border-border bg-muted text-muted-foreground',
  failed: 'border-danger/40 bg-danger/10 text-danger',
  denied: 'border-danger/40 bg-danger/10 text-danger',
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium capitalize',
        STATUS_TONE[status] ?? 'border-border bg-muted text-muted-foreground',
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
  const meta = ENTITY_META[type]
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium',
        className,
      )}
      style={{
        borderColor: `color-mix(in oklch, ${meta.token} 40%, transparent)`,
        background: `color-mix(in oklch, ${meta.token} 12%, transparent)`,
        color: meta.token,
      }}
    >
      <span className="size-2 rounded-[3px]" style={{ background: meta.token }} />
      {label ?? meta.label}
    </span>
  )
}

// ---------- Section header ----------
export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
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
  const toneClass =
    tone === 'danger'
      ? 'text-danger'
      : tone === 'warning'
        ? 'text-warning'
        : tone === 'success'
          ? 'text-success'
          : 'text-primary'
  return (
    <div className="flex flex-col justify-between rounded-lg border border-border bg-card p-4">
      <div className="flex items-start justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        {icon ? <span className={cn('shrink-0', toneClass)}>{icon}</span> : null}
      </div>
      <div className="mt-3">
        <p className="tabular text-2xl font-semibold tracking-tight">{value}</p>
        {hint ? <p className="mt-0.5 text-[11px] text-muted-foreground">{hint}</p> : null}
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
    <div className="flex flex-col bg-card p-3 text-center">
      <span className="text-[10px] uppercase text-muted-foreground">{label}</span>
      <span className={cn('mt-0.5 text-sm font-semibold', mono && 'font-mono')}>{value}</span>
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
      ? 'border-success/40 bg-success/10 text-success'
      : value >= 50
        ? 'border-warning/40 bg-warning/10 text-warning'
        : 'border-border bg-muted text-muted-foreground'
  return (
    <span className={cn('inline-flex items-center rounded-md border px-2 py-0.5 text-[10px] font-mono font-medium', tone)}>
      {value}%
    </span>
  )
}

