import { listAudit, listUsers } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { StatusBadge } from '@/components/primitives'
import { ScrollText, Filter, Calendar, ShieldCheck } from 'lucide-react'

export default async function GlobalAuditPage() {
  const user = await requireUser()
  const logs = await listAudit()
  const users = await listUsers()
  const userMap = new Map(users.map(u => [u.id, u]))

  const ACTION_VERB: Record<string, string> = {
    LOGIN: 'Signed in session',
    UPLOAD: 'Ingested evidence file',
    VIEW: 'Viewed case context records',
    QUERY: 'Queried grounded Copilot RAG',
    FINDING_ACKNOWLEDGE: 'Updated case findings status',
    ENTITY_MERGE: 'Approved target entity resolution',
    ENTITY_REJECT: 'Rejected target entity resolution',
  }

  return (
    <div>
      <PageHeader
        eyebrow="Security Operations"
        title="Access & Modification Audit Logs"
        description="Tamper-proof chronological trail of all user logins, evidence ingestion, graph resolving merges, and Copilot queries."
      />

      <div className="p-6 max-w-5xl space-y-4">
        {logs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border py-16 text-center bg-card">
            <ScrollText className="size-8 text-muted-foreground mx-auto mb-2 opacity-50" />
            <p className="text-sm text-muted-foreground">Audit log registry is currently empty.</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border bg-card">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="border-b border-border bg-secondary/15 text-xs font-semibold text-muted-foreground uppercase">
                  <th className="px-5 py-3 font-medium">Timestamp</th>
                  <th className="px-5 py-3 font-medium">User Actor</th>
                  <th className="px-5 py-3 font-medium">Action</th>
                  <th className="px-5 py-3 font-medium">Resource Target</th>
                  <th className="px-5 py-3 font-medium">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {logs.map((log) => {
                  const actor = userMap.get(log.userId)
                  return (
                    <tr key={log.id} className="hover:bg-secondary/10 transition">
                      <td className="px-5 py-3.5 font-mono text-xs text-muted-foreground">
                        {new Date(log.timestamp).toLocaleString('en-GB', { 
                          day: '2-digit', 
                          month: 'short', 
                          hour: '2-digit', 
                          minute: '2-digit',
                          second: '2-digit'
                        })}
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-2">
                          <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-secondary text-[9px] font-bold text-muted-foreground">
                            {actor?.name.split(' ').map(n => n[0]).slice(-2).join('') || '??'}
                          </span>
                          <div className="leading-tight">
                            <p className="text-xs font-semibold">{actor?.name || 'System Admin'}</p>
                            <p className="text-[9px] text-muted-foreground font-mono uppercase">{actor?.role || 'SYSTEM'}</p>
                          </div>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 font-semibold text-primary/90 text-xs">
                        {log.action}
                      </td>
                      <td className="px-5 py-3.5 leading-tight max-w-xs truncate">
                        <p className="font-semibold text-xs truncate">{ACTION_VERB[log.action] || log.action.toLowerCase()}</p>
                        <p className="text-[10px] text-muted-foreground font-mono mt-0.5 truncate">{log.resource}</p>
                      </td>
                      <td className="px-5 py-3.5">
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
