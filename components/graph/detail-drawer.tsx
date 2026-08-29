"use client"

import type { CanonicalEntity, GraphEdge, Evidence } from "@/lib/domain/types"
import { ENTITY_META, RELATIONSHIP_LABELS } from "@/lib/domain/types"
import { Meter, RelevanceBadge, StatCell } from "@/components/primitives"
import { X, FileText, ArrowRight, AlertTriangle, ScanSearch } from "lucide-react"

interface EntityDrawerProps {
  entity: CanonicalEntity
  centrality?: { degree: number; centrality: number; isBridge: boolean }
  evidence: Evidence[]
  connections: { edge: GraphEdge; other: CanonicalEntity }[]
  onClose: () => void
  onSelectEntity: (id: string) => void
  onOpenEvidence: (id: string) => void
  onPathFrom: (id: string) => void
}

export function EntityDrawer({
  entity,
  centrality,
  evidence,
  connections,
  onClose,
  onSelectEntity,
  onOpenEvidence,
  onPathFrom,
}: EntityDrawerProps) {
  const meta = ENTITY_META[entity.type]
  return (
    <DrawerShell onClose={onClose}>
      <div className="flex items-start gap-3">
        <span
          className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-md font-mono text-[10px] font-bold text-[var(--graph-bg)]"
          style={{ background: meta.token }}
        >
          {meta.short}
        </span>
        <div className="min-w-0 flex-1">
          <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{meta.label}</div>
          <h3 className="text-pretty text-base font-semibold text-foreground">{entity.label}</h3>
          {entity.subtitle && <p className="text-sm text-muted-foreground">{entity.subtitle}</p>}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-3 gap-px overflow-hidden rounded-md border border-border bg-border">
        <StatCell label="Relevance" value={`${entity.relevance}`} />
        <StatCell label="Degree" value={`${centrality?.degree ?? 0}`} />
        <StatCell label="Centrality" value={`${Math.round((centrality?.centrality ?? 0) * 100)}%`} />
      </div>

      {centrality?.isBridge && (
        <div className="mt-3 flex items-start gap-2 rounded-md border border-[var(--warn)]/40 bg-[var(--warn)]/10 p-3 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--warn)]" />
          <p className="text-foreground/90">
            Acts as a <strong>bridge</strong> across otherwise separate clusters. Removing it would
            fragment the network — a candidate for prioritized review.
          </p>
        </div>
      )}

      {entity.aliases.length > 0 && (
        <Section title="Aliases / Surface forms">
          <div className="flex flex-wrap gap-1.5">
            {entity.aliases.map((a) => (
              <span key={a} className="rounded border border-border bg-secondary px-2 py-0.5 font-mono text-xs text-secondary-foreground">
                {a}
              </span>
            ))}
          </div>
        </Section>
      )}

      <Section title="Attributes">
        <dl className="grid grid-cols-1 gap-1.5">
          {Object.entries(entity.attributes).map(([k, v]) => (
            <div key={k} className="flex items-baseline justify-between gap-3 text-sm">
              <dt className="shrink-0 text-muted-foreground">{k}</dt>
              <dd className="text-right font-mono text-foreground">{v}</dd>
            </div>
          ))}
        </dl>
      </Section>

      <Section title={`Connections (${connections.length})`}>
        <ul className="flex flex-col gap-1">
          {connections.map(({ edge, other }) => (
            <li key={edge.id}>
              <button
                onClick={() => onSelectEntity(other.id)}
                className="group flex w-full items-center justify-between gap-2 rounded-md border border-border bg-card px-2.5 py-2 text-left hover:border-primary/50 hover:bg-secondary"
              >
                <span className="flex items-center gap-2 truncate">
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ background: ENTITY_META[other.type].token }}
                  />
                  <span className="truncate text-sm text-foreground">{other.label}</span>
                </span>
                <span className="flex shrink-0 items-center gap-1 font-mono text-[10px] uppercase text-muted-foreground">
                  {edge.suspicious && <AlertTriangle className="h-3 w-3 text-[var(--warn)]" />}
                  {RELATIONSHIP_LABELS[edge.type]}
                  <ArrowRight className="h-3 w-3 opacity-0 transition-opacity group-hover:opacity-100" />
                </span>
              </button>
            </li>
          ))}
        </ul>
      </Section>

      {evidence.length > 0 && (
        <Section title={`Appears in evidence (${evidence.length})`}>
          <ul className="flex flex-col gap-1">
            {evidence.map((ev) => (
              <li key={ev.id}>
                <button
                  onClick={() => onOpenEvidence(ev.id)}
                  className="flex w-full items-center gap-2 rounded-md border border-border bg-card px-2.5 py-2 text-left hover:border-primary/50 hover:bg-secondary"
                >
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate text-sm text-foreground">{ev.title}</span>
                  <span className="ml-auto shrink-0 font-mono text-[10px] text-muted-foreground">{ev.sourceType}</span>
                </button>
              </li>
            ))}
          </ul>
        </Section>
      )}

      <button
        onClick={() => onPathFrom(entity.id)}
        className="mt-5 flex w-full items-center justify-center gap-2 rounded-md border border-primary/40 bg-primary/10 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/20"
      >
        <ScanSearch className="h-4 w-4" />
        Find path from this entity
      </button>
    </DrawerShell>
  )
}

