import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { Shield, Database, Cpu, Compass, Settings, CheckCircle2 } from 'lucide-react'

export default async function SettingsPage() {
  const user = await requireUser()

  const systemStatus = [
    { name: 'Core API Services', status: 'Operational', icon: Cpu, uri: 'http://localhost:8000/api' },
    { name: 'PostgreSQL Database', status: 'Operational', icon: Database, uri: 'postgresql://localhost:5432' },
    { name: 'Neo4j Graph Database', status: 'Operational', icon: Compass, uri: 'bolt://localhost:7687' },
  ]

  return (
    <div>
      <PageHeader
        eyebrow="System Configuration"
        title="Settings & System Diagnostics"
        description="Verify database connections, operational statuses, and current clearance configurations."
      />

      <div className="p-6 max-w-4xl space-y-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {/* Profile Details */}
          <section className="rounded-lg border border-border bg-card p-6 space-y-4">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <Shield className="size-4 text-primary" /> Investigator Profile
            </h2>
            <dl className="space-y-3 text-xs leading-relaxed">
              <div className="flex justify-between border-b border-border pb-2">
                <dt className="text-muted-foreground">Full Name</dt>
                <dd className="font-semibold text-foreground">{user.name}</dd>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <dt className="text-muted-foreground">Email ID</dt>
                <dd className="font-semibold text-foreground font-mono">{user.email}</dd>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <dt className="text-muted-foreground">Officer Role</dt>
                <dd className="font-semibold text-foreground uppercase">{user.role}</dd>
              </div>
              <div className="flex justify-between border-b border-border pb-2">
                <dt className="text-muted-foreground">Access Scope</dt>
                <dd className="font-semibold text-foreground">{user.agency}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-muted-foreground">Clearance level</dt>
                <dd className="font-semibold text-warning">{user.clearance}</dd>
              </div>
            </dl>
          </section>

          {/* System Diagnostics */}
          <section className="rounded-lg border border-border bg-card p-6 space-y-4">
            <h2 className="text-sm font-semibold flex items-center gap-2">
              <Settings className="size-4 text-primary" /> Core Service Connectors
            </h2>
            <ul className="space-y-4">
              {systemStatus.map((srv) => {
                const Icon = srv.icon
                return (
                  <li key={srv.name} className="flex items-center gap-3">
                    <span className="flex size-9 items-center justify-center rounded-md border border-border bg-secondary/35 text-muted-foreground">
                      <Icon className="size-4" />
                    </span>
                    <div className="min-w-0 flex-1 leading-snug">
                      <p className="text-xs font-semibold text-foreground">{srv.name}</p>
                      <p className="text-[10px] text-muted-foreground font-mono truncate mt-0.5">{srv.uri}</p>
                    </div>
                    <span className="flex items-center gap-1 text-[10px] font-bold text-success bg-success/5 border border-success/20 px-2 py-0.5 rounded">
                      <CheckCircle2 className="size-3" />
                      {srv.status}
                    </span>
                  </li>
                )
              })}
            </ul>
          </section>
        </div>
      </div>
    </div>
  )
}
