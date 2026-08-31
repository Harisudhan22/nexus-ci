"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import {
  Search,
  Users,
  Phone,
  Car,
  MapPin,
  CreditCard,
  Building2,
  GitMerge,
  Layers,
  ArrowUpRight,
  ShieldAlert,
  SlidersHorizontal,
  ExternalLink,
  ChevronRight,
  Sparkles,
  Lock,
} from "lucide-react"
import { EntityBadge, ConfidenceMeter, StatCard } from "@/components/primitives"
import { cn } from "@/lib/utils"

interface SearchResult {
  id: string
  label: string
  type: string
  subtitle?: string
  aliases: string[]
  caseIds: string[]
  cases: { id: string; title: string; priority: string }[]
  relevance: number
  attributes: Record<string, any>
  phones: string[]
  vehicles: string[]
  locations: string[]
  accounts: string[]
  organizations: string[]
  relationshipsCount: number
  findingsCount: number
  matchReasons: string[]
}

export default function GlobalEntitySearchPage() {
  const [query, setQuery] = useState("Ravi Kumar")
  const [selectedType, setSelectedType] = useState<string>("all")
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedEntity, setSelectedEntity] = useState<SearchResult | null>(null)

  const performSearch = async (term: string, type: string) => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (term) params.append("q", term)
      if (type && type !== "all") params.append("entity_type", type)
      const res = await fetch(`/api/entities/search?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setResults(data)
        if (data.length > 0) {
          setSelectedEntity(data[0])
        } else {
          setSelectedEntity(null)
        }
      }
    } catch (e) {
      console.error("Global search failed", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    performSearch(query, selectedType)
  }, [])

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    performSearch(query, selectedType)
  }

  return (
    <div className="space-y-6 p-6">
      {/* Title Console Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-cyan-400">
            CROSS-CASE ENTITY CONVERGENCE EXPLORER
          </span>
          <h1 className="text-xl font-extrabold text-white">Global Entity Intelligence Directory</h1>
          <p className="text-xs text-slate-400">
            Search canonical suspects, phone numbers, vehicle plates, and financial accounts across all historical operations.
          </p>
        </div>
      </div>

      {/* Search Input Bar & Type Selector */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-4 shadow-xl">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-slate-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search suspect name, phone, vehicle plate, account number..."
              className="h-10 w-full rounded-lg border border-slate-800 bg-slate-950 pl-10 pr-4 text-xs text-white outline-none ring-cyan-500/30 focus:border-cyan-500"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={selectedType}
              onChange={(e) => {
                setSelectedType(e.target.value)
                performSearch(query, e.target.value)
              }}
              className="h-10 rounded-lg border border-slate-800 bg-slate-950 px-3 font-mono text-xs text-slate-200"
            >
              <option value="all">ALL ENTITY TYPES</option>
              <option value="person">PERSON</option>
              <option value="phone">PHONE</option>
              <option value="vehicle">VEHICLE</option>
              <option value="account">ACCOUNT</option>
              <option value="location">LOCATION</option>
            </select>

            <button
              type="submit"
              disabled={loading}
              className="h-10 rounded-lg bg-cyan-600 px-5 text-xs font-bold text-white shadow-lg shadow-cyan-600/20 hover:bg-cyan-500 active:scale-95 transition"
            >
              {loading ? "SEARCHING..." : "SEARCH ENTITIES"}
            </button>
          </div>
        </form>
      </div>

      {/* 2-Column Split: Results List (5 Cols) vs Cross-Case Intelligence Panel (7 Cols) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-16rem)]">
        
        {/* Results List */}
        <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col h-full overflow-hidden">
          <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
            <span className="font-mono text-xs font-bold text-white flex items-center gap-1.5">
              <Users className="size-4 text-cyan-400" /> SEARCH MATCHES ({results.length})
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
            {results.map((ent) => {
              const active = selectedEntity?.id === ent.id
              return (
                <div
                  key={ent.id}
                  onClick={() => setSelectedEntity(ent)}
                  className={cn(
                    "cursor-pointer rounded-lg border p-3.5 transition space-y-2",
                    active
                      ? "border-cyan-500 bg-cyan-500/10 text-white shadow-lg"
                      : "border-slate-800 bg-slate-950 text-slate-300 hover:border-slate-700 hover:bg-slate-900"
                  )}
                >
                  <div className="flex items-center justify-between font-mono">
                    <span className="text-[10px] font-bold text-cyan-400 uppercase">{ent.type}</span>
                    <span className="text-[10px] font-bold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-1.5 py-0.5 rounded">
                      {ent.caseIds?.length || 1} CASES
                    </span>
                  </div>

                  <h3 className="font-bold text-sm text-white">{ent.label}</h3>
                  {ent.subtitle ? <p className="text-xs text-slate-400">{ent.subtitle}</p> : null}

                  {ent.aliases && ent.aliases.length > 0 ? (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {ent.aliases.map((alias) => (
                        <span key={alias} className="rounded bg-slate-900 border border-slate-800 px-1.5 py-0.5 text-[9px] font-mono text-slate-400">
                          {alias}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>
              )
            })}
          </div>
        </div>

        {/* Cross-Case Intelligence Panel */}
        <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-900/90 p-5 flex flex-col h-full overflow-hidden">
          {selectedEntity ? (
            <div className="flex-1 overflow-y-auto space-y-5 pr-1">
              <div className="border-b border-slate-800 pb-3 flex items-center justify-between">
                <div>
                  <span className="font-mono text-[10px] font-bold text-cyan-400 uppercase">{selectedEntity.type}</span>
                  <h2 className="text-lg font-extrabold text-white">{selectedEntity.label}</h2>
                  {selectedEntity.subtitle ? <p className="text-xs text-slate-400">{selectedEntity.subtitle}</p> : null}
                </div>
                <Link
                  href={`/cases/${selectedEntity.caseIds?.[0] || 'case-101'}/network`}
                  className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-bold text-white shadow hover:bg-cyan-500 active:scale-95 transition"
                >
                  <GitMerge className="size-3.5" /> View Network Subgraph
                </Link>
              </div>

              {/* Connected Cases */}
              <div className="space-y-2 font-mono">
                <span className="text-xs font-bold text-white flex items-center gap-1.5">
                  <Layers className="size-3.5 text-amber-400" /> RECURRING CROSS-CASE OCCURRENCES
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {(selectedEntity.cases || selectedEntity.caseIds || ['case-101']).map((c: any) => {
                    const cId = typeof c === 'string' ? c : c.id
                    const cTitle = typeof c === 'string' ? `Investigation ${c}` : c.title
                    return (
                      <Link
                        key={cId}
                        href={`/cases/${cId}/overview`}
                        className="p-3 rounded-lg border border-slate-800 bg-slate-950 hover:border-cyan-500/40 hover:bg-slate-900 transition flex items-center justify-between text-xs"
                      >
                        <div>
                          <span className="text-cyan-400 font-bold block">{cId}</span>
                          <span className="text-slate-300 line-clamp-1">{cTitle}</span>
                        </div>
                        <ArrowUpRight className="size-4 text-slate-500 shrink-0" />
                      </Link>
                    )
                  })}
                </div>
              </div>

              {/* Key Attributes */}
              {selectedEntity.attributes && Object.keys(selectedEntity.attributes).length > 0 ? (
                <div className="space-y-2 font-mono">
                  <span className="text-xs font-bold text-white flex items-center gap-1.5">
                    <Sparkles className="size-3.5 text-emerald-400" /> KNOWN ATTRIBUTES & PROPERTIES
                  </span>
                  <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1 text-xs">
                    {Object.entries(selectedEntity.attributes).map(([k, v]) => (
                      <div key={k} className="flex justify-between border-b border-slate-800/60 pb-1 last:border-0">
                        <span className="text-slate-400">{k}:</span>
                        <span className="font-bold text-white">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-slate-500 text-xs">
              <Users className="size-8 mb-2 opacity-40" />
              <span>Select an entity to inspect cross-case convergence</span>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
