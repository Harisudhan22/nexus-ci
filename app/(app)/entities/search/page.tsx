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
  ChevronRight
} from "lucide-react"
import { PageHeader } from "@/components/page-header"
import { EntityBadge, ConfidenceMeter, StatCard } from "@/components/primitives"

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
    <div>
      <PageHeader
        eyebrow="Intelligence Directory"
        title="Global Entity Search"
        description="Search canonical entities across all historical and active operations with multi-case convergence matching."
      />

      <div className="p-6 space-y-6">
        {/* Search Bar & Filters */}
        <div className="rounded-lg border border-border bg-card p-4 shadow-sm">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search by person name, alias, phone (e.g. 9876543210), plate (TN01AB1234), account (A101)..."
                className="w-full h-10 pl-10 pr-4 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div className="flex gap-2">
              <select
                value={selectedType}
                onChange={(e) => {
                  setSelectedType(e.target.value)
                  performSearch(query, e.target.value)
                }}
                className="h-10 px-3 rounded-md border border-border bg-background text-sm font-medium focus:outline-none"
              >
                <option value="all">All Types</option>
                <option value="person">Persons</option>
                <option value="phone">Phones</option>
                <option value="vehicle">Vehicles</option>
                <option value="account">Accounts</option>
                <option value="location">Locations</option>
                <option value="org">Organizations</option>
              </select>

              <button
                type="submit"
                className="h-10 px-5 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition flex items-center gap-1.5"
              >
                <Search className="size-4" />
                Search
              </button>
            </div>
          </form>
        </div>

        {/* Search Results & Convergence Details Split View */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Results List */}
          <div className="lg:col-span-5 space-y-3">
            <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
              <span>{results.length} matches found across historical database</span>
              {loading && <span className="text-primary animate-pulse">Searching...</span>}
            </div>

            {results.map((ent) => {
              const isSelected = selectedEntity?.id === ent.id
              const isMultiCase = ent.caseIds.length > 1

              return (
                <div
                  key={ent.id}
                  onClick={() => setSelectedEntity(ent)}
                  className={`rounded-lg border p-4 cursor-pointer transition ${
                    isSelected
                      ? "border-primary bg-primary/5 shadow-sm"
                      : "border-border bg-card hover:border-border/80 hover:bg-muted/30"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-foreground">{ent.label}</span>
                        <EntityBadge type={ent.type as any} />
                      </div>
                      {ent.subtitle && (
                        <p className="text-xs text-muted-foreground mt-0.5">{ent.subtitle}</p>
                      )}
                    </div>

                    {isMultiCase && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                        {ent.caseIds.length} Cases
                      </span>
                    )}
                  </div>

                  {/* Badges / Links */}
                  <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Layers className="size-3 text-muted-foreground" />
                      {ent.caseIds.join(", ")}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <GitMerge className="size-3 text-muted-foreground" />
                      {ent.relationshipsCount} links
                    </span>
                  </div>
                </div>
              )
            })}

            {results.length === 0 && !loading && (
              <div className="rounded-lg border border-border bg-card p-8 text-center text-muted-foreground">
                <Search className="size-8 mx-auto opacity-40 mb-2" />
                <p className="text-sm font-medium">No historical entities matched "{query}".</p>
                <p className="text-xs mt-1">Try searching for Ravi Kumar, 9876543210, TN01AB1234, or A101.</p>
              </div>
            )}
          </div>

          {/* Detailed Convergence Inspector */}
          <div className="lg:col-span-7">
            {selectedEntity ? (
              <div className="rounded-lg border border-border bg-card p-6 space-y-6 sticky top-6">
                {/* Header */}
                <div className="flex items-start justify-between border-b border-border pb-4">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h3 className="text-xl font-bold">{selectedEntity.label}</h3>
                      <EntityBadge type={selectedEntity.type as any} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">
                      Entity ID: <code className="font-mono">{selectedEntity.id}</code> • Priority Score: {selectedEntity.relevance}/100
                    </p>
                  </div>

                  <Link
                    href={`/cases/${selectedEntity.caseIds[0]}/network`}
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition"
                  >
                    <GitMerge className="size-3.5" />
                    Open in Graph
                  </Link>
                </div>

                {/* Cross-Case Convergence Convergence Callout */}
                {selectedEntity.caseIds.length > 1 && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 space-y-2">
                    <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm">
                      <ShieldAlert className="size-4" />
                      Multi-Case Convergence Detected ({selectedEntity.caseIds.length} Operations)
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">
                      Target appears across operations <strong>{selectedEntity.caseIds.join(", ")}</strong> with consistent identifiers and relational anchors.
                    </p>
                  </div>
                )}

                {/* Associated Identifiers Grid */}
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  <div className="p-3 rounded-md border border-border/70 bg-background/50">
                    <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <Phone className="size-3 text-emerald-500" /> Linked Phones
                    </div>
                    <div className="text-xs font-semibold">
                      {selectedEntity.phones.length > 0 ? selectedEntity.phones.join(", ") : "None recorded"}
                    </div>
                  </div>

                  <div className="p-3 rounded-md border border-border/70 bg-background/50">
                    <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <Car className="size-3 text-amber-500" /> Linked Vehicles
                    </div>
                    <div className="text-xs font-semibold">
                      {selectedEntity.vehicles.length > 0 ? selectedEntity.vehicles.join(", ") : "None recorded"}
                    </div>
                  </div>

                  <div className="p-3 rounded-md border border-border/70 bg-background/50">
                    <div className="text-xs text-muted-foreground mb-1 flex items-center gap-1">
                      <CreditCard className="size-3 text-blue-500" /> Bank Accounts
                    </div>
                    <div className="text-xs font-semibold">
                      {selectedEntity.accounts.length > 0 ? selectedEntity.accounts.join(", ") : "None recorded"}
                    </div>
                  </div>
                </div>

                {/* Resolved Aliases */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Resolved Aliases & Surface Forms
                  </h4>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedEntity.aliases.map((a, i) => (
                      <span key={i} className="px-2.5 py-1 rounded-md text-xs bg-muted font-medium">
                        {a}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Historical Cases List */}
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
                    Appears in Cases ({selectedEntity.cases.length})
                  </h4>
                  <div className="space-y-2">
                    {selectedEntity.cases.map((c) => (
                      <div
                        key={c.id}
                        className="flex items-center justify-between p-2.5 rounded-md border border-border/60 bg-background/50 text-xs"
                      >
                        <div>
                          <span className="font-semibold text-foreground uppercase">{c.id}</span>
                          <span className="text-muted-foreground ml-2">— {c.title}</span>
                        </div>
                        <Link
                          href={`/cases/${c.id}/overview`}
                          className="text-primary hover:underline flex items-center gap-1"
                        >
                          View Case <ChevronRight className="size-3" />
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-lg border border-border bg-card p-12 text-center text-muted-foreground">
                <Users className="size-10 mx-auto opacity-30 mb-3" />
                <p className="text-sm">Select an entity from the list to view multi-case convergence intelligence.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
