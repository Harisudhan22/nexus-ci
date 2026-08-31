'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { PlusCircle, Search, Folder, SlidersHorizontal } from 'lucide-react'
import type { Case } from '@/lib/domain/types'
import { CaseCard } from '@/components/case-card'
import { cn } from '@/lib/utils'

type CaseWithMeta = {
  c: Case
  stats: { entities: number; evidence: number; findings: number; crossCaseLinks: number }
  assignee?: string
}

const STATUS_FILTERS = ['all', 'active', 'under_review', 'cold', 'closed'] as const
const SORTS = [
  { key: 'updated', label: 'Last updated' },
  { key: 'priority', label: 'Priority' },
  { key: 'entities', label: 'Entity count' },
] as const

const PRIORITY_RANK: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1 }

export function CasesBrowser({ items }: { items: CaseWithMeta[] }) {
  const [query, setQuery] = useState('')
  const [status, setStatus] = useState<(typeof STATUS_FILTERS)[number]>('all')
  const [sort, setSort] = useState<(typeof SORTS)[number]['key']>('updated')

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    let list = items.filter((it) => {
      if (status !== 'all' && it.c.status !== status) return false
      if (!q) return true
      return (
        it.c.title.toLowerCase().includes(q) ||
        it.c.id.toLowerCase().includes(q) ||
        it.c.description.toLowerCase().includes(q)
      )
    })
    list = [...list].sort((a, b) => {
      if (sort === 'priority') return PRIORITY_RANK[b.c.priority] - PRIORITY_RANK[a.c.priority]
      if (sort === 'entities') return b.stats.entities - a.stats.entities
      return b.c.updatedAt.localeCompare(a.c.updatedAt)
    })
    return list
  }, [items, query, status, sort])

  return (
    <div className="space-y-5 p-6">
      {/* Title Bar */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-cyan-400">
            INTELLIGENCE OPERATIONS DIRECTORY
          </span>
          <h1 className="text-xl font-extrabold text-white">Cases Directory ({items.length})</h1>
          <p className="text-xs text-slate-400">
            Browse active investigations, historical cold cases, and multi-agency operations.
          </p>
        </div>

        <Link
          href="/cases/new"
          className="flex items-center gap-2 rounded-lg bg-cyan-600 px-4 py-2 text-xs font-bold text-white shadow-lg shadow-cyan-600/20 hover:bg-cyan-500 active:scale-95 transition"
        >
          <PlusCircle className="size-4" />
          + CREATE NEW CASE
        </Link>
      </div>

      {/* Filter Toolbar */}
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/90 p-3 shadow-xl">
        <div className="relative min-w-56 flex-1">
          <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search cases by title, ID, or narrative..."
            className="h-9 w-full rounded-lg border border-slate-800 bg-slate-950 pl-9 pr-3 text-xs text-white outline-none ring-cyan-500/30 focus:border-cyan-500 font-mono"
          />
        </div>

        <div className="flex items-center gap-1 rounded-lg border border-slate-800 bg-slate-950 p-1 font-mono text-xs">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={cn(
                'rounded-md px-2.5 py-1 text-[11px] font-bold capitalize transition',
                status === s ? 'bg-cyan-600 text-white shadow' : 'text-slate-400 hover:text-slate-200',
              )}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
          className="h-9 rounded-lg border border-slate-800 bg-slate-950 px-3 font-mono text-xs text-slate-200"
        >
          {SORTS.map((s) => (
            <option key={s.key} value={s.key}>
              Sort: {s.label}
            </option>
          ))}
        </select>
      </div>

      {/* Cases Grid */}
      {filtered.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 py-16 text-center bg-slate-900/50">
          <Folder className="size-8 text-slate-600 mx-auto mb-2" />
          <p className="text-xs font-mono text-slate-400">No cases match your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map(({ c, stats, assignee }) => (
            <CaseCard key={c.id} c={c} stats={stats} assignee={assignee} />
          ))}
        </div>
      )}
    </div>
  )
}
