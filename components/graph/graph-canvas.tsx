"use client"

import { useMemo, useRef, useState, useCallback } from "react"
import type { CanonicalEntity, GraphEdge } from "@/lib/domain/types"
import { ENTITY_META } from "@/lib/domain/types"

interface Centrality {
  degree: number
  centrality: number
  isBridge: boolean
}

interface GraphCanvasProps {
  nodes: CanonicalEntity[]
  edges: GraphEdge[]
  centrality: Record<string, Centrality>
  selectedNode?: string | null
  selectedEdge?: string | null
  pathNodeIds?: string[]
  pathEdgeIds?: string[]
  onSelectNode: (id: string | null) => void
  onSelectEdge: (id: string | null) => void
  highlightBridges?: boolean
  highlightSuspicious?: boolean
}

const VIEW_W = 1000
const VIEW_H = 680

export function GraphCanvas({
  nodes,
  edges,
  centrality,
  selectedNode,
  selectedEdge,
  pathNodeIds = [],
  pathEdgeIds = [],
  onSelectNode,
  onSelectEdge,
  highlightBridges = false,
  highlightSuspicious = false,
}: GraphCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [transform, setTransform] = useState({ x: 0, y: 0, k: 1 })
  const [hover, setHover] = useState<string | null>(null)
  const dragState = useRef<{ x: number; y: number; tx: number; ty: number } | null>(null)

  const pos = useMemo(() => {
    const m = new Map<string, { x: number; y: number }>()
    nodes.forEach((n) => m.set(n.id, { x: n.x, y: n.y }))
    return m
  }, [nodes])

  const pathNodeSet = useMemo(() => new Set(pathNodeIds), [pathNodeIds])
  const pathEdgeSet = useMemo(() => new Set(pathEdgeIds), [pathEdgeIds])
  const pathActive = pathNodeIds.length > 0

  // neighbor set for hover/selection dimming
  const activeNode = hover ?? selectedNode ?? null
  const connectedIds = useMemo(() => {
    if (!activeNode) return null
    const set = new Set<string>([activeNode])
    edges.forEach((e) => {
      if (e.source === activeNode) set.add(e.target)
      if (e.target === activeNode) set.add(e.source)
    })
    return set
  }, [activeNode, edges])

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = -e.deltaY * 0.0015
    setTransform((t) => {
      const k = Math.min(3, Math.max(0.4, t.k * (1 + delta)))
      return { ...t, k }
    })
  }, [])

  const onPointerDown = (e: React.PointerEvent) => {
    if (e.target === svgRef.current || (e.target as Element).id === "graph-bg") {
      onSelectNode(null)
      onSelectEdge(null)
    }
    dragState.current = { x: e.clientX, y: e.clientY, tx: transform.x, ty: transform.y }
    ;(e.target as Element).setPointerCapture?.(e.pointerId)
  }
  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragState.current) return
    const dx = e.clientX - dragState.current.x
    const dy = e.clientY - dragState.current.y
    const tx = dragState.current.tx
    const ty = dragState.current.ty
    setTransform((t) => ({ ...t, x: tx + dx, y: ty + dy }))
  }
  const onPointerUp = () => {
    dragState.current = null
  }

  const reset = () => setTransform({ x: 0, y: 0, k: 1 })

  return (
    <div className="relative h-full w-full overflow-hidden rounded-lg border border-border bg-[var(--graph-bg)]">
      {/* controls */}
      <div className="absolute right-3 top-3 z-10 flex flex-col gap-1">
        <button
          onClick={() => setTransform((t) => ({ ...t, k: Math.min(3, t.k * 1.2) }))}
          className="flex h-8 w-8 items-center justify-center rounded border border-border bg-card text-sm text-foreground hover:bg-secondary"
          aria-label="Zoom in"
        >
          +
        </button>
        <button
          onClick={() => setTransform((t) => ({ ...t, k: Math.max(0.4, t.k / 1.2) }))}
          className="flex h-8 w-8 items-center justify-center rounded border border-border bg-card text-sm text-foreground hover:bg-secondary"
          aria-label="Zoom out"
        >
          −
        </button>
        <button
          onClick={reset}
          className="flex h-8 w-8 items-center justify-center rounded border border-border bg-card text-[10px] font-mono text-muted-foreground hover:bg-secondary"
          aria-label="Reset view"
        >
          1:1
        </button>
      </div>

      <svg
        ref={svgRef}
        viewBox={`0 0 ${VIEW_W} ${VIEW_H}`}
        className="h-full w-full cursor-grab touch-none active:cursor-grabbing"
        onWheel={onWheel}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        <defs>
          <pattern id="grid" width="32" height="32" patternUnits="userSpaceOnUse">
            <path d="M 32 0 L 0 0 0 32" fill="none" stroke="var(--graph-grid)" strokeWidth="1" />
          </pattern>
          <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--edge-line)" />
          </marker>
        </defs>
        <rect id="graph-bg" width={VIEW_W} height={VIEW_H} fill="url(#grid)" />

        <g transform={`translate(${transform.x} ${transform.y}) scale(${transform.k})`}>
          {/* edges */}
          {edges.map((e) => {
            const s = pos.get(e.source)
            const t = pos.get(e.target)
            if (!s || !t) return null
            const onPath = pathEdgeSet.has(e.id)
            const dim =
              (pathActive && !onPath) ||
              (connectedIds !== null && !(connectedIds.has(e.source) && connectedIds.has(e.target)))
            const isSuspicious = highlightSuspicious && e.suspicious
            const selected = selectedEdge === e.id
            const mx = (s.x + t.x) / 2
            const my = (s.y + t.y) / 2
            const stroke = onPath
              ? "var(--path-line)"
              : isSuspicious
                ? "var(--warn)"
                : selected
                  ? "var(--primary)"
                  : "var(--edge-line)"
            return (
              <g key={e.id} opacity={dim ? 0.12 : 1} className="transition-opacity">
                <line
                  x1={s.x}
                  y1={s.y}
                  x2={t.x}
                  y2={t.y}
                  stroke={stroke}
                  strokeWidth={onPath ? 3 : selected ? 2.5 : 1 + Math.min(3, e.occurrences / 6)}
                  strokeDasharray={isSuspicious && !onPath ? "6 4" : undefined}
                  markerEnd="url(#arrow)"
                />
                <line
                  x1={s.x}
                  y1={s.y}
                  x2={t.x}
                  y2={t.y}
                  stroke="transparent"
                  strokeWidth={14}
                  className="cursor-pointer"
                  onClick={(ev) => {
                    ev.stopPropagation()
                    onSelectEdge(e.id)
                    onSelectNode(null)
                  }}
                />
                {(selected || onPath) && (
                  <g transform={`translate(${mx} ${my})`}>
                    <rect x={-26} y={-9} width={52} height={16} rx={3} fill="var(--card)" stroke="var(--border)" />
                    <text textAnchor="middle" y={3} fontSize={9} fill="var(--foreground)" className="font-mono">
                      {e.type}
                    </text>
                  </g>
                )}
              </g>
            )
          })}

          {/* nodes */}
          {nodes.map((n) => {
            const p = pos.get(n.id)!
            const meta = ENTITY_META[n.type]
            const c = centrality[n.id]
            const r = 12 + (c ? c.centrality * 14 : 0)
            const onPath = pathNodeSet.has(n.id)
            const dim =
              (pathActive && !onPath) || (connectedIds !== null && !connectedIds.has(n.id))
            const selected = selectedNode === n.id
            const isBridge = highlightBridges && c?.isBridge
            return (
              <g
                key={n.id}
                transform={`translate(${p.x} ${p.y})`}
                opacity={dim ? 0.18 : 1}
                className="cursor-pointer transition-opacity"
                onPointerEnter={() => setHover(n.id)}
                onPointerLeave={() => setHover(null)}
                onClick={(ev) => {
                  ev.stopPropagation()
                  onSelectNode(n.id)
                  onSelectEdge(null)
                }}
              >
                {(selected || onPath) && (
                  <circle r={r + 6} fill="none" stroke={onPath ? "var(--path-line)" : "var(--primary)"} strokeWidth={2} />
                )}
                {isBridge && (
                  <circle r={r + 3} fill="none" stroke="var(--warn)" strokeWidth={1.5} strokeDasharray="3 3" />
                )}
                <circle r={r} fill={meta.token} stroke="var(--graph-bg)" strokeWidth={2} />
                <text
                  textAnchor="middle"
                  y={3}
                  fontSize={9}
                  fontWeight={700}
                  fill="var(--graph-bg)"
                  className="font-mono pointer-events-none select-none"
                >
                  {meta.short}
                </text>
                <text
                  textAnchor="middle"
                  y={r + 14}
                  fontSize={11}
                  fill="var(--foreground)"
                  className="pointer-events-none select-none"
                >
                  {n.label.length > 20 ? n.label.slice(0, 19) + "…" : n.label}
                </text>
              </g>
            )
          })}
        </g>
      </svg>
    </div>
  )
}
