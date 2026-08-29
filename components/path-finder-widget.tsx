'use client'

import { useState } from 'react'
import { Route, Play, ArrowRight, ShieldCheck, AlertCircle, HelpCircle } from 'lucide-react'
import { ConfidenceMeter, EntityBadge } from '@/components/primitives'
import { cn } from '@/lib/utils'

interface Entity {
  id: string
  label: string
  type: string
}

interface PathEdge {
  id: string
  source: string
  target: string
  type: string
  confidence: number
  occurrences: number
  evidenceIds: string[]
  createdByPipeline: string
  rationale: string
}

export function PathFinderWidget({ caseId, entities }: { caseId: string; entities: Entity[] }) {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [mode, setMode] = useState<'shortest' | 'strongest'>('shortest')
  const [loading, setLoading] = useState(false)
  const [pathResult, setPathResult] = useState<{ nodeIds: string[]; edges: PathEdge[]; totalConfidence: number; hops: number } | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSearch = async () => {
    if (!from || !to) return
    setLoading(true)
    setError(null)
    setPathResult(null)

    try {
      const res = await fetch(`/api/paths?from=${from}&to=${to}&case_id=${caseId}&mode=${mode}`)
      if (res.ok) {
        const data = await res.json()
        setPathResult(data)
      } else {
        const err = await res.json().catch(() => ({}))
        setError(err.detail || 'No connection found between entities.')
      }
    } catch {
      setError('Connection search timed out. Ensure the backend services are reachable.')
    } finally {
      setLoading(false)
    }
  }

  // Lookup labels
  const getEntityLabel = (id: string) => {
    const ent = entities.find(e => e.id === id)
    return ent ? `${ent.label} (${ent.type})` : id
  }

  const getEntityType = (id: string) => {
    const ent = entities.find(e => e.id === id)
    return ent ? ent.type : 'person'
  }

  return (
    <section className="rounded-lg border border-border bg-card p-6 space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Source Dropdown */}
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Source Entity</label>
          <select
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="h-9 w-full rounded-md border border-input bg-surface px-3 text-xs outline-none focus:border-primary/60"
          >
            <option value="">Choose entity...</option>
            {entities.map(e => <option key={e.id} value={e.id}>{e.label} ({e.type})</option>)}
          </select>
        </div>

        {/* Target Dropdown */}
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Target Entity</label>
          <select
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="h-9 w-full rounded-md border border-input bg-surface px-3 text-xs outline-none focus:border-primary/60"
          >
            <option value="">Choose target...</option>
            {entities.map(e => <option key={e.id} value={e.id}>{e.label} ({e.type})</option>)}
          </select>
        </div>

        {/* Strategy Selector */}
        <div>
          <label className="block text-xs text-muted-foreground mb-1">Analytical Strategy</label>
          <div className="flex gap-2 rounded-md border border-border p-0.5 bg-surface h-9">
            <button
              onClick={() => setMode('shortest')}
              className={cn(
                "flex-1 text-xs rounded font-semibold transition",
                mode === 'shortest' ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Shortest Hops
            </button>
            <button
              onClick={() => setMode('strongest')}
              className={cn(
                "flex-1 text-xs rounded font-semibold transition",
                mode === 'strongest' ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
              )}
            >
              Strongest Evidence
            </button>
          </div>
        </div>
      </div>

      <button
        onClick={handleSearch}
        disabled={loading || !from || !to}
        className="w-full h-9 flex items-center justify-center gap-1.5 rounded-md bg-primary text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50"
      >
        {loading ? 'Running Dijkstra Routing Algorithms...' : 'Locate Evidence Route'}
      </button>

      {error && (
        <div className="flex items-start gap-2.5 p-3 rounded-md bg-danger/10 border border-danger/30 text-danger text-sm">
          <AlertCircle className="size-4 shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {pathResult && (
        <div className="space-y-6 pt-4 border-t border-border">
          {/* Path Header Stats */}
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 rounded-lg bg-secondary/20 border border-border">
            <div>
              <p className="text-xs text-muted-foreground">Path Strength Evaluation</p>
              <h4 className="text-sm font-bold text-success flex items-center gap-1.5 mt-0.5">
                <ShieldCheck className="size-4" /> Connection Established
              </h4>
            </div>
            <div className="flex items-center gap-6 text-xs font-mono">
              <div>
                <span className="text-muted-foreground block text-[9px] uppercase">Route Length</span>
                <span className="text-sm font-semibold text-foreground">{pathResult.hops} Hops</span>
              </div>
              <div className="w-28">
                <span className="text-muted-foreground block text-[9px] uppercase mb-0.5">Confidence Avg</span>
                <ConfidenceMeter value={pathResult.totalConfidence} />
              </div>
            </div>
          </div>

          {/* Path Step-by-Step Flow */}
          <div className="space-y-4">
            <span className="text-[10px] font-bold text-muted-foreground uppercase block">Connection Sequence Details</span>
            <div className="space-y-3 pl-3 border-l-2 border-primary/20">
              {pathResult.edges.map((edge, idx) => (
                <div key={edge.id} className="relative space-y-2 pb-2 border-b border-border/40 last:border-b-0">
                  {/* Visual Node Pin */}
                  <div className="absolute -left-[20px] top-1.5 size-2 rounded-full bg-primary" />

                  {/* Flow Direction display */}
                  <div className="flex items-center gap-2 text-xs font-bold">
                    <EntityBadge type={getEntityType(edge.source)} label={getEntityLabel(edge.source)} />
                    <ArrowRight className="size-3.5 text-muted-foreground shrink-0" />
                    <EntityBadge type={getEntityType(edge.target)} label={getEntityLabel(edge.target)} />
                  </div>

                  {/* Edge properties */}
                  <div className="rounded border border-border bg-surface/40 p-3 space-y-2">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="font-mono font-bold text-warning uppercase">Relationship: {edge.type}</span>
                      <span className="text-muted-foreground">Confidence: {edge.confidence}%</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-normal">{edge.rationale}</p>
                    <div className="flex items-center justify-between text-[10px] text-muted-foreground pt-1.5 border-t border-border/40 font-mono">
                      <span>Citations: {edge.evidenceIds.join(', ')}</span>
                      <span>Source: {edge.createdByPipeline}</span>
                    </div>
                  </div>
                </div>
              ))}
              
              {/* Final Node display */}
              <div className="relative pt-1">
                <div className="absolute -left-[20px] top-2.5 size-2.5 rounded-full bg-success" />
                <div className="text-xs font-bold flex items-center gap-1.5">
                  Target Entity Reached:
                  <EntityBadge type={getEntityType(to)} label={getEntityLabel(to)} />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
