'use client'

import { useState } from 'react'
import { Check, X, Users, AlertTriangle, Layers, GitMerge, FileSearch, ArrowRight } from 'lucide-react'
import { EntityBadge, ConfidenceMeter } from '@/components/primitives'
import { cn } from '@/lib/utils'

interface Entity {
  id: string
  type: string
  label: string
  subtitle?: string
  caseIds: string[]
  aliases: string[]
  relevance: number
  attributes: Record<string, string>
}

interface ResolutionCandidate {
  id: string
  caseId: string
  canonicalId: string
  canonicalLabel: string
  type: string
  mentions: string[]
  confidence: number
  signals: { label: string; matched: boolean }[]
  status: string
}

export function EntitiesResolver({
  caseId,
  initialEntities,
  initialCandidates
}: {
  caseId: string
  initialEntities: Entity[]
  initialCandidates: ResolutionCandidate[]
}) {
  const [entities, setEntities] = useState<Entity[]>(initialEntities)
  const [candidates, setCandidates] = useState<ResolutionCandidate[]>(initialCandidates)
  const [activeTab, setActiveTab] = useState<'resolved' | 'pending'>('resolved')
  const [busyCandidate, setBusyCandidate] = useState<string | null>(null)

  const handleDecision = async (candidateId: string, decision: 'accepted' | 'rejected') => {
    setBusyCandidate(candidateId)
    try {
      const res = await fetch(`/api/entity-resolution/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ candidate_id: candidateId, decision })
      })
      
      if (res.ok) {
        // Remove candidate from list
        setCandidates(prev => prev.filter(c => c.id !== candidateId))
        
        // Refresh entities if accepted
        if (decision === 'accepted') {
          const entsRes = await fetch(`/api/cases/${caseId}/entities`)
          if (entsRes.ok) {
            const freshEnts = await entsRes.json()
            setEntities(freshEnts)
          }
        }
      } else {
        alert('Failed to submit resolution decision.')
      }
    } catch (err) {
      console.error(err)
    } finally {
      setBusyCandidate(null)
    }
  }

  return (
    <div className="p-6 space-y-6">
      {/* Navigation tabs */}
      <div className="flex gap-2 border-b border-border pb-3">
        <button
          onClick={() => setActiveTab('resolved')}
          className={cn(
            "flex items-center gap-1.5 h-8 px-4 text-xs font-semibold rounded-md transition",
            activeTab === 'resolved' 
              ? "bg-primary text-primary-foreground" 
              : "text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
          )}
        >
          <Users className="size-3.5" />
          Resolved Entities ({entities.length})
        </button>
        <button
          onClick={() => setActiveTab('pending')}
          className={cn(
            "flex items-center gap-1.5 h-8 px-4 text-xs font-semibold rounded-md transition",
            activeTab === 'pending' 
              ? "bg-warning/15 border border-warning/30 text-warning" 
              : "text-muted-foreground hover:bg-secondary/40 hover:text-foreground"
          )}
        >
          <GitMerge className="size-3.5" />
          Pending Merges ({candidates.length})
        </button>
      </div>

      {activeTab === 'resolved' ? (
        <section className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
            {entities.map((ent) => (
              <div 
                key={ent.id}
                className="rounded-lg border border-border bg-card p-5 flex flex-col justify-between hover:border-primary/50 transition"
              >
                <div>
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <EntityBadge type={ent.type} />
                    <span className="text-[10px] font-mono opacity-65">{ent.id}</span>
                  </div>
                  <h3 className="text-sm font-semibold">{ent.label}</h3>
                  {ent.subtitle && <p className="text-xs text-muted-foreground">{ent.subtitle}</p>}

                  {ent.aliases.length > 1 && (
                    <div className="mt-3 space-y-1">
                      <span className="text-[9px] uppercase tracking-wider text-muted-foreground block">Merged Mentions</span>
                      <div className="flex flex-wrap gap-1">
                        {ent.aliases.map(a => (
                          <span key={a} className="px-1.5 py-0.5 text-[9px] rounded bg-secondary font-mono text-muted-foreground border border-border">{a}</span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-border flex items-center justify-between text-[11px] text-muted-foreground">
                  <span>Relevance: {ent.relevance}%</span>
                  <span className="flex items-center gap-1">
                    <Layers className="size-3 text-muted-foreground" />
                    {ent.caseIds.length} Case{ent.caseIds.length === 1 ? '' : 's'}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : (
        <section className="space-y-4">
          {candidates.length === 0 ? (
            <div className="rounded-lg border border-dashed border-border py-16 text-center bg-card">
              <GitMerge className="size-8 text-muted-foreground mx-auto mb-2 opacity-50" />
              <p className="text-sm text-muted-foreground">All duplicate entity references resolved. No pending reviews.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {candidates.map((cand) => (
                <div 
                  key={cand.id}
                  className="rounded-lg border border-border bg-card p-5 space-y-4 hover:border-warning/50 transition flex flex-col justify-between"
                >
                  <div>
                    {/* Header */}
                    <div className="flex items-start justify-between border-b border-border pb-3">
                      <div>
                        <span className="text-[10px] font-mono text-warning uppercase">Merge Candidate</span>
                        <h4 className="text-sm font-bold mt-1 flex items-center gap-2">
                          <EntityBadge type={cand.type} label={cand.mentions[0]} />
                          <ArrowRight className="size-3 text-muted-foreground" />
                          <EntityBadge type={cand.type} label={cand.canonicalLabel} />
                        </h4>
                      </div>
                      <div className="w-24 shrink-0">
                        <ConfidenceMeter value={cand.confidence} />
                      </div>
                    </div>

                    {/* Signals Grid */}
                    <div className="grid grid-cols-2 gap-2 mt-4">
                      {cand.signals.map((sig) => (
                        <div 
                          key={sig.label} 
                          className={cn(
                            "flex items-center gap-2 p-1.5 rounded border text-xs font-semibold",
                            sig.matched 
                              ? "bg-success/5 border-success/20 text-success" 
                              : "bg-secondary/20 border-border text-muted-foreground opacity-60"
                          )}
                        >
                          <span className="size-1.5 rounded-full bg-current" />
                          {sig.label}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Actions Button */}
                  <div className="flex gap-2 pt-3 border-t border-border">
                    <button
                      onClick={() => handleDecision(cand.id, 'accepted')}
                      disabled={busyCandidate !== null}
                      className="flex-1 flex h-8 items-center justify-center gap-1.5 rounded bg-success text-success-foreground text-xs font-bold hover:opacity-90 disabled:opacity-50"
                    >
                      <Check className="size-4" />
                      Approve Merge
                    </button>
                    <button
                      onClick={() => handleDecision(cand.id, 'rejected')}
                      disabled={busyCandidate !== null}
                      className="flex-1 flex h-8 items-center justify-center gap-1.5 rounded bg-secondary text-foreground text-xs font-bold hover:bg-secondary/70 disabled:opacity-50"
                    >
                      <X className="size-4" />
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      )}
      <div className="mt-8 text-[10px] text-muted-foreground italic leading-normal text-center border-t border-border/40 pt-4">
        Disclaimer: This registry lists resolved entity profile associations based on analytical matching confidence algorithms. These listings represent investigative leads and priority signals, not a final determination of guilt or criminality.
      </div>
    </div>
  )
}