interface EdgeDrawerProps {
  edge: GraphEdge
  source: CanonicalEntity
  target: CanonicalEntity
  evidence: Evidence[]
  onClose: () => void
  onSelectEntity: (id: string) => void
  onOpenEvidence: (id: string) => void
}

export function EdgeDrawer({
  edge,
  source,
  target,
  evidence,
  onClose,
  onSelectEntity,
  onOpenEvidence,
}: EdgeDrawerProps) {
  return (
    <DrawerShell onClose={onClose}>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">Relationship</div>
      <h3 className="mt-0.5 flex items-center gap-2 text-base font-semibold text-foreground">
        {RELATIONSHIP_LABELS[edge.type]}
        {edge.suspicious && (
          <span className="flex items-center gap-1 rounded border border-[var(--warn)]/40 bg-[var(--warn)]/10 px-1.5 py-0.5 text-[10px] font-medium text-[var(--warn)]">
            <AlertTriangle className="h-3 w-3" /> Flagged
          </span>
        )}
      </h3>

      <div className="mt-3 flex items-center gap-2 rounded-md border border-border bg-card p-2.5">
        <EntityPill entity={source} onClick={() => onSelectEntity(source.id)} />
        <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground" />
        <EntityPill entity={target} onClick={() => onSelectEntity(target.id)} />
      </div>

      <div className="mt-4">
        <Meter label="Confidence" value={edge.confidence} />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-px overflow-hidden rounded-md border border-border bg-border">
        <StatCell label="Occurrences" value={`${edge.occurrences}`} />
        <StatCell label="Pipeline" value={edge.createdByPipeline} mono />
      </div>

      <Section title="Timeframe">
        <p className="font-mono text-sm text-foreground">
          {edge.timeframe.from} → {edge.timeframe.to}
        </p>
      </Section>

      <Section title="Why this exists">
        <p className="text-pretty text-sm leading-relaxed text-foreground/90">{edge.rationale}</p>
      </Section>

      {evidence.length > 0 && (
        <Section title={`Supporting evidence (${evidence.length})`}>
          <ul className="flex flex-col gap-1">
            {evidence.map((ev) => (
              <li key={ev.id}>
                <button
                  onClick={() => onOpenEvidence(ev.id)}
                  className="flex w-full items-center gap-2 rounded-md border border-border bg-card px-2.5 py-2 text-left hover:border-primary/50 hover:bg-secondary"
                >
                  <FileText className="h-4 w-4 shrink-0 text-muted-foreground" />
                  <span className="truncate text-sm text-foreground">{ev.title}</span>
                  <span className="ml-auto shrink-0"><RelevanceBadge value={ev.relevance} /></span>
                </button>
              </li>
            ))}
          </ul>
        </Section>
      )}
    </DrawerShell>
  )
}

function EntityPill({ entity, onClick }: { entity: CanonicalEntity; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="flex min-w-0 flex-1 items-center gap-2 rounded px-1.5 py-1 text-left hover:bg-secondary"
    >
      <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: ENTITY_META[entity.type].token }} />
      <span className="truncate text-sm font-medium text-foreground">{entity.label}</span>
    </button>
  )
}

function DrawerShell({ children, onClose }: { children: React.ReactNode; onClose: () => void }) {
  return (
    <aside className="flex h-full w-full flex-col overflow-y-auto border-l border-border bg-card p-4">
      <button
        onClick={onClose}
        className="mb-3 ml-auto flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground"
        aria-label="Close panel"
      >
        <X className="h-4 w-4" />
      </button>
      {children}
    </aside>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-5">
      <h4 className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">{title}</h4>
      {children}
    </section>
  )
}
