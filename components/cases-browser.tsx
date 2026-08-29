'use client'

import { useMemo, useState } from 'react'
import { Search } from 'lucide-react'
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search cases by title, ID, or description"
            className="h-9 w-full rounded-md border border-input bg-surface pl-9 pr-3 text-sm outline-none ring-ring/40 transition focus:border-primary/60 focus:ring-2"
          />
        </div>

        <div className="flex items-center gap-1 rounded-md border border-border bg-surface p-0.5">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setStatus(s)}
              className={cn(
                'rounded px-2.5 py-1 text-xs font-medium capitalize transition',
                status === s ? 'bg-primary text-primary-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value as typeof sort)}
          className="h-9 rounded-md border border-input bg-surface px-3 text-xs text-foreground outline-none focus:border-primary/60"
        >
          {SORTS.map((s) => (
            <option key={s.key} value={s.key}>
              Sort: {s.label}
            </option>
          ))}
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border py-16 text-center">
          <p className="text-sm text-muted-foreground">No cases match your filters.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((it) => (
            <CaseCard key={it.c.id} c={it.c} stats={it.stats} assignee={it.assignee} />
          ))}
        </div>
      )}
    </div>
  )
}
