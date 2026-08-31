import Link from 'next/link'
import { FileStack, Layers, Radar, Users, ArrowUpRight, FolderGit, Lock } from 'lucide-react'
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
      className="group flex flex-col justify-between rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl transition-all duration-200 hover:border-cyan-500/50 hover:bg-slate-900 hover:shadow-cyan-500/10"
    >
      <div>
        <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 pb-3 mb-3">
          <div>
            <div className="flex items-center gap-1.5 font-mono text-[10px] font-bold text-cyan-400">
              <FolderGit className="size-3.5" />
              <span>{c.id}</span>
              <span className="text-slate-600">|</span>
              <span className="text-amber-400">{c.classification || 'SECRET'}</span>
            </div>
            <h3 className="mt-1 text-sm font-extrabold text-white group-hover:text-cyan-300 transition line-clamp-1">
              {c.title}
            </h3>
          </div>
          <SeverityBadge severity={c.priority} />
        </div>

        <p className="line-clamp-2 text-xs text-slate-300 leading-relaxed font-sans">
          {c.description}
        </p>
      </div>

      <div>
        <div className="mt-4 grid grid-cols-4 gap-2 rounded-lg bg-slate-950 p-2.5 border border-slate-800 font-mono">
          {[
            { icon: Users, value: stats.entities, label: 'Entities', color: 'text-emerald-400' },
            { icon: FileStack, value: stats.evidence, label: 'Evidence', color: 'text-cyan-400' },
            { icon: Radar, value: stats.findings, label: 'Findings', color: 'text-amber-400' },
            { icon: Layers, value: stats.crossCaseLinks, label: 'Links', color: 'text-rose-400' },
          ].map(({ icon: Icon, value, label, color }) => (
            <div key={label} className="flex flex-col items-center text-center">
              <Icon className={`size-3.5 ${color}`} />
              <span className="text-xs font-extrabold text-white mt-0.5">{value}</span>
              <span className="text-[9px] text-slate-400">{label}</span>
            </div>
          ))}
        </div>

        <div className="mt-3 flex items-center justify-between font-mono text-[10px]">
          <StatusBadge status={c.status} />
          <span className="text-slate-400 font-bold flex items-center gap-1">
            {assignee ?? c.agency} <ArrowUpRight className="size-3 text-cyan-400 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition" />
          </span>
        </div>
      </div>
    </Link>
  )
}
