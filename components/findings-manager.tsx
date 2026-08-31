'use client'

import { useState } from 'react'
import { Radar, AlertTriangle, ShieldCheck, Eye, EyeOff, CheckCircle, GitMerge, Sparkles, ArrowRight } from 'lucide-react'
import { StatusBadge, SeverityBadge, ConfidenceMeter } from '@/components/primitives'
import { cn } from '@/lib/utils'
import Link from 'next/link'

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
        body: JSON.stringify({ status }),
      })
      if (res.ok) {
        const updated = await res.json()
        setFindings((prev) => prev.map((f) => (f.id === findingId ? { ...f, status: updated.status } : f)))
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
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      {/* Title Header Console */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-rose-500/30 bg-rose-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-rose-400">
            ANALYTICAL SIGNAL TRIAGE WORKSPACE
          </span>
          <h1 className="text-xl font-extrabold text-white">Pattern Engine Findings & Anomalies</h1>
          <p className="text-xs text-slate-400">
            Automated graph analytics detections requiring human officer review and validation.
          </p>
        </div>
      </div>

      {findings.length === 0 ? (
        <div className="rounded-xl border border-dashed border-slate-800 py-16 text-center bg-slate-900/50">
          <Radar className="size-8 text-slate-600 mx-auto mb-2 opacity-50" />
          <p className="text-xs font-mono text-slate-400">No anomalous patterns flagged for this investigation.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {findings.map((f) => (
            <div
              key={f.id}
              className={cn(
                'rounded-xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 shadow-xl hover:border-slate-700 transition',
                f.status === 'dismissed' && 'opacity-50',
              )}
            >
              {/* Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={f.severity} />
                    <span className="font-mono text-[10px] font-bold text-cyan-400 uppercase tracking-wider">{f.category}</span>
                  </div>
                  <h3 className="text-base font-extrabold text-white">{f.title}</h3>
                </div>

                <div className="flex items-center gap-4 shrink-0 font-mono">
                  <div className="w-28 hidden sm:block">
                    <ConfidenceMeter value={f.confidence} />
                  </div>
                  <StatusBadge status={f.status} />
                </div>
              </div>

              {/* Rationale explanation */}
              <div className="text-xs text-slate-200 leading-relaxed bg-slate-950 p-3.5 rounded-lg border border-slate-800 font-mono space-y-1">
                <span className="text-[10px] font-bold text-slate-400 uppercase block">ANALYTICAL EXPLANATION & EVIDENCE RATIONALE</span>
                <p>{f.why}</p>
              </div>

              {/* Connected entities & supporting evidence list */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">LINKED ENTITIES</span>
                  <div className="flex flex-wrap gap-1.5">
                    {f.entityIds.map((eid) => (
                      <span key={eid} className="px-2 py-0.5 rounded border border-slate-800 bg-slate-950 text-emerald-400 font-bold">
                        {eid}
                      </span>
                    ))}
                  </div>
                </div>

                <div>
                  <span className="text-[10px] font-bold text-slate-400 uppercase block mb-1">SUPPORTING EVIDENCE CITATIONS</span>
                  <div className="flex flex-wrap gap-1.5">
                    {f.evidenceIds.map((evid) => (
                      <span key={evid} className="px-2 py-0.5 rounded border border-slate-800 bg-slate-950 text-cyan-400 font-bold">
                        {evid}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-800 flex items-center justify-between font-mono text-xs">
                <Link
                  href={`/cases/${caseId}/network`}
                  className="flex items-center gap-1.5 text-cyan-400 font-bold hover:underline"
                >
                  <GitMerge className="size-3.5" /> View Connected Subgraph <ArrowRight className="size-3" />
                </Link>

                <div className="flex items-center gap-2">
                  {f.status !== 'acknowledged' && (
                    <button
                      onClick={() => handleStatusChange(f.id, 'acknowledged')}
                      disabled={updatingId === f.id}
                      className="px-3 py-1.5 rounded-lg bg-emerald-600 text-white font-bold text-[11px] shadow hover:bg-emerald-500 active:scale-95 transition disabled:opacity-50"
                    >
                      Acknowledge Finding
                    </button>
                  )}

                  {f.status !== 'dismissed' && (
                    <button
                      onClick={() => handleStatusChange(f.id, 'dismissed')}
                      disabled={updatingId === f.id}
                      className="px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950 text-slate-400 font-bold text-[11px] hover:text-white transition disabled:opacity-50"
                    >
                      Dismiss
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
