"use client"

import { useEffect, useState } from "react"
import { PageHeader } from "@/components/page-header"
import { FileText, Download, CheckCircle2, RefreshCw, ShieldCheck, Lock, Sparkles, Printer } from "lucide-react"

interface CaseOption {
  id: string
  title: string
}

export default function ReportsPage() {
  const [cases, setCases] = useState<CaseOption[]>([])
  const [selectedCase, setSelectedCase] = useState("")
  const [reportFormat, setReportFormat] = useState("markdown")
  const [generating, setGenerating] = useState(false)
  const [loadingCases, setLoadingCases] = useState(true)
  const [reportData, setReportData] = useState<any>(null)

  useEffect(() => {
    let active = true

    async function loadCases() {
      try {
        const res = await fetch("/api/cases")
        if (!res.ok) return

        const data = await res.json()
        if (!active) return

        const options = data.map((item: any) => ({
          id: item.id,
          title: item.title || item.id,
        }))
        setCases(options)
        setSelectedCase(options[0]?.id || "")
      } catch (error) {
        console.error("Case list fetch failed", error)
      } finally {
        if (active) setLoadingCases(false)
      }
    }

    loadCases()
    return () => {
      active = false
    }
  }, [])

  const handleGenerate = async () => {
    if (!selectedCase) return
    setGenerating(true)
    try {
      const res = await fetch("/api/reports/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: selectedCase, format: reportFormat }),
      })
      if (res.ok) {
        const data = await res.json()
        setReportData(data)
      }
    } catch (e) {
      console.error("Report generation failed", e)
    } finally {
      setGenerating(false)
    }
  }

  const handleDownload = () => {
    if (!reportData?.reportMarkdown) return
    const blob = new Blob([reportData.reportMarkdown], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `NEXUS_CI_Report_${selectedCase}.md`
    a.click()
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Title Header Console */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-cyan-400">
            OFFICIAL JUDICIAL & EXECUTIVE DOSSIER
          </span>
          <h1 className="text-xl font-extrabold text-white">Executive Intelligence Report Generator</h1>
          <p className="text-xs text-slate-400">
            Compiles evidence dossiers, entity graph topologies, pattern engine findings, and SHA-256 cryptographic seals.
          </p>
        </div>
      </div>

      {/* Report Configuration Form */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-5 shadow-xl space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 font-mono text-xs">
          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">TARGET CASE</label>
            <select
              value={selectedCase}
              onChange={(e) => setSelectedCase(e.target.value)}
              disabled={loadingCases || cases.length === 0}
              className="w-full h-10 rounded-lg border border-slate-800 bg-slate-950 px-3 font-bold text-cyan-400 outline-none ring-cyan-500/30 focus:border-cyan-500"
            >
              {cases.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.id} - {c.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-[10px] font-bold text-slate-400 uppercase mb-1">EXPORT FORMAT</label>
            <select
              value={reportFormat}
              onChange={(e) => setReportFormat(e.target.value)}
              className="w-full h-10 rounded-lg border border-slate-800 bg-slate-950 px-3 font-bold text-slate-200"
            >
              <option value="markdown">MARKDOWN (.MD)</option>
              <option value="json">STRUCTURED JSON (.JSON)</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={handleGenerate}
              disabled={generating || !selectedCase}
              className="w-full h-10 flex items-center justify-center gap-2 rounded-lg bg-cyan-600 px-4 text-xs font-bold text-white shadow-lg shadow-cyan-600/20 hover:bg-cyan-500 active:scale-95 transition disabled:opacity-50"
            >
              {generating ? (
                <>
                  <RefreshCw className="size-4 animate-spin" /> GENERATING...
                </>
              ) : (
                <>
                  <Sparkles className="size-4" /> GENERATE REPORT
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Generated Formal Report Preview */}
      {reportData ? (
        <div className="rounded-xl border border-slate-800 bg-slate-900/90 p-6 shadow-2xl space-y-5">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <span className="rounded bg-emerald-500/10 border border-emerald-500/30 px-2 py-0.5 font-mono text-[10px] font-bold text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="size-3" /> OFFICIAL DOSSIER GENERATED
              </span>
              <span className="font-mono text-xs text-slate-400">CASE: {selectedCase}</span>
            </div>

            <button
              onClick={handleDownload}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white shadow hover:bg-emerald-500 active:scale-95 transition"
            >
              <Download className="size-4" /> Download Official Report (.md)
            </button>
          </div>

          <div className="rounded-lg bg-slate-950 p-6 border border-slate-800 font-mono text-xs text-slate-200 leading-relaxed whitespace-pre-wrap">
            {reportData.reportMarkdown}
          </div>
        </div>
      ) : null}
    </div>
  )
}
