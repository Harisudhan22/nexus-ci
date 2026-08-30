"use client"

import { useEffect, useState } from "react"
import { PageHeader } from "@/components/page-header"
import { FileText, Download, CheckCircle2, RefreshCw } from "lucide-react"

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
    <div>
      <PageHeader
        eyebrow="Documentation"
        title="Executive Report Generation"
        description="Generate evidence-grounded, audit-compliant intelligence summaries for judicial and operational review."
      />

      <div className="p-6 space-y-6 max-w-5xl">
        {/* Report Configuration Card */}
        <div className="rounded-lg border border-border bg-card p-6 shadow-sm space-y-4">
          <h3 className="font-semibold text-base text-foreground">Report Configuration</h3>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">Select Target Case</label>
              <select
                value={selectedCase}
                onChange={(e) => setSelectedCase(e.target.value)}
                disabled={loadingCases || cases.length === 0}
                className="mt-1.5 w-full h-10 px-3 rounded-md border border-border bg-background text-sm font-medium focus:outline-none"
              >
                {loadingCases ? (
                  <option>Loading accessible cases...</option>
                ) : cases.length === 0 ? (
                  <option>No accessible cases found</option>
                ) : (
                  cases.map(item => (
                    <option key={item.id} value={item.id}>
                      {item.id} ({item.title})
                    </option>
                  ))
                )}
              </select>
            </div>

            <div>
              <label className="text-xs font-semibold uppercase text-muted-foreground">Output Format</label>
              <select
                value={reportFormat}
                onChange={(e) => setReportFormat(e.target.value)}
                className="mt-1.5 w-full h-10 px-3 rounded-md border border-border bg-background text-sm font-medium focus:outline-none"
              >
                <option value="markdown">Markdown (.md)</option>
                <option value="pdf">PDF Ready Summary</option>
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={handleGenerate}
                disabled={generating || !selectedCase}
                className="w-full h-10 px-5 rounded-md bg-primary text-primary-foreground font-semibold text-sm hover:opacity-90 transition flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {generating ? <RefreshCw className="size-4 animate-spin" /> : <FileText className="size-4" />}
                {generating ? "Compiling Report..." : "Generate Intelligence Report"}
              </button>
            </div>
          </div>
        </div>

        {/* Report Preview */}
        {reportData && (
          <div className="rounded-lg border border-border bg-card shadow-sm overflow-hidden space-y-4">
            <div className="p-4 border-b border-border bg-muted/20 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <CheckCircle2 className="size-4 text-emerald-500" />
                <span>Generated at {new Date(reportData.generatedAt).toLocaleString()}</span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={handleDownload}
                  className="px-3.5 py-1.5 rounded-md bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition flex items-center gap-1.5"
                >
                  <Download className="size-3.5" />
                  Download Report (.md)
                </button>
              </div>
            </div>

            <div className="p-6 font-mono text-xs text-foreground bg-background leading-relaxed whitespace-pre-wrap rounded border border-border/80 mx-6 mb-6">
              {reportData.reportMarkdown}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
