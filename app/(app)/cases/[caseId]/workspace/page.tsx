"use client"

import { useState, useEffect, use } from "react"
import Link from "next/link"
import {
  GitMerge,
  Users,
  FileStack,
  ShieldAlert,
  Search,
  Bot,
  FileSpreadsheet,
  Clock,
  Layers,
  Sparkles,
  ArrowRight,
  Maximize2,
  ChevronRight,
  Info,
  CheckCircle2,
  Share2
} from "lucide-react"

import { PageHeader } from "@/components/page-header"
import { EntityBadge, StatCard, ConfidenceMeter } from "@/components/primitives"
import { GraphCanvas } from "@/components/graph/graph-canvas"
import {
  getCase,
  graphForCase,
  listEntities,
  listEvidence,
  listFindings,
  getGraphCentrality,
  getGraphCommunities,
  getNetworkDna,
  queryRAG
} from "@/lib/domain/store"

export default function CaseWorkspacePage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = use(params)
  const [caseObj, setCaseObj] = useState<any>(null)
  const [graphData, setGraphData] = useState<{ nodes: any[]; edges: any[] }>({ nodes: [], edges: [] })
  const [entities, setEntities] = useState<any[]>([])
  const [findings, setFindings] = useState<any[]>([])
  const [evidence, setEvidence] = useState<any[]>([])
  const [centrality, setCentrality] = useState<any>(null)
  const [communities, setCommunities] = useState<any[]>([])
  const [networkDna, setNetworkDna] = useState<any>(null)
  
  const [selectedEntity, setSelectedEntity] = useState<any>(null)
  const [copilotOpen, setCopilotOpen] = useState(false)
  const [copilotQuestion, setCopilotQuestion] = useState("What phone does Ravi Kumar use?")
  const [copilotResponse, setCopilotResponse] = useState<any>(null)
  const [copilotLoading, setCopilotLoading] = useState(false)

  useEffect(() => {
    async function loadData() {
      const c = await getCase(caseId)
      setCaseObj(c)

      const g = await graphForCase(caseId)
      setGraphData(g)

      const ents = await listEntities(caseId)
      setEntities(ents)
      if (ents.length > 0) setSelectedEntity(ents[0])

      const fnds = await listFindings(caseId)
      setFindings(fnds)

      const evs = await listEvidence(caseId)
      setEvidence(evs)

      const cent = await getGraphCentrality(caseId)
      setCentrality(cent)

      const comms = await getGraphCommunities(caseId)
      setCommunities(comms)

      const dna = await getNetworkDna(caseId)
      setNetworkDna(dna)
    }
    loadData()
  }, [caseId])

  const handleCopilotSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!copilotQuestion.trim()) return
    setCopilotLoading(true)
    try {
      const res = await fetch("/api/copilot/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: caseId, question: copilotQuestion }),
      })
      if (res.ok) {
        const data = await res.json()
        setCopilotResponse(data)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setCopilotLoading(false)
    }
  }

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col overflow-hidden bg-background">
      {/* Top Operational Bar */}
      <div className="border-b border-border bg-card px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-primary/10 text-primary">
            <GitMerge className="size-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-base text-foreground">{caseObj?.title || caseId}</h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-muted text-muted-foreground">
                {caseId}
              </span>
            </div>
            <p className="text-xs text-muted-foreground">Investigation Workspace • Multi-Pane Interactive Graph Canvas</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setCopilotOpen(!copilotOpen)}
            className={`px-3.5 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition ${
              copilotOpen ? "bg-primary text-primary-foreground" : "border border-border bg-background hover:bg-muted"
            }`}
          >
            <Bot className="size-3.5" />
            AI Copilot Assistant
          </button>
          <Link
            href="/reports"
            className="px-3.5 py-1.5 rounded-md border border-border bg-background hover:bg-muted text-xs font-semibold flex items-center gap-1.5 transition"
          >
            <FileSpreadsheet className="size-3.5" />
            Generate Report
          </Link>
        </div>
      </div>

      {/* Main 4-Pane Layout */}
      <div className="flex-1 grid grid-cols-12 overflow-hidden">
        {/* Left Navigator (3 Cols) */}
        <div className="col-span-3 border-r border-border bg-card flex flex-col overflow-hidden">
          <div className="p-3 border-b border-border bg-muted/20">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Case Entities ({entities.length})</h3>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-border/60">
            {entities.map((e) => {
              const isSelected = selectedEntity?.id === e.id
              return (
                <div
                  key={e.id}
                  onClick={() => setSelectedEntity(e)}
                  className={`p-3 cursor-pointer transition ${
                    isSelected ? "bg-primary/10 border-l-2 border-primary" : "hover:bg-muted/30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-xs text-foreground">{e.label}</span>
                    <EntityBadge type={e.type} />
                  </div>
                  {e.subtitle && <p className="text-[11px] text-muted-foreground mt-0.5">{e.subtitle}</p>}
                </div>
              )
            })}
          </div>

          <div className="p-3 border-t border-border bg-muted/20">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">Findings ({findings.length})</h3>
            <div className="space-y-1.5">
              {findings.slice(0, 3).map((f) => (
                <div key={f.id} className="p-2 rounded bg-background border border-border text-[11px]">
                  <div className="font-semibold text-warning">{f.title}</div>
                  <div className="text-muted-foreground truncate mt-0.5">{f.why}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Center Graph Canvas (6 Cols or 9 Cols if Copilot closed) */}
        <div className={`${copilotOpen ? "col-span-6" : "col-span-6"} border-r border-border bg-background relative flex flex-col`}>
          <div className="p-3 border-b border-border bg-card/60 flex items-center justify-between">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span>Nodes: <strong className="text-foreground">{graphData.nodes.length}</strong></span>
              <span>Edges: <strong className="text-foreground">{graphData.edges.length}</strong></span>
              <span>Communities: <strong className="text-foreground">{communities.length}</strong></span>
            </div>
            <span className="text-[10px] text-emerald-500 font-mono">Grounded Knowledge Graph</span>
          </div>

          <div className="flex-1 relative">
            <GraphCanvas
              nodes={graphData.nodes}
              edges={graphData.edges}
              selectedEntityId={selectedEntity?.id}
              onSelectEntity={(id) => {
                const found = entities.find((ent) => ent.id === id)
                if (found) setSelectedEntity(found)
              }}
            />
          </div>

          {/* Bottom Timeline bar */}
          <div className="h-14 border-t border-border bg-card px-4 flex items-center justify-between text-xs text-muted-foreground shrink-0">
            <div className="flex items-center gap-2">
              <Clock className="size-4 text-primary" />
              <span>Temporal Activity Window: 2026-08-01 to 2026-08-30</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="size-2 rounded-full bg-emerald-500" />
              <span>Real-Time Sync Active</span>
            </div>
          </div>
        </div>

        {/* Right Inspector & Copilot Drawer (3 Cols) */}
        <div className="col-span-3 border-l border-border bg-card flex flex-col overflow-y-auto">
          {copilotOpen ? (
            <div className="p-4 space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <h3 className="font-bold text-sm flex items-center gap-2 text-primary">
                  <Bot className="size-4" /> Copilot Intelligence Drawer
                </h3>
              </div>

              <form onSubmit={handleCopilotSubmit} className="space-y-3">
                <textarea
                  value={copilotQuestion}
                  onChange={(e) => setCopilotQuestion(e.target.value)}
                  rows={3}
                  className="w-full p-2.5 rounded-md border border-border bg-background text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="Ask Copilot a grounded question about this case..."
                />
                <button
                  type="submit"
                  disabled={copilotLoading}
                  className="w-full py-2 rounded-md bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  {copilotLoading ? "Querying RAG & Graph..." : "Ask Copilot"}
                  <Sparkles className="size-3.5" />
                </button>
              </form>

              {copilotResponse && (
                <div className="rounded-md border border-border bg-background p-3 space-y-2 text-xs">
                  <div className="font-semibold text-primary">Copilot Response</div>
                  <p className="leading-relaxed text-foreground">{copilotResponse.summary}</p>
                  {copilotResponse.sources && copilotResponse.sources.length > 0 && (
                    <div className="border-t border-border pt-2 text-[11px] text-muted-foreground">
                      Sources: {copilotResponse.sources.join(", ")}
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 space-y-5">
              <div className="border-b border-border pb-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">Entity Inspector</h3>
                {selectedEntity ? (
                  <div>
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-base">{selectedEntity.label}</h4>
                      <EntityBadge type={selectedEntity.type} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{selectedEntity.subtitle}</p>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">Select a node from graph or list</p>
                )}
              </div>

              {selectedEntity && (
                <div className="space-y-4">
                  {/* Identifiers */}
                  <div>
                    <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1.5">Attributes & Identifiers</h5>
                    <div className="space-y-1 bg-background p-2.5 rounded border border-border text-xs">
                      {selectedEntity.attributes ? (
                        Object.entries(selectedEntity.attributes).map(([k, v]) => (
                          <div key={k} className="flex justify-between">
                            <span className="text-muted-foreground">{k}:</span>
                            <span className="font-semibold font-mono">{String(v)}</span>
                          </div>
                        ))
                      ) : (
                        <span className="text-muted-foreground">No custom attributes</span>
                      )}
                    </div>
                  </div>

                  {/* Resolved Aliases */}
                  <div>
                    <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1.5">Aliases</h5>
                    <div className="flex flex-wrap gap-1">
                      {selectedEntity.aliases?.map((a: string, i: number) => (
                        <span key={i} className="px-2 py-0.5 rounded bg-muted text-[10px] font-medium">
                          {a}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Historical Cases */}
                  <div>
                    <h5 className="text-[11px] font-semibold uppercase text-muted-foreground mb-1.5">Appears in Cases</h5>
                    <div className="flex flex-wrap gap-1">
                      {selectedEntity.caseIds?.map((c: string) => (
                        <span key={c} className="px-2 py-0.5 rounded bg-amber-500/10 text-amber-500 border border-amber-500/20 text-[10px] font-semibold">
                          {c}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
