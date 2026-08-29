import Link from 'next/link'
import {
  ArrowUpRight,
  Boxes,
  CheckCircle2,
  Cpu,
  Database,
  FileStack,
  GitMerge,
  Layers,
  Radar,
  ShieldAlert,
  Users,
} from 'lucide-react'
import { getSessionUser } from '@/lib/auth/session'
import {
  listAudit,
  listCases,
  listCrossCaseLinks,
  listEntities,
  listEvidence,
  listFindings,
  listResolutionCandidates,
  getUser,
} from '@/lib/domain/store'
import { PageHeader } from '@/components/page-header'
import { ActivityChart } from '@/components/activity-chart'
import { ConfidenceMeter, EntityBadge, SeverityBadge, StatCard, StatusBadge } from '@/components/primitives'

const ACTION_VERB: Record<string, string> = {
  LOGIN: 'signed in',
  UPLOAD: 'uploaded evidence',
  VIEW: 'viewed',
  QUERY: 'queried Copilot',
  FINDING_ACKNOWLEDGE: 'acknowledged a finding',
  ENTITY_MERGE: 'merged an entity',
  ENTITY_REJECT: 'rejected a merge',
}

export default async function DashboardPage() {
  const user = (await getSessionUser())!
  const cases = listCases(user)
  const caseIds = cases.map((c) => c.id)

  const entities = listEntities().filter((e) => e.caseIds.some((c) => caseIds.includes(c)))
  const evidence = listEvidence().filter((e) => caseIds.includes(e.caseId))
  const findings = listFindings().filter((f) => caseIds.includes(f.caseId))
  const highFindings = findings.filter((f) => f.severity === 'high')
  const crossLinks = listCrossCaseLinks().filter((l) => l.caseIds.some((c) => caseIds.includes(c)))
  const pendingMerges = listResolutionCandidates().filter(
    (c) => c.status === 'pending' && caseIds.includes(c.caseId),
  )
  const audit = listAudit()
    .filter((a) => !a.caseId || caseIds.includes(a.caseId))
    .slice(0, 6)

  const topFindings = [...findings].sort((a, b) => b.confidence - a.confidence).slice(0, 4)

  const health = [
    { label: 'Evidence ingestion', status: 'Operational', tone: 'success' as const, icon: Database },
    { label: 'AI processing', status: 'Operational', tone: 'success' as const, icon: Cpu },
    { label: 'Graph service', status: 'Operational', tone: 'success' as const, icon: GitMerge },
    { label: 'Data freshness', status: 'Updated 12m ago', tone: 'success' as const, icon: Layers },
  ]

  return (
    <div>
      <PageHeader
        eyebrow="Operations Overview"
        title={`Welcome back, ${user.name.split(' ').slice(-1)[0]}`}
        description="What needs your attention across your assigned cases."
        actions={
          <Link
            href="/cases"
            className="flex h-9 items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground transition hover:opacity-90"
          >
            <Boxes className="size-4" />
            View cases
          </Link>
        }
      />

      <div className="space-y-6 p-6">
        {/* KPI cards */}
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
          <StatCard label="Active cases" value={cases.filter((c) => c.status === 'active').length} hint={`${cases.length} accessible`} icon={<Boxes className="size-4" />} />
          <StatCard label="Total entities" value={entities.length} hint="resolved & canonical" icon={<Users className="size-4" />} />
          <StatCard label="High-priority findings" value={highFindings.length} hint="need triage" tone="danger" icon={<ShieldAlert className="size-4" />} />
          <StatCard label="Cross-case links" value={crossLinks.length} hint="recurring entities" tone="warning" icon={<Layers className="size-4" />} />
          <StatCard label="Pending merges" value={pendingMerges.length} hint="await review" tone="warning" icon={<GitMerge className="size-4" />} />
          <StatCard label="Evidence files" value={evidence.length} hint="ingested" icon={<FileStack className="size-4" />} />
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Activity */}
          <section className="rounded-lg border border-border bg-card p-5 lg:col-span-2">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <h2 className="text-sm font-semibold">Investigative activity</h2>
                <p className="text-xs text-muted-foreground">Analyses and uploads over the month</p>
              </div>
              <div className="flex items-center gap-3 text-[11px] text-muted-foreground">
                <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-primary" />Analyses</span>
                <span className="flex items-center gap-1.5"><span className="size-2 rounded-sm bg-chart-2" />Uploads</span>
              </div>
            </div>
            <ActivityChart />
          </section>

          {/* Network overview */}
          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-sm font-semibold">Network overview</h2>
            <p className="text-xs text-muted-foreground">Across accessible cases</p>
            <dl className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <dt className="text-sm text-muted-foreground">Entities</dt>
                <dd className="tabular text-sm font-semibold">{entities.length}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-sm text-muted-foreground">Relationships</dt>
                <dd className="tabular text-sm font-semibold">21</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-sm text-muted-foreground">Major clusters</dt>
                <dd className="tabular text-sm font-semibold">2</dd>
              </div>
            </dl>
            <div className="mt-4 border-t border-border pt-4">
              <p className="mb-2 text-xs text-muted-foreground">Cross-case recurrence</p>
              <ul className="space-y-2">
                {crossLinks.slice(0, 3).map((l) => (
                  <li key={l.id} className="flex items-center justify-between gap-2">
                    <EntityBadge type={l.type} label={l.label} />
                    <span className="tabular text-[11px] text-warning">{l.confidence}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>
        </div>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {/* Priority findings */}
          <section className="rounded-lg border border-border bg-card lg:col-span-2">
            <div className="flex items-center justify-between border-b border-border px-5 py-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold">
                <Radar className="size-4 text-warning" />
                Priority findings
              </h2>
              <span className="text-[11px] text-muted-foreground">Analytical signals, not determinations</span>
            </div>
            <ul className="divide-y divide-border">
              {topFindings.map((f) => (
                <li key={f.id}>
                  <Link
                    href={`/cases/${f.caseId}/findings`}
                    className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-secondary/50"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={f.severity} />
                        <span className="font-mono text-[10px] uppercase text-muted-foreground">{f.caseId}</span>
                      </div>
                      <p className="mt-1 truncate text-sm font-medium">{f.title}</p>
                      <p className="truncate text-xs text-muted-foreground">{f.why}</p>
                    </div>
                    <div className="hidden w-28 shrink-0 sm:block">
                      <ConfidenceMeter value={f.confidence} />
                    </div>
                    <ArrowUpRight className="size-4 shrink-0 text-muted-foreground" />
                  </Link>
                </li>
              ))}
            </ul>
          </section>

          {/* System health */}
          <section className="rounded-lg border border-border bg-card p-5">
            <h2 className="text-sm font-semibold">System health</h2>
            <ul className="mt-4 space-y-3">
              {health.map(({ label, status, icon: Icon }) => (
                <li key={label} className="flex items-center gap-3">
                  <span className="flex size-8 items-center justify-center rounded-md border border-border bg-elevated text-muted-foreground">
                    <Icon className="size-4" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium">{label}</p>
                    <p className="flex items-center gap-1 text-[11px] text-success">
                      <CheckCircle2 className="size-3" />
                      {status}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* Recent activity */}
        <section className="rounded-lg border border-border bg-card">
          <div className="border-b border-border px-5 py-4">
            <h2 className="text-sm font-semibold">Recent activity</h2>
          </div>
          <ul className="divide-y divide-border">
            {audit.map((a) => {
              const actor = getUser(a.userId)
              return (
                <li key={a.id} className="flex items-center gap-3 px-5 py-3 text-sm">
                  <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-secondary text-[10px] font-medium text-muted-foreground">
                    {actor?.name.split(' ').map((n) => n[0]).slice(-2).join('') ?? '??'}
                  </span>
                  <p className="min-w-0 flex-1 truncate">
                    <span className="font-medium">{actor?.name ?? 'Unknown'}</span>{' '}
                    <span className="text-muted-foreground">
                      {ACTION_VERB[a.action] ?? a.action.toLowerCase()} · {a.resource}
                    </span>
                  </p>
                  <StatusBadge status={a.result} />
                  <time className="shrink-0 text-[11px] text-muted-foreground">
                    {new Date(a.timestamp).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })}
                  </time>
                </li>
              )
            })}
          </ul>
        </section>
      </div>
    </div>
  )
}
