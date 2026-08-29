'use client'

import { useState, useEffect } from 'react'
import { FileStack, FileText, UploadCloud, Search, ShieldCheck, AlertCircle, RefreshCw, Layers } from 'lucide-react'
import { StatusBadge, RelevanceBadge } from '@/components/primitives'
import { cn } from '@/lib/utils'

interface Evidence {
  id: string
  caseId: string
  title: string
  sourceType: string
  fileName: string
  sha256: string
  uploadedAt: string
  uploadedBy: string
  sizeBytes: number
  status: string
  relevance: number
  extractedText?: string
}

const SOURCE_TYPES = ['FIR', 'POLICE_REPORT', 'CDR', 'TRANSACTIONS', 'VEHICLE', 'JSON', 'IMAGE']

export function EvidenceManager({ caseId, initialEvidence }: { caseId: string; initialEvidence: Evidence[] }) {
  const [evidenceList, setEvidenceList] = useState<Evidence[]>(initialEvidence)
  const [selectedDoc, setSelectedDoc] = useState<Evidence | null>(null)
  const [docText, setDocText] = useState<string>('')
  const [docEntities, setDocEntities] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [integrityState, setIntegrityState] = useState<{ verified?: boolean; message?: string } | null>(null)
  const [verifying, setVerifying] = useState(false)

  // Upload state
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState('')
  const [sourceType, setSourceType] = useState('FIR')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  // Poll processing files
  useEffect(() => {
    const processingFiles = evidenceList.filter(e => e.status === 'processing')
    if (processingFiles.length === 0) return

    const interval = setInterval(async () => {
      let updated = false
      const newList = await Promise.all(evidenceList.map(async (e) => {
        if (e.status === 'processing') {
          try {
            const res = await fetch(`/api/documents/${e.id}`)
            if (res.ok) {
              const data = await res.json()
              if (data.status !== 'processing') {
                updated = true
                return data
              }
            }
          } catch (err) {
            console.error('Error polling document status:', err)
          }
        }
        return e
      }))

      if (updated) {
        setEvidenceList(newList)
      }
    }, 2500)

    return () => clearInterval(interval)
  }, [evidenceList])

  // Fetch document text and entities on selection
  const selectDocument = async (doc: Evidence) => {
    setSelectedDoc(doc)
    setIntegrityState(null)
    setDocText('')
    setDocEntities([])
    
    try {
      const textRes = await fetch(`/api/documents/${doc.id}/text`)
      if (textRes.ok) {
        const textData = await textRes.json()
        setDocText(textData.text)
      }

      const entRes = await fetch(`/api/documents/${doc.id}/entities`)
      if (entRes.ok) {
        const entData = await entRes.json()
        setDocEntities(entData)
      }
    } catch (err) {
      console.error('Error fetching document details:', err)
    }
  }

  // Integrity Check
  const runIntegrityCheck = async (docId: string) => {
    setVerifying(true)
    setIntegrityState(null)
    try {
      const res = await fetch(`/api/documents/${docId}/verify-integrity`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setIntegrityState({ verified: data.verified, message: data.message })
      } else {
        setIntegrityState({ verified: false, message: 'Could not compute hash. File may be missing or corrupt.' })
      }
    } catch {
      setIntegrityState({ verified: false, message: 'Integrity check request timed out.' })
    } finally {
      setVerifying(false)
    }
  }

  // Upload handler
  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedFile) return

    setUploading(true)
    setUploadProgress('FILE RECEIVED')
    
    const formData = new FormData()
    formData.append('file', selectedFile)
    formData.append('source_type', sourceType)
    formData.append('title', selectedFile.name)

    try {
      // Simulate pipeline logs locally for UI updates
      setTimeout(() => setUploadProgress('HASH GENERATED'), 600)
      setTimeout(() => setUploadProgress('PARSING'), 1200)
      setTimeout(() => setUploadProgress('ENTITY EXTRACTION'), 1800)

      const res = await fetch(`/api/cases/${caseId}/documents`, {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        throw new Error(err.detail || 'Upload failed.')
      }

      const newDoc = await res.json()
      setEvidenceList(prev => [newDoc, ...prev])
      setSelectedFile(null)
    } catch (err: any) {
      alert(err.message || 'File upload failed.')
    } finally {
      setUploading(false)
      setUploadProgress('')
    }
  }

  // Filter list
  const filteredList = evidenceList.filter(e => 
    e.fileName.toLowerCase().includes(searchQuery.toLowerCase()) ||
    e.sourceType.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="grid grid-cols-1 gap-6 p-6 lg:grid-cols-3">
      {/* Upload & List Column */}
      <div className="space-y-6 lg:col-span-2">
        {/* Upload Form */}
        <section className="rounded-lg border border-border bg-card p-5">
          <h2 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <UploadCloud className="size-4 text-primary" />
            Ingest New Evidence File
          </h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Source Record Type</label>
                <select
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  className="h-9 w-full rounded-md border border-input bg-surface px-3 text-xs outline-none focus:border-primary/60"
                >
                  {SOURCE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs text-muted-foreground mb-1">Upload File (Max 15MB)</label>
                <input
                  type="file"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="h-9 w-full rounded-md border border-input bg-surface px-2 py-1 text-xs outline-none cursor-pointer focus:border-primary/60"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={uploading || !selectedFile}
              className="flex w-full h-9 items-center justify-center gap-2 rounded-md bg-primary text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {uploading ? (
                <>
                  <RefreshCw className="size-4 animate-spin" />
                  Processing Pipeline: {uploadProgress}
                </>
              ) : 'Start Ingestion Pipeline'}
            </button>
          </form>
        </section>

        {/* Evidence List */}
        <section className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center justify-between gap-4 mb-4">
            <h2 className="text-sm font-semibold">Evidence Inventory</h2>
            <div className="relative w-48">
              <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search uploads..."
                className="h-8 w-full rounded-md border border-input bg-surface pl-8 pr-2 text-xs outline-none focus:border-primary/60"
              />
            </div>
          </div>

          <div className="divide-y divide-border overflow-hidden rounded-md border border-border">
            {filteredList.length === 0 ? (
              <div className="py-8 text-center text-xs text-muted-foreground">No evidence records match your search criteria.</div>
            ) : (
              filteredList.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => selectDocument(doc)}
                  className={cn(
                    "flex w-full items-center gap-4 px-4 py-3 text-left transition hover:bg-secondary/35",
                    selectedDoc?.id === doc.id && "bg-secondary/50"
                  )}
                >
                  <FileText className="size-8 text-muted-foreground shrink-0" />
                  <div className="min-w-0 flex-1 leading-snug">
                    <p className="text-xs font-mono text-primary uppercase">{doc.id}</p>
                    <p className="text-sm font-semibold truncate mt-0.5">{doc.fileName}</p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {doc.sourceType} · {(doc.sizeBytes / 1024).toFixed(1)} KB · Ingested {new Date(doc.uploadedAt).toLocaleDateString()}
                    </p>
                  </div>
                  <div className="shrink-0 flex flex-col items-end gap-1">
                    <StatusBadge status={doc.status} />
                    <RelevanceBadge value={doc.relevance} />
                  </div>
                </button>
              ))
            )}
          </div>
        </section>
      </div>

      {/* Details & Contents Drawer Column */}
      <div className="lg:col-span-1">
        {selectedDoc ? (
          <aside className="rounded-lg border border-border bg-card p-5 space-y-5">
            <div>
              <span className="text-[10px] font-mono text-primary font-bold uppercase">{selectedDoc.id}</span>
              <h3 className="text-base font-semibold leading-tight">{selectedDoc.fileName}</h3>
              <p className="text-xs text-muted-foreground mt-1">Source: {selectedDoc.sourceType}</p>
            </div>

            {/* SHA-256 & Integrity Verification */}
            <div className="rounded-md border border-border bg-secondary/20 p-3 space-y-2">
              <span className="text-[10px] font-medium uppercase text-muted-foreground block">SHA-256 Checksum</span>
              <code className="text-[10px] break-all block leading-normal font-mono bg-surface p-1.5 rounded border border-border text-foreground/80">
                {selectedDoc.sha256}
              </code>
              <button
                onClick={() => runIntegrityCheck(selectedDoc.id)}
                disabled={verifying}
                className="flex items-center gap-1.5 h-7 px-3 text-[11px] font-semibold text-primary border border-primary/40 bg-primary/10 rounded hover:bg-primary/20 disabled:opacity-50"
              >
                <ShieldCheck className="size-3.5" />
                {verifying ? 'Calculating Checksum...' : 'Verify File Integrity'}
              </button>

              {integrityState && (
                <div className={cn(
                  "flex items-start gap-2 p-2 rounded text-xs mt-2 border",
                  integrityState.verified 
                    ? "bg-success/10 border-success/30 text-success" 
                    : "bg-danger/10 border-danger/30 text-danger"
                )}>
                  {integrityState.verified ? <ShieldCheck className="size-4 shrink-0" /> : <AlertCircle className="size-4 shrink-0" />}
                  <p>{integrityState.message}</p>
                </div>
              )}
            </div>

            {/* Extracted Entities */}
            <div>
              <span className="text-[10px] font-medium uppercase text-muted-foreground block mb-2">Extracted Entities ({docEntities.length})</span>
              {docEntities.length === 0 ? (
                <p className="text-xs text-muted-foreground italic">No entities matched in document text yet.</p>
              ) : (
                <div className="flex flex-wrap gap-1.5">
                  {docEntities.map((e) => (
                    <span 
                      key={e.id}
                      className="px-2 py-0.5 text-[10px] font-medium rounded border border-border bg-surface text-foreground"
                    >
                      {e.surface} <span className="text-[8px] opacity-60 uppercase font-mono">({e.type})</span>
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Parsed Text Preview */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-medium uppercase text-muted-foreground block">Extracted Text Content</span>
              <div className="max-h-56 overflow-y-auto border border-border bg-surface p-3 rounded font-mono text-[11px] leading-relaxed text-muted-foreground whitespace-pre-wrap">
                {docText || 'No text extracted. File is either empty or processing.'}
              </div>
            </div>
          </aside>
        ) : (
          <div className="rounded-lg border border-dashed border-border py-20 text-center bg-card">
            <FileStack className="size-8 text-muted-foreground mx-auto mb-2 opacity-50" />
            <p className="text-sm text-muted-foreground">Select an evidence record to inspect metadata details.</p>
          </div>
        )}
      </div>
    </div>
  )
}
