'use client'

import { useState, useEffect } from 'react'
import { Bot, User, Send, Compass, ShieldAlert, Sparkles, RefreshCw, FileText, CheckCircle2, Lock, ArrowRight, Layers } from 'lucide-react'
import { ConfidenceMeter } from '@/components/primitives'
import { cn } from '@/lib/utils'

interface ChatMessage {
  role: 'user' | 'assistant'
  content?: string
  structured?: {
    summary: string
    key_reasons: string[]
    observed_evidence: string[]
    analytical_interpretation: string[]
    confidence: number
    supporting_evidence: string[]
    provider_name?: string
    providerName?: string
    provider_type?: string
    providerType?: string
    model?: string
    is_real_llm?: boolean
  }
}

interface ProviderStatus {
  provider_name?: string
  providerName?: string
  provider_type?: string
  providerType?: string
  model?: string
  is_real_llm?: boolean
  configured?: boolean
}

const SUGGESTIONS = [
  "who is Vikram Seth what is the relation of him in this project",
  "Why is Ravi Kumar connected to vehicle TN01AB1234?",
  "What evidence connects Case-101 to historical cases?"
]

export function CopilotChat({ caseId }: { caseId: string }) {
  const [providerStatus, setProviderStatus] = useState<ProviderStatus>({
    provider_name: 'grounded_local',
    provider_type: 'LOCAL_FALLBACK',
    model: 'GroundedLocalSolver',
    is_real_llm: false,
    configured: true,
  })

  useEffect(() => {
    fetch('/api/copilot/status')
      .then((res) => res.json())
      .then((data) => {
        if (data && data.provider_name) {
          setProviderStatus(data)
        }
      })
      .catch(() => {})
  }, [])

  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content:
        'Welcome to the NEXUS-CI Investigator Copilot. I retrieve facts exclusively from verified case evidence (PostgreSQL pgvector + Neo4j Graph). How can I assist your investigation today?',
    },
  ])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setQuery('')
    setLoading(true)

    try {
      const res = await fetch(`/api/copilot/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseId, question: text }),
      })

      if (res.ok) {
        const data = await res.json()
        setMessages((prev) => [...prev, { role: 'assistant', structured: data }])
      } else {
        const err = await res.json().catch(() => ({}))
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: err.detail || 'I encountered an error querying the analytical services.',
          },
        ])
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Network connection issue connecting to Copilot API.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const pName = providerStatus.provider_name || providerStatus.providerName || 'grounded_local'
  const pType = providerStatus.provider_type || providerStatus.providerType || 'LOCAL_FALLBACK'

  return (
    <div className="space-y-4 p-6">
      {/* Title Header Console */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-pink-500/30 bg-pink-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-pink-400">
            EVIDENCE-GROUNDED QA WORKBENCH
          </span>
          <h1 className="text-xl font-extrabold text-white">Investigator AI Copilot ({caseId})</h1>
          <p className="text-xs text-slate-400">
            Hybrid RAG pipeline querying PostgreSQL pgvector embeddings & Neo4j Knowledge Graph with zero-hallucination bounds.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 rounded-lg border border-pink-500/30 bg-slate-900 px-3 py-1.5 font-mono text-xs font-bold text-pink-400">
            <Sparkles className="size-3.5" /> Provider: {pName.toUpperCase()} ({pType})
          </span>
        </div>
      </div>

      {/* Main Chat Workbench Area */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[calc(100vh-14rem)]">
        {/* Left 8 Cols: Messages Stream */}
        <div className="lg:col-span-8 rounded-xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col h-full overflow-hidden">
          <div className="flex-1 overflow-y-auto space-y-4 pr-2">
            {messages.map((m, idx) => (
              <div
                key={idx}
                className={cn('flex gap-3 text-xs', m.role === 'user' ? 'justify-end' : 'justify-start')}
              >
                {m.role === 'assistant' && (
                  <div className="size-8 rounded-full bg-pink-500/20 border border-pink-500/40 flex items-center justify-center shrink-0">
                    <Bot className="size-4 text-pink-400" />
                  </div>
                )}

                <div
                  className={cn(
                    'max-w-2xl rounded-xl p-4 leading-relaxed',
                    m.role === 'user'
                      ? 'bg-cyan-600 text-white font-medium shadow-md'
                      : 'bg-slate-950 border border-slate-800 text-slate-200 shadow-xl space-y-3',
                  )}
                >
                  {m.content && <p>{m.content}</p>}

                  {m.structured && (
                    <div className="space-y-3">
                      {/* Summary */}
                      <div className="space-y-1">
                        <span className="font-mono text-[9px] font-bold text-pink-400 uppercase tracking-wider block">
                          GROUNDED SUMMARY
                        </span>
                        <p className="font-bold text-xs text-white leading-relaxed">{m.structured.summary}</p>
                      </div>

                      {/* Observed Facts / Documents */}
                      {m.structured.observed_evidence && m.structured.observed_evidence.length > 0 && (
                        <div className="space-y-1">
                          <span className="font-mono text-[9px] font-bold text-slate-400 uppercase tracking-wider block">
                            OBSERVED EVIDENCE CITATIONS
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {m.structured.observed_evidence.map((docId) => (
                              <span
                                key={docId}
                                className="rounded bg-slate-900 border border-cyan-500/40 px-2 py-0.5 font-mono text-[10px] font-bold text-cyan-300 flex items-center gap-1"
                              >
                                <FileText className="size-3 text-cyan-400" /> {docId}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Confidence Meter & Provider */}
                      <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[10px] font-mono">
                        <ConfidenceMeter value={m.structured.confidence || 85} />
                        <span className="text-slate-400">Engine: {m.structured.provider_name || 'grounded_local'}</span>
                      </div>
                    </div>
                  )}
                </div>

                {m.role === 'user' && (
                  <div className="size-8 rounded-full bg-cyan-600/20 border border-cyan-500/40 flex items-center justify-center shrink-0">
                    <User className="size-4 text-cyan-400" />
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex gap-3 text-xs justify-start">
                <div className="size-8 rounded-full bg-pink-500/20 border border-pink-500/40 flex items-center justify-center shrink-0">
                  <Bot className="size-4 text-pink-400 animate-spin" />
                </div>
                <div className="rounded-xl p-4 bg-slate-950 border border-slate-800 text-slate-400 font-mono">
                  Synthesizing grounded facts across PostgreSQL & Neo4j...
                </div>
              </div>
            )}
          </div>

          {/* Prompt Input Form */}
          <div className="pt-3 border-t border-slate-800">
            <form
              onSubmit={(e) => {
                e.preventDefault()
                handleSend(query)
              }}
              className="relative flex items-center"
            >
              <input
                type="text"
                placeholder="Query Copilot on entities, transactions, or communications..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="h-11 w-full rounded-xl border border-slate-800 bg-slate-950 pl-4 pr-12 text-xs text-white outline-none ring-pink-500/30 focus:border-pink-500 focus:ring-2"
              />
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="absolute right-2 rounded-lg bg-pink-600 p-2 text-white hover:bg-pink-500 disabled:opacity-40 transition active:scale-95"
              >
                <Send className="size-4" />
              </button>
            </form>
          </div>
        </div>

        {/* Right 4 Cols: Suggestions & RAG Guard Panel */}
        <div className="lg:col-span-4 rounded-xl border border-slate-800 bg-slate-900/90 p-4 flex flex-col h-full overflow-hidden space-y-4">
          <div className="border-b border-slate-800 pb-3">
            <span className="font-mono text-xs font-bold text-white flex items-center gap-1.5 mb-1">
              <Compass className="size-4 text-pink-400" /> RECOMMENDED INVESTIGATION PROMPTS
            </span>
            <p className="text-[11px] text-slate-400">Click any prompt to send query directly</p>
          </div>

          <div className="space-y-2">
            {SUGGESTIONS.map((sug) => (
              <button
                key={sug}
                onClick={() => handleSend(sug)}
                className="w-full text-left p-3 rounded-lg border border-slate-800 bg-slate-950 text-xs text-slate-300 hover:border-pink-500/40 hover:bg-slate-900 hover:text-white transition group"
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium line-clamp-2">{sug}</span>
                  <ArrowRight className="size-3.5 text-slate-500 group-hover:text-pink-400 shrink-0 ml-2" />
                </div>
              </button>
            ))}
          </div>

          <div className="flex-1 rounded-xl bg-slate-950 p-4 border border-slate-800 space-y-3 font-mono text-xs">
            <span className="text-emerald-400 font-bold flex items-center gap-1.5 text-xs">
              <Lock className="size-4" /> ZERO-HALLUCINATION GUARD
            </span>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Copilot responses are bounded within <code className="text-cyan-300">&lt;evidence_data_content&gt;</code> tags.
              Unsubstantiated claims trigger automated fallback: <em className="text-amber-300">"Insufficient evidence in dataset."</em>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
