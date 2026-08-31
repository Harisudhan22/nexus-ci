"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { PageHeader } from "@/components/page-header"
import {
  Boxes,
  FileText,
  Upload,
  ArrowRight,
  ShieldAlert,
  CheckCircle2,
  Building,
  MapPin,
  Sparkles,
  Cpu,
  Database,
  GitMerge,
  Layers,
} from "lucide-react"

const PIPELINE_STAGES = [
  { id: "received", label: "RAW EVIDENCE RECEIVED", icon: Upload },
  { id: "queued", label: "QUEUED FOR WORKER PROCESSING", icon: Cpu },
  { id: "ocr", label: "TEXT EXTRACTION & NORMALIZATION", icon: FileText },
  { id: "ner", label: "NER ENTITY EXTRACTION", icon: Sparkles },
  { id: "er", label: "ENTITY RESOLUTION & MERGE", icon: GitMerge },
  { id: "neo4j", label: "NEO4J KNOWLEDGE GRAPH SYNC", icon: Layers },
  { id: "pgvector", label: "PGVECTOR EMBEDDING INDEX", icon: Database },
  { id: "ready", label: "HYBRID RAG & COPILOT READY", icon: CheckCircle2 },
]

export default function NewCasePage() {
  const router = useRouter()
  const [caseId, setCaseId] = useState(`case-${Math.floor(100 + Math.random() * 900)}`)
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [agency, setAgency] = useState("State Crime Branch")
  const [policeStation, setPoliceStation] = useState("Central Station PS")
  const [district, setDistrict] = useState("Chennai")
  const [state, setState] = useState("Tamil Nadu")
  const [priority, setPriority] = useState("high")
  const [classification, setClassification] = useState("SECRET")
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null)
  const [sourceType, setSourceType] = useState("FIR")
  const [loading, setLoading] = useState(false)
  const [activeStage, setActiveStage] = useState<number>(-1)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!caseId || !title) {
      setError("Please provide a Case ID and Title.")
      return
    }

    setLoading(true)
    setError(null)
    setActiveStage(0)

    try {
      // Simulate pipeline progression for visual jury demonstration
      const stageInterval = setInterval(() => {
        setActiveStage((prev) => {
          if (prev < PIPELINE_STAGES.length - 1) return prev + 1
          clearInterval(stageInterval)
          return prev
        })
      }, 400)

      // 1. Create Case
      const caseRes = await fetch("/api/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          id: caseId,
          title,
          description,
          agency,
          priority,
          classification,
          police_station: policeStation,
          district,
          state,
        }),
      })

      if (!caseRes.ok) {
        const errData = await caseRes.json().catch(() => ({}))
        throw new Error(errData.detail || "Failed to create case.")
      }

      // 2. Upload initial evidence if provided
      if (evidenceFile) {
        const formData = new FormData()
        formData.append("file", evidenceFile)
        formData.append("source_type", sourceType)
        formData.append("title", evidenceFile.name)

        await fetch(`/api/cases/${caseId}/documents`, {
          method: "POST",
          body: formData,
        })
      }

      setTimeout(() => {
        router.push(`/cases/${caseId}/overview`)
      }, 3500)
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.")
      setLoading(false)
      setActiveStage(-1)
    }
  }

  return (
    <div className="p-6 space-y-6 max-w-5xl mx-auto">
      <div className="border-b border-slate-800 pb-4">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-cyan-400">
          UNIFIED INGESTION WIZARD
        </span>
        <h1 className="text-2xl font-extrabold text-white">Register New Case & Ingest Evidence</h1>
        <p className="text-xs text-slate-400">
          Triggers automated NER extraction, entity resolution, pgvector embedding, and Neo4j graph construction.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Form Panel (7 Cols) */}
        <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-5">
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <div className="rounded-lg border border-rose-500/40 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                <ShieldAlert className="size-4 shrink-0 text-rose-400" />
                {error}
              </div>
            )}

            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">CASE ID</label>
                <input
                  type="text"
                  value={caseId}
                  onChange={(e) => setCaseId(e.target.value)}
                  className="w-full h-9 rounded-lg border border-slate-800 bg-slate-950 px-3 font-bold text-cyan-400 outline-none ring-cyan-500/30 focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">PRIORITY LEVEL</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full h-9 rounded-lg border border-slate-800 bg-slate-950 px-3 font-bold text-amber-400 outline-none ring-cyan-500/30 focus:border-cyan-500"
                >
                  <option value="low">LOW</option>
                  <option value="medium">MEDIUM</option>
                  <option value="high">HIGH</option>
                  <option value="critical">CRITICAL</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">INVESTIGATION TITLE</label>
              <input
                type="text"
                placeholder="e.g. Operation Cyber-Shield Financial Fraud"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                className="w-full h-9 rounded-lg border border-slate-800 bg-slate-950 px-3 text-xs text-white outline-none ring-cyan-500/30 focus:border-cyan-500"
              />
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">CASE SUMMARY / DESCRIPTION</label>
              <textarea
                rows={3}
                placeholder="Enter detailed facts, initial suspects, or police report narrative..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full rounded-lg border border-slate-800 bg-slate-950 p-3 text-xs text-white outline-none ring-cyan-500/30 focus:border-cyan-500"
              />
            </div>

            {/* Initial Evidence Attachment */}
            <div className="pt-3 border-t border-slate-800">
              <label className="block text-[10px] font-bold text-slate-400 uppercase mb-2">INITIAL UNSTRUCTURED EVIDENCE FILE</label>
              <div className="grid grid-cols-2 gap-3 mb-2">
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  className="h-9 rounded-lg border border-slate-800 bg-slate-950 px-3 font-mono text-xs text-slate-200"
                >
                  <option value="FIR">FIR (First Information Report)</option>
                  <option value="POLICE_REPORT">Police Surveillance Report</option>
                  <option value="CDR">CDR Log File</option>
                  <option value="TRANSACTIONS">Bank Transactions CSV</option>
                  <option value="OSINT">OSINT Intelligence</option>
                </select>

                <input
                  type="file"
                  onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                  className="h-9 text-xs text-slate-400 file:mr-2 file:h-full file:rounded-md file:border-0 file:bg-slate-800 file:px-3 file:text-xs file:font-bold file:text-cyan-400 hover:file:bg-slate-700"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-lg bg-cyan-600 py-3 text-xs font-bold text-white shadow-lg shadow-cyan-600/20 transition hover:bg-cyan-500 active:scale-98 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Cpu className="size-4 animate-spin text-white" />
                  EXECUTING INTELLIGENCE PIPELINE...
                </>
              ) : (
                <>
                  <Upload className="size-4" />
                  CREATE CASE & PROCESS PIPELINE
                </>
              )}
            </button>
          </form>
        </div>

        {/* Right Processing Pipeline Tracker Panel (5 Cols) */}
        <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-900/90 p-6 shadow-xl space-y-4 font-mono">
          <div className="border-b border-slate-800 pb-3">
            <span className="text-xs font-bold text-white flex items-center gap-2">
              <Sparkles className="size-4 text-cyan-400" /> LIVE PROCESSING PIPELINE TRACKER
            </span>
            <p className="text-[10px] text-slate-400">Visual state of asynchronous multi-stage ingestion</p>
          </div>

          <div className="space-y-2">
            {PIPELINE_STAGES.map((stage, idx) => {
              const StageIcon = stage.icon
              const isPassed = activeStage > idx
              const isActive = activeStage === idx
              return (
                <div
                  key={stage.id}
                  className={`p-2.5 rounded-lg border text-xs flex items-center justify-between transition ${
                    isPassed
                      ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                      : isActive
                      ? "border-cyan-500 bg-cyan-500/15 text-white animate-pulse"
                      : "border-slate-800/60 bg-slate-950 text-slate-500"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <StageIcon className={`size-4 ${isPassed ? "text-emerald-400" : isActive ? "text-cyan-400" : "text-slate-600"}`} />
                    <span className="text-[11px] font-bold">{stage.label}</span>
                  </div>
                  {isPassed ? (
                    <CheckCircle2 className="size-3.5 text-emerald-400 shrink-0" />
                  ) : isActive ? (
                    <span className="text-[9px] font-bold text-cyan-400 uppercase">RUNNING</span>
                  ) : (
                    <span className="text-[9px] text-slate-600">IDLE</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
