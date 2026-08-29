import Link from 'next/link'
import { FileStack, Layers, Radar, Users } from 'lucide-react'
import type { Case } from '@/lib/domain/types'
import { SeverityBadge, StatusBadge } from '@/components/primitives'

export function CaseCard({
  c,
  stats,
  assignee,
}: {
  c: Case
  stats: { entities: number; evidence: number; findings: number; crossCaseLinks: number }
  assignee?: string
}) {
  return (
    <Link
      href={`/cases/${c.id}/overview`}
      className="group flex flex-col rounded-lg border border-border bg-card p-5 transition hover:border-primary/50 hover:bg-secondary/30"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="font-mono text-[11px] uppercase tracking-wider text-primary">{c.id}</p>
          <h3 className="mt-1 text-pretty text-sm font-semibold leading-snug group-hover:text-primary">
            {c.title}
          </h3>
        </div>
        <SeverityBadge severity={c.priority} />
      </div>

      <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-muted-foreground">
        {c.description}
      </p>

      <div className="mt-4 grid grid-cols-4 gap-2 border-t border-border pt-4">
        {[
          { icon: Users, value: stats.entities, label: 'Entities' },
          { icon: FileStack, value: stats.evidence, label: 'Evidence' },
          { icon: Radar, value: stats.findings, label: 'Findings' },
          { icon: Layers, value: stats.crossCaseLinks, label: 'Links' },
        ].map(({ icon: Icon, value, label }) => (
          <div key={label} className="flex flex-col items-center gap-1 text-center">
            <Icon className="size-3.5 text-muted-foreground" />
            <span className="tabular text-sm font-semibold">{value}</span>
            <span className="text-[10px] text-muted-foreground">{label}</span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex items-center justify-between">
        <StatusBadge status={c.status} />
        <span className="text-[11px] text-muted-foreground">{assignee ?? c.agency}</span>
      </div>
    </Link>
  )
}
