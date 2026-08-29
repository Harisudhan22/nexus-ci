'use client'

import { useState, useEffect } from 'react'
import { GraphCanvas } from '@/components/graph/graph-canvas'
import { EntityDrawer, EdgeDrawer } from '@/components/graph/detail-drawer'
import { GitBranch, Sliders, Play, Route, ShieldAlert, AlertCircle, RefreshCw } from 'lucide-react'
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
  cluster: string
  x: number
  y: number
}

interface Edge {
  id: string
  source: string
  target: string
  type: string
  confidence: number
  occurrences: number
  timeframe: { from: string; to: string }
  evidenceIds: string[]
  createdByPipeline: string
  suspicious?: boolean
  rationale: string
}

export function NetworkViewer({ caseId }: { caseId: string }) {
  // Graph state
  const [nodes, setNodes] = useState<Entity[]>([])
  const [edges, setEdges] = useState<Edge[]>([])
  const [centrality, setCentrality] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)

  // Filters
  const [entityType, setEntityType] = useState('')
  const [relationshipType, setRelationshipType] = useState('')
  const [minConfidence, setMinConfidence] = useState(0)
  const [suspiciousOnly, setSuspiciousOnly] = useState(false)
  const [highlightBridges, setHighlightBridges] = useState(false)

  // Selected item drawers
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)

  // Path Finder state
  const [pathFrom, setPathFrom] = useState<string>('')
  const [pathTo, setPathTo] = useState<string>('')
  const [pathMode, setPathMode] = useState<'shortest' | 'strongest'>('shortest')
  const [pathResult, setPathResult] = useState<{ nodeIds: string[]; edges: Edge[] } | null>(null)
  const [pathError, setPathError] = useState<string | null>(null)

  // Fetch graph data
  const fetchGraph = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (entityType) params.append('entity_type', entityType)
      if (relationshipType) params.append('relationship_type', relationshipType)
      if (minConfidence > 0) params.append('min_confidence', String(minConfidence))
      if (suspiciousOnly) params.append('suspicious_only', 'true')
      if (selectedNodeId) params.append('selected_entity', selectedNodeId)

      const res = await fetch(`/api/cases/${caseId}/graph?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setNodes(data.nodes)
        setEdges(data.edges)
        setCentrality(data.centrality)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchGraph()
  }, [entityType, relationshipType, minConfidence, suspiciousOnly, selectedNodeId])

  // Find path
  const handleFindPath = async () => {
    if (!pathFrom || !pathTo) return
    setPathError(null)
    setPathResult(null)
    try {
      const res = await fetch(`/api/paths?from=${pathFrom}&to=${pathTo}&case_id=${caseId}&mode=${pathMode}`)
      if (res.ok) {
        const data = await res.json()
        setPathResult(data)
      } else {
        const err = await res.json().catch(() => ({}))
        setPathError(err.detail || 'No path found.')
      }
    } catch {
      setPathError('Failed to calculate path between selected target nodes.')
    }
  }

  // Drawers lookups
  const selectedNodeObj = nodes.find(n => n.id === selectedNodeId)
  const selectedEdgeObj = edges.find(e => e.id === selectedEdgeId)

  // Expand neighbors helper
  const handleExpandNeighbors = (nodeId: string) => {
    setSelectedNodeId(nodeId)
    setSelectedEdgeId(null)
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      {/* Filters Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-border bg-card px-6 py-3">
        <div className="flex flex-wrap items-center gap-3">
          {/* Entity Type Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase text-muted-foreground font-semibold">Entity</span>
            <select
              value={entityType}
              onChange={(e) => setEntityType(e.target.value)}
              className="h-8 rounded border border-input bg-surface px-2 text-xs outline-none focus:border-primary/60"
            >
              <option value="">All Types</option>
              <option value="person">Person</option>
              <option value="phone">Phone</option>
              <option value="vehicle">Vehicle</option>
              <option value="account">Account</option>
              <option value="location">Location</option>
              <option value="org">Organization</option>
            </select>
          </div>

          {/* Relationship Filter */}
          <div className="flex items-center gap-1.5">
            <span className="text-[10px] uppercase text-muted-foreground font-semibold">Link</span>
            <select
              value={relationshipType}
              onChange={(e) => setRelationshipType(e.target.value)}
              className="h-8 rounded border border-input bg-surface px-2 text-xs outline-none focus:border-primary/60"
            >
              <option value="">All Links</option>
              <option value="CALLS">Calls</option>
              <option value="TRANSFERS">Transfers</option>
              <option value="OWNS">Owns</option>
              <option value="SEEN_AT">Seen at</option>
              <option value="CO_OCCURS">Co-occurs</option>
              <option value="ASSOCIATED_WITH">Associated with</option>
            </select>
          </div>

          {/* Confidence Slider */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase text-muted-foreground font-semibold">Confidence {minConfidence}%</span>
            <input
              type="range"
              min="0"
              max="90"
              step="10"
              value={minConfidence}
              onChange={(e) => setMinConfidence(Number(e.target.value))}
              className="w-20 accent-primary h-1 rounded bg-muted appearance-none cursor-pointer"
            />
          </div>

          {/* Flags Toggles */}
          <div className="flex items-center gap-3 border-l border-border pl-3">
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground select-none cursor-pointer">
              <input
                type="checkbox"
                checked={suspiciousOnly}
                onChange={(e) => setSuspiciousOnly(e.target.checked)}
                className="accent-primary rounded border-input"
              />
              Suspicious
            </label>
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground select-none cursor-pointer">
              <input
                type="checkbox"
                checked={highlightBridges}
                onChange={(e) => setHighlightBridges(e.target.checked)}
                className="accent-primary rounded border-input"
              />
              Show Bridges
            </label>
          </div>
        </div>

        {/* Clear Path selection */}
        {pathResult && (
          <button 
            onClick={() => { setPathResult(null); setPathFrom(''); setPathTo(''); }}
            className="h-7 px-3 text-[10px] font-semibold text-danger border border-danger/40 bg-danger/10 rounded hover:bg-danger/20"
          >
            Clear Highlighted Path
          </button>
        )}
      </div>

      {/* Main Canvas & Panel Splitter */}
      <div className="flex flex-1 min-h-0">
        {/* Graph Canvas */}
        <div className="flex-1 relative">
          {loading && (
            <div className="absolute inset-0 bg-background/50 backdrop-blur-sm z-20 flex items-center justify-center">
              <div className="flex flex-col items-center gap-2">
                <RefreshCw className="size-6 text-primary animate-spin" />
                <span className="text-xs text-muted-foreground font-medium">Recompiling graph structure...</span>
              </div>
            </div>
          )}
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            centrality={centrality}
            selectedNode={selectedNodeId}
            selectedEdge={selectedEdgeId}
            pathNodeIds={pathResult?.nodeIds}
            pathEdgeIds={pathResult?.edges.map(e => e.id)}
            onSelectNode={setSelectedNodeId}
            onSelectEdge={setSelectedEdgeId}
            highlightBridges={highlightBridges}
            highlightSuspicious={suspiciousOnly}
          />
        </div>

        {/* Dynamic Details / Path Drawer overlays on right */}
        <div className="w-80 border-l border-border bg-card flex flex-col shrink-0 min-h-0 overflow-y-auto">
          {selectedNodeObj ? (
            <EntityDrawer
              entity={selectedNodeObj}
              centrality={centrality[selectedNodeObj.id]}
              evidence={[]} // Fetched inside or passed empty
              connections={[]} // Handled in local canvas select
              onClose={() => setSelectedNodeId(null)}
              onSelectEntity={handleExpandNeighbors}
              onOpenEvidence={() => {}}
              onPathFrom={(id) => { setPathFrom(id); setSelectedNodeId(null); }}
            />
          ) : selectedEdgeObj ? (
            <EdgeDrawer
              edge={selectedEdgeObj}
              source={nodes.find(n => n.id === selectedEdgeObj.source)!}
              target={nodes.find(n => n.id === selectedEdgeObj.target)!}
              evidence={[]}
              onClose={() => setSelectedEdgeId(null)}
              onSelectEntity={handleExpandNeighbors}
              onOpenEvidence={() => {}}
            />
          ) : (
            <div className="p-5 space-y-6">
              {/* Path Finder Tools */}
              <div>
                <h3 className="text-sm font-bold flex items-center gap-1.5 mb-3">
                  <Route className="size-4 text-primary" />
                  Evidence Path Finder
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className="block text-[10px] uppercase text-muted-foreground mb-1">From Node</label>
                    <select
                      value={pathFrom}
                      onChange={(e) => setPathFrom(e.target.value)}
                      className="h-8 w-full rounded border border-input bg-surface px-2 text-xs outline-none focus:border-primary/60"
                    >
                      <option value="">Select Entity...</option>
                      {nodes.map(n => <option key={n.id} value={n.id}>{n.label} ({n.type})</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase text-muted-foreground mb-1">To Node</label>
                    <select
                      value={pathTo}
                      onChange={(e) => setPathTo(e.target.value)}
                      className="h-8 w-full rounded border border-input bg-surface px-2 text-xs outline-none focus:border-primary/60"
                    >
                      <option value="">Select Target...</option>
                      {nodes.map(n => <option key={n.id} value={n.id}>{n.label} ({n.type})</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-[10px] uppercase text-muted-foreground mb-1">Search Strategy</label>
                    <div className="flex gap-2 rounded border border-border p-0.5 bg-surface">
                      <button
                        onClick={() => setPathMode('shortest')}
                        className={cn(
                          "flex-1 h-6 text-[10px] rounded transition font-bold",
                          pathMode === 'shortest' ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                        )}
                      >
                        Shortest Path
                      </button>
                      <button
                        onClick={() => setPathMode('strongest')}
                        className={cn(
                          "flex-1 h-6 text-[10px] rounded transition font-bold",
                          pathMode === 'strongest' ? "bg-primary text-primary-foreground" : "text-muted-foreground"
                        )}
                      >
                        Strongest Evidence
                      </button>
                    </div>
                  </div>

                  <button
                    onClick={handleFindPath}
                    disabled={!pathFrom || !pathTo}
                    className="w-full h-8 flex items-center justify-center gap-1.5 rounded bg-primary text-xs font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-50"
                  >
                    <Play className="size-3.5 fill-current" />
                    Locate Connection Route
                  </button>

                  {pathError && (
                    <div className="flex items-start gap-2 p-2 rounded bg-danger/10 border border-danger/30 text-danger text-xs mt-2">
                      <AlertCircle className="size-4 shrink-0" />
                      <p>{pathError}</p>
                    </div>
                  )}

                  {pathResult && (
                    <div className="rounded-md border border-success/30 bg-success/5 p-3 text-xs space-y-2 mt-2">
                      <span className="font-bold text-success flex items-center gap-1">
                        <ShieldAlert className="size-3.5" />
                        Evidence-Backed Path Found
                      </span>
                      <p className="text-muted-foreground font-mono text-[10px]">
                        Confidence Score: {pathResult.nodeIds.length > 0 ? (pathResult as any).totalConfidence : 0}%<br />
                        Length: {(pathResult as any).hops} Hops
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
