'use client'

import { useState } from 'react'
import { Bot, User, Send, Compass, ShieldAlert, Sparkles, RefreshCw } from 'lucide-react'
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
  }
}

const SUGGESTIONS = [
  "Why is Ravi Kumar considered important?",
  "How is Ravi connected to Account X?",
  "Tell me about the vehicle seen at Central Station."
]

export function CopilotChat({ caseId }: { caseId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: "Hello. I am your evidence-grounded investigator assistant. I will retrieve relevant entities, network connections, and document texts from this case context to answer your queries with strict factual validation. How can I assist you?"
    }
  ])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async (text: string) => {
    if (!text.trim() || loading) return

    // Add user message
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setQuery('')
    setLoading(true)

    try {
      const res = await fetch(`/api/copilot/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ case_id: caseId, question: text })
      })

      if (res.ok) {
        const data = await res.json()
        setMessages(prev => [...prev, { role: 'assistant', structured: data }])
      } else {
        const err = await res.json().catch(() => ({}))
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: err.detail || "I encountered an error querying the analytical services."
        }])
      }
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: "Failed to communicate with the Copilot backend. Ensure the server is online."
      }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] max-w-4xl mx-auto border border-border rounded-lg bg-card overflow-hidden my-4 shadow-sm">
      {/* Messages Window */}
      <div className="flex-1 overflow-y-auto p-5 space-y-4 min-h-0 bg-surface/30">
        {messages.map((msg, idx) => (
          <div 
            key={idx} 
            className={cn(
              "flex gap-3 text-sm max-w-3xl",
              msg.role === 'user' ? "ml-auto flex-row-reverse" : "mr-auto"
            )}
          >
            {/* Avatar */}
            <div className={cn(
              "flex size-8 shrink-0 items-center justify-center rounded-full border",
              msg.role === 'user' ? "border-primary/20 bg-primary/10 text-primary" : "border-border bg-card text-muted-foreground"
            )}>
              {msg.role === 'user' ? <User className="size-4" /> : <Bot className="size-4 text-primary" />}
            </div>

            {/* Content */}
            <div className={cn(
              "rounded-lg p-4 space-y-3 leading-relaxed",
              msg.role === 'user' ? "bg-primary text-primary-foreground font-semibold" : "bg-card border border-border text-foreground"
            )}>
              {msg.content && <p>{msg.content}</p>}

              {msg.structured && (
                <div className="space-y-4">
                  <div>
                    <span className="text-[10px] font-bold text-primary uppercase block mb-1">Grounded Summary</span>
                    <p className="text-sm font-semibold">{msg.structured.summary}</p>
                  </div>

                  {msg.structured.key_reasons.length > 0 && (
                    <div>
                      <span className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">Key Factors</span>
                      <ul className="list-disc pl-4 space-y-1 text-xs text-muted-foreground">
                        {msg.structured.key_reasons.map((r, i) => <li key={i}>{r}</li>)}
                      </ul>
                    </div>
                  )}

                  {msg.structured.observed_evidence.length > 0 && (
                    <div>
                      <span className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">Observed Facts</span>
                      <ul className="list-disc pl-4 space-y-1 text-xs text-muted-foreground">
                        {msg.structured.observed_evidence.map((o, i) => <li key={i}>{o}</li>)}
                      </ul>
                    </div>
                  )}

                  {msg.structured.analytical_interpretation.length > 0 && (
                    <div>
                      <span className="text-[10px] font-bold text-muted-foreground uppercase block mb-1">Analytical Interpretation</span>
                      <ul className="list-disc pl-4 space-y-1 text-xs text-muted-foreground">
                        {msg.structured.analytical_interpretation.map((int, i) => <li key={i}>{int}</li>)}
                      </ul>
                    </div>
                  )}

                  <div className="grid grid-cols-2 gap-4 pt-2 border-t border-border/70 text-xs">
                    <div>
                      <ConfidenceMeter value={msg.structured.confidence} />
                    </div>
                    <div>
                      <span className="text-[9px] uppercase text-muted-foreground font-bold block mb-1">Evidence Citations</span>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {msg.structured.supporting_evidence.map(cite => (
                          <span key={cite} className="px-1.5 py-0.5 rounded border border-primary/30 bg-primary/5 font-mono text-[9px] font-bold text-primary">
                            {cite}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-3 text-sm mr-auto">
            <div className="flex size-8 shrink-0 items-center justify-center rounded-full border border-border bg-card text-muted-foreground">
              <Bot className="size-4 text-primary animate-pulse" />
            </div>
            <div className="rounded-lg p-4 bg-card border border-border text-muted-foreground flex items-center gap-2">
              <RefreshCw className="size-3.5 animate-spin" />
              Retrieving grounded case records...
            </div>
          </div>
        )}
      </div>

      {/* Suggestion Chips */}
      {messages.length === 1 && (
        <div className="px-5 py-3 border-t border-border bg-card space-y-2">
          <span className="text-[9px] uppercase text-muted-foreground font-semibold flex items-center gap-1">
            <Sparkles className="size-3 text-warning" /> Suggested Queries
          </span>
          <div className="flex flex-wrap gap-2">
            {SUGGESTIONS.map(s => (
              <button
                key={s}
                onClick={() => handleSend(s)}
                className="h-7 px-3 text-xs border border-border rounded-full bg-surface hover:bg-secondary/40 text-muted-foreground hover:text-foreground transition"
              >
                {s}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Box */}
      <div className="p-3 border-t border-border bg-card">
        <form 
          onSubmit={(e) => { e.preventDefault(); handleSend(query); }}
          className="flex items-center gap-2"
        >
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={loading}
            placeholder="Query Copilot on entities, transactions, or communications..."
            className="flex-1 h-9 rounded-md border border-input bg-surface px-3 text-sm outline-none focus:border-primary/60"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="flex size-9 items-center justify-center rounded-md bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50"
            aria-label="Send query"
          >
            <Send className="size-4" />
          </button>
        </form>
      </div>
    </div>
  )
}
