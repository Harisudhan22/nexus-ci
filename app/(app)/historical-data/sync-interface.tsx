"use client"

import { useState, useEffect } from "react"
import {
  Database,
  FileStack,
  RefreshCw,
  CheckCircle2,
  ShieldAlert,
  Layers,
  Users,
  Phone,
  Car,
  MapPin,
  Building2,
  CreditCard,
  Radio,
  FileText,
  AlertTriangle,
  Play,
  Share2
} from "lucide-react"

interface HistoricalStats {
  historicalCases: number
  firRecords: number
  cdrRecords: number
  financialRecords: number
  surveillanceRecords: number
  intelligenceRecords: number
  persons: number
  phones: number
  vehicles: number
  locations: number
  organizations: number
  accounts: number
  documents: number
  entities: number
  relationships: number
  evidence: number
  indexedRagDocuments: number
  processingFailures: number
}

export function SyncInterface() {
  const [stats, setStats] = useState<HistoricalStats | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)
  const [importing, setImporting] = useState(false)
  const [simulating, setSimulating] = useState<string | null>(null)
  const [actionMessage, setActionMessage] = useState<string | null>(null)

  const fetchStats = async () => {
    setLoadingStats(true)
    try {
      const res = await fetch("/api/historical/stats")
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      console.error("Failed to load historical stats", e)
    } finally {
      setLoadingStats(false)
    }
  }

  useEffect(() => {
    fetchStats()
  }, [])

  const handleImportBatch = async () => {
    setImporting(true)
    setActionMessage(null)
    try {
      const res = await fetch("/api/historical/import-batch", { method: "POST" })
      if (res.ok) {
        const data = await res.json()
        setActionMessage(data.message || "Historical batch ingested and indexed successfully!")
        await fetchStats()
      } else {
        setActionMessage("Error importing historical batch.")
      }
    } catch (err: any) {
      setActionMessage(`Import error: ${err.message}`)
    } finally {
      setImporting(false)
    }
  }

  const handleSimulate = async (type: "fir" | "cdr" | "transaction") => {
    setSimulating(type)
    setActionMessage(null)
    try {
      const res = await fetch(`/api/historical/simulate/${type}`, { method: "POST" })
      if (res.ok) {
        const data = await res.json()
        setActionMessage(data.message || `Simulated ${type.toUpperCase()} ingested successfully.`)
        await fetchStats()
      }
    } catch (err: any) {
      setActionMessage(`Simulation error: ${err.message}`)
    } finally {
      setSimulating(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Real-time Statistics Cards */}
      <div className="rounded-lg border border-border bg-card p-6 shadow-sm">
        <div className="flex items-center justify-between border-b border-border pb-4 mb-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Historical Intelligence Base Statistics</h2>
            <p className="text-xs text-muted-foreground">Live multi-source canonical records across PostgreSQL & Neo4j</p>
          </div>
          <button
            onClick={fetchStats}
            disabled={loadingStats}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium border border-border bg-muted/50 hover:bg-muted transition"
          >
            <RefreshCw className={`size-3.5 ${loadingStats ? "animate-spin" : ""}`} />
            Refresh Counts
          </button>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Layers className="size-3.5 text-primary" /> Historical Cases
            </div>
            <div className="text-xl font-bold">{stats?.historicalCases ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <FileText className="size-3.5 text-blue-500" /> FIR Records
            </div>
            <div className="text-xl font-bold">{stats?.firRecords ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Phone className="size-3.5 text-emerald-500" /> CDR Records
            </div>
            <div className="text-xl font-bold">{stats?.cdrRecords ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <CreditCard className="size-3.5 text-amber-500" /> Financial Records
            </div>
            <div className="text-xl font-bold">{stats?.financialRecords ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Radio className="size-3.5 text-purple-500" /> Surveillance Records
            </div>
            <div className="text-xl font-bold">{stats?.surveillanceRecords ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <ShieldAlert className="size-3.5 text-indigo-500" /> Intel Reports
            </div>
            <div className="text-xl font-bold">{stats?.intelligenceRecords ?? "--"}</div>
          </div>

          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Users className="size-3.5 text-primary" /> Persons
            </div>
            <div className="text-xl font-bold">{stats?.persons ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Phone className="size-3.5 text-emerald-500" /> Phones
            </div>
            <div className="text-xl font-bold">{stats?.phones ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Car className="size-3.5 text-amber-500" /> Vehicles
            </div>
            <div className="text-xl font-bold">{stats?.vehicles ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <MapPin className="size-3.5 text-rose-500" /> Locations
            </div>
            <div className="text-xl font-bold">{stats?.locations ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Building2 className="size-3.5 text-cyan-500" /> Organizations
            </div>
            <div className="text-xl font-bold">{stats?.organizations ?? "--"}</div>
          </div>
          <div className="rounded-md border border-border/70 p-3 bg-background/50">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1">
              <Share2 className="size-3.5 text-violet-500" /> Relationships
            </div>
            <div className="text-xl font-bold">{stats?.relationships ?? "--"}</div>
          </div>
        </div>
      </div>

      {/* Action Notification */}
      {actionMessage && (
        <div className="rounded-lg border border-success/40 bg-success/10 p-4 flex items-center gap-3 text-success">
          <CheckCircle2 className="size-5 shrink-0" />
          <span className="text-sm font-medium">{actionMessage}</span>
        </div>
      )}

      {/* Operations Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Batch Synchronization Card */}
        <div className="rounded-lg border border-border bg-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 rounded-full bg-primary/10 text-primary">
                <Database className="size-6" />
              </div>
              <div>
                <h3 className="text-base font-semibold">Historical Multi-Source Ingestion</h3>
                <p className="text-xs text-muted-foreground">Ingest all synthetic datasets across FIR, CDR, Transactions, Surveillance, Dossiers</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Executes idempotent normalization, NER entity extraction, entity resolution, and knowledge graph construction across 5 historical operations.
            </p>
          </div>

          <div className="mt-6 flex items-center gap-3">
            <button
              onClick={handleImportBatch}
              disabled={importing}
              className="px-5 py-2.5 rounded-md bg-primary text-primary-foreground font-medium text-sm flex items-center gap-2 hover:opacity-90 disabled:opacity-50 transition shadow-sm"
            >
              {importing ? <RefreshCw className="size-4 animate-spin" /> : <Play className="size-4" />}
              {importing ? "Ingesting & Indexing..." : "Initialize & Ingest Batch"}
            </button>
          </div>
        </div>

        {/* Real-time Source Simulation Card */}
        <div className="rounded-lg border border-border bg-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2.5 rounded-full bg-emerald-500/10 text-emerald-500">
                <Radio className="size-6" />
              </div>
              <div>
                <h3 className="text-base font-semibold">Live Source Stream Simulation</h3>
                <p className="text-xs text-muted-foreground">Trigger mock real-time events through source adapters</p>
              </div>
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              Injects individual simulated telemetry events to evaluate real-time processing, normalization, and immediate graph update triggers.
            </p>
          </div>

          <div className="mt-6 flex flex-wrap gap-2">
            <button
              onClick={() => handleSimulate("fir")}
              disabled={simulating !== null}
              className="px-3.5 py-2 rounded-md border border-border bg-background hover:bg-muted text-xs font-medium flex items-center gap-1.5 transition"
            >
              {simulating === "fir" ? <RefreshCw className="size-3.5 animate-spin" /> : <FileText className="size-3.5 text-blue-500" />}
              Simulate New FIR
            </button>
            <button
              onClick={() => handleSimulate("cdr")}
              disabled={simulating !== null}
              className="px-3.5 py-2 rounded-md border border-border bg-background hover:bg-muted text-xs font-medium flex items-center gap-1.5 transition"
            >
              {simulating === "cdr" ? <RefreshCw className="size-3.5 animate-spin" /> : <Phone className="size-3.5 text-emerald-500" />}
              Simulate New CDR
            </button>
            <button
              onClick={() => handleSimulate("transaction")}
              disabled={simulating !== null}
              className="px-3.5 py-2 rounded-md border border-border bg-background hover:bg-muted text-xs font-medium flex items-center gap-1.5 transition"
            >
              {simulating === "transaction" ? <RefreshCw className="size-3.5 animate-spin" /> : <CreditCard className="size-3.5 text-amber-500" />}
              Simulate Transaction
            </button>
          </div>
        </div>
      </div>

      {/* Compliance / Source Adapter Architecture Banner */}
      <div className="rounded-lg border border-warning/40 bg-warning/5 p-4 flex items-start gap-3">
        <ShieldAlert className="size-5 text-warning shrink-0 mt-0.5" />
        <div>
          <h4 className="text-sm font-semibold text-warning">Source Adapter Architecture Notice</h4>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            All ingested records are routed through dedicated mock source adapters (<code>MockCCTNSAdapter</code>, <code>MockCDRAdapter</code>, <code>MockFinancialAdapter</code>, <code>MockSurveillanceAdapter</code>, <code>MockIntelligenceAdapter</code>). NEXUS-CI does not interface with live, unauthorized government production environments.
          </p>
        </div>
      </div>
    </div>
  )
}
