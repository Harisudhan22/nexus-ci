'use client'

import { useState } from 'react'
import { Radar, AlertTriangle, ShieldCheck, Eye, EyeOff, CheckCircle } from 'lucide-react'
import { StatusBadge, SeverityBadge, ConfidenceMeter } from '@/components/primitives'
import { cn } from '@/lib/utils'

interface Finding {
  id: string
  caseId: string
  title: string
  category: string
  severity: 'low' | 'medium' | 'high'
  confidence: number
  why: string
  entityIds: string[]
  evidenceIds: string[]
  status: 'open' | 'acknowledged' | 'investigating' | 'dismissed'
  createdAt: string
}

export function FindingsManager({ caseId, initialFindings }: { caseId: string; initialFindings: Finding[] }) {
  const [findings, setFindings] = useState<Finding[]>(initialFindings)
  const [updatingId, setUpdatingId] = useState<string | null>(null)

  const handleStatusChange = async (findingId: string, status: Finding['status']) => {
    setUpdatingId(findingId)
    try {
      const res = await fetch(`/api/findings/${findingId}/acknowledge`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      })
      if (res.ok) {
        const updated = await res.json()
        setFindings(prev => prev.map(f => f.id === findingId ? { ...f, status: updated.status } : f))
      } else {
        alert('Failed to update finding status.')
      }
    } catch (err) {
      console.error(err)
    } finally {
      setUpdatingId(null)
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl">
      {findings.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border py-16 text-center bg-card">
          <Radar className="size-8 text-muted-foreground mx-auto mb-2 opacity-50" />
          <p className="text-sm text-muted-foreground font-medium">All graph analysis complete. No anomalous patterns flagged.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {findings.map((f) => (
            <div 
              key={f.id}
              className={cn(
                "rounded-lg border border-border bg-card p-5 space-y-4 hover:border-primary/45 transition",
                f.status === 'dismissed' && "opacity-55"
              )}
            >
              {/* Header */}
              <div className="flex items-start justify-between gap-4 border-b border-border pb-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <span className="font-mono text-[9px] uppercase tracking-wider text-muted-foreground">{f.category}</span>
                  </div>
                  <h3 className="text-sm font-bold text-foreground mt-1">{f.title}</h3>
                </div>

                <div className="flex items-center gap-4 shrink-0">
                  <div className="w-28 hidden sm:block">
                    <ConfidenceMeter value={f.confidence} />
                  </div>
                  <StatusBadge status={f.status} />
                </div>
              </div>

              {/* Rationale explanation */}
              <div className="text-sm text-foreground/90 leading-relaxed bg-surface/50 p-3 rounded border border-border">
                <span className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">Analytical Explanation</span>
                {f.why}
              </div>

              {/* Connected entities & supporting evidence list */}
              <div className="grid grid-cols-2 gap-4 text-xs pt-1">
                <div>
                  <span className="text-[9px] uppercase text-muted-foreground font-semibold block mb-1">Linked Entities</span>
                  <div className="flex flex-wrap gap-1">
                    {f.entityIds.map(eid => (
                      <span key={eid} className="px-1.5 py-0.5 rounded border border-border bg-secondary font-mono text-muted-foreground">{eid}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-[9px] uppercase text-muted-foreground font-semibold block mb-1">Supporting Evidence</span>
                  <div className="flex flex-wrap gap-1">
                    {f.evidenceIds.length === 0 ? (
                      <span className="text-muted-foreground italic">Cross-case metadata matches</span>
                    ) : (
                      f.evidenceIds.map(evid => (
                        <span key={evid} className="px-1.5 py-0.5 rounded border border-primary/20 bg-primary/5 font-mono text-primary font-bold">{evid}</span>
                      ))
                    )}
                  </div>
                </div>
              </div>

              {/* Acknowledge Actions controls */}
              <div className="flex flex-wrap gap-2 pt-3 border-t border-border/60">
                <button
                  onClick={() => handleStatusChange(f.id, 'acknowledged')}
                  disabled={updatingId !== null || f.status === 'acknowledged'}
                  className="flex items-center gap-1 h-7 px-3 text-[11px] font-bold text-success border border-success/30 bg-success/5 rounded hover:bg-success/15 disabled:opacity-50"
                >
                  <CheckCircle className="size-3.5" />
                  Acknowledge Lead
                </button>
                <button
                  onClick={() => handleStatusChange(f.id, 'investigating')}
                  disabled={updatingId !== null || f.status === 'investigating'}
                  className="flex items-center gap-1 h-7 px-3 text-[11px] font-bold text-primary border border-primary/30 bg-primary/5 rounded hover:bg-primary/15 disabled:opacity-50"
                >
                  <Eye className="size-3.5" />
                  Investigate
                </button>
                <button
                  onClick={() => handleStatusChange(f.id, 'dismissed')}
                  disabled={updatingId !== null || f.status === 'dismissed'}
                  className="flex items-center gap-1 h-7 px-3 text-[11px] font-bold text-muted-foreground border border-border bg-secondary/50 rounded hover:bg-secondary/100 disabled:opacity-50"
                >
                  <EyeOff className="size-3.5" />
                  Dismiss
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="mt-8 text-[10px] text-muted-foreground italic leading-normal text-center border-t border-border/40 pt-4">
        Disclaimer: Investigative findings are generated from evidence linkages and relationship weights computed via database rules and network centrality analysis. They represent analytical signals to guide human investigator reviews and do not constitute proof of guilt or criminality.
      </div>
    </div>
  )
}
