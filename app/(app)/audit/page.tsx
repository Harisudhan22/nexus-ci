import { listAudit, listUsers } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { StatusBadge } from '@/components/primitives'
import { ScrollText, Filter, Calendar, ShieldCheck, Lock, CheckCircle2, Key, Database, Sparkles } from 'lucide-react'

export default async function GlobalAuditPage() {
  const user = await requireUser()
  const logs = await listAudit()
  const users = await listUsers()
  const userMap = new Map(users.map((u) => [u.id, u]))

  const ACTION_VERB: Record<string, string> = {
    LOGIN: 'Signed in session',
    UPLOAD: 'Ingested evidence file',
    VIEW: 'Viewed case context records',
    QUERY: 'Queried grounded Copilot RAG',
    FINDING_ACKNOWLEDGE: 'Updated case findings status',
    ENTITY_MERGE: 'Approved target entity resolution',
    ENTITY_REJECT: 'Rejected target entity resolution',
  }

  const trustBadges = [
    { title: 'RBAC Access Bounded', desc: 'Case-level role authorization enforced', icon: Lock, ok: true },
    { title: 'SHA-256 Hash Integrity', desc: 'Immutable document hash seals', icon: ShieldCheck, ok: true },
    { title: 'Zero-Hallucination Guard', desc: '<evidence_data_content> XML bounded', icon: CheckCircle2, ok: true },
    { title: 'Prompt-Injection Redaction', desc: 'Adversarial directive stripping', icon: Key, ok: true },
  ]

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      {/* Console Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-amber-400">
            IMMUTABLE SECURITY GOVERNANCE
          </span>
          <h1 className="text-xl font-extrabold text-white">Cryptographic Audit Ledger</h1>
          <p className="text-xs text-slate-400">
            Tamper-proof chronological trail of all user logins, evidence ingestion, entity merges, and Copilot queries.
          </p>
        </div>
      </div>

      {/* Security & Trust Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
        {trustBadges.map((b) => {
          const Icon = b.icon
          return (
            <div key={b.title} className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/90 flex items-center gap-3">
              <div className="size-9 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center shrink-0">
                <Icon className="size-4 text-amber-400" />
              </div>
              <div className="min-w-0">
                <span className="font-mono text-xs font-bold text-white block truncate">{b.title}</span>
                <span className="text-[10px] text-slate-400 block truncate">{b.desc}</span>
              </div>
            </div>
          )
        })}
      </div>

      {/* Audit Log Table */}
      <div className="rounded-xl border border-slate-800 bg-slate-900/90 shadow-xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 flex items-center justify-between font-mono text-xs">
          <span className="font-bold text-white flex items-center gap-2">
            <ScrollText className="size-4 text-amber-400" /> RECENT AUDIT LEDGER ENTRIES ({logs.length})
          </span>
        </div>

        {logs.length === 0 ? (
          <div className="p-12 text-center text-slate-500 font-mono text-xs">
            No audit ledger entries logged.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="border-b border-slate-800 bg-slate-950 text-[10px] font-bold text-slate-400 uppercase">
                  <th className="px-4 py-3">Timestamp</th>
                  <th className="px-4 py-3">Actor / User</th>
                  <th className="px-4 py-3">Action</th>
                  <th className="px-4 py-3">Resource Target</th>
                  <th className="px-4 py-3">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/80 bg-slate-950/40">
                {logs.map((log) => {
                  const actor = userMap.get(log.userId)
                  return (
                    <tr key={log.id} className="hover:bg-slate-900/60 transition">
                      <td className="px-4 py-3 text-slate-400 whitespace-nowrap">
                        {new Date(log.timestamp).toLocaleString('en-GB', {
                          day: '2-digit',
                          month: 'short',
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-cyan-500/20 text-[9px] font-bold text-cyan-400 border border-cyan-500/40">
                            {actor?.name.split(' ').map((n) => n[0]).slice(-2).join('') || '??'}
                          </span>
                          <div>
                            <p className="font-bold text-white">{actor?.name || 'System Admin'}</p>
                            <p className="text-[9px] text-slate-500 uppercase">{actor?.role || 'SYSTEM'}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 font-bold text-amber-400">{log.action}</td>
                      <td className="px-4 py-3 text-slate-300 max-w-xs truncate">
                        <p className="font-semibold truncate">{ACTION_VERB[log.action] || log.action.toLowerCase()}</p>
                        <p className="text-[10px] text-slate-500 truncate">{log.resource}</p>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={log.result} />
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
