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
  MapPin
} from "lucide-react"

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
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!caseId || !title) {
      setError("Please provide a Case ID and Title.")
      return
    }

    setLoading(true)
    setError(null)

    try {
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

      router.push(`/cases/${caseId}/overview`)
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred.")
      setLoading(false)
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Case Operations"
        title="Register New Case"
        description="Initialize a new investigation and trigger automated historical cross-case matching against the multi-source intelligence database."
      />

      <div className="p-6 max-w-4xl">
        <form onSubmit={handleSubmit} className="space-y-6 rounded-lg border border-border bg-card p-6 shadow-sm">
          {error && (
            <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive flex items-center gap-2">
              <ShieldAlert className="size-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">Case ID *</label>
              <input
                type="text"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                required
                className="mt-1.5 w-full h-9 px-3 rounded-md border border-border bg-background text-sm font-mono focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>

            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">Priority Level</label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="mt-1.5 w-full h-9 px-3 rounded-md border border-border bg-background text-sm focus:outline-none"
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-xs font-semibold uppercase text-muted-foreground">Case Title *</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Operation Cyber Shield / Hawala Transfer Ring"
              required
              className="mt-1.5 w-full h-9 px-3 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="text-xs font-semibold uppercase text-muted-foreground">Operational Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Brief summary of the complaint, incident facts, or initial intelligence lead..."
              className="mt-1.5 w-full p-3 rounded-md border border-border bg-background text-sm focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">Police Station</label>
              <input
                type="text"
                value={policeStation}
                onChange={(e) => setPoliceStation(e.target.value)}
                className="mt-1.5 w-full h-9 px-3 rounded-md border border-border bg-background text-sm focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">District</label>
              <input
                type="text"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="mt-1.5 w-full h-9 px-3 rounded-md border border-border bg-background text-sm focus:outline-none"
              />
            </div>

            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">State</label>
              <input
                type="text"
                value={state}
                onChange={(e) => setState(e.target.value)}
                className="mt-1.5 w-full h-9 px-3 rounded-md border border-border bg-background text-sm focus:outline-none"
              />
            </div>
          </div>

          {/* Initial Evidence Attachment */}
          <div className="border-t border-border pt-6">
            <h4 className="text-sm font-semibold mb-1 flex items-center gap-2">
              <FileText className="size-4 text-primary" /> Attach Initial Evidence / Document
            </h4>
            <p className="text-xs text-muted-foreground mb-4">
              Uploaded files will automatically trigger SHA-256 integrity hashing, NER entity extraction, and historical entity resolution.
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-semibold uppercase text-muted-foreground">Source Category</label>
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  className="mt-1.5 w-full h-9 px-3 rounded-md border border-border bg-background text-sm focus:outline-none"
                >
                  <option value="FIR">FIR / Police Report</option>
                  <option value="CDR">Call Detail Record (CDR)</option>
                  <option value="TRANSACTIONS">Financial Transactions / Ledger</option>
                  <option value="SURVEILLANCE">Surveillance Report</option>
                  <option value="INTELLIGENCE">Intelligence Bulletin</option>
                  <option value="DOSSIER">Criminal Dossier</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-semibold uppercase text-muted-foreground">Select File</label>
                <input
                  type="file"
                  onChange={(e) => setEvidenceFile(e.target.files?.[0] || null)}
                  className="mt-1.5 w-full text-xs file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border-0 file:text-xs file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 cursor-pointer"
                />
              </div>
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-border pt-4">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 rounded-md border border-border text-sm font-medium hover:bg-muted transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-6 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition flex items-center gap-1.5 disabled:opacity-50"
            >
              {loading ? "Creating & Analyzing..." : "Create Case & Start Ingestion"}
              <ArrowRight className="size-4" />
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
