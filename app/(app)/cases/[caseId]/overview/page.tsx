import { getCase, caseStats } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { StatCard, SeverityBadge, StatusBadge } from '@/components/primitives'
import { ShieldCheck, Calendar, User, Building, FolderGit, Users, FileStack, Radar, Layers } from 'lucide-react'
import { redirect } from 'next/navigation'

export default async function CaseOverviewPage({ params }: { params: { caseId: string } }) {
  const user = await requireUser()
  const caseId = params.caseId
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  const stats = await caseStats(caseId)

  return (
    <div>
      <PageHeader
        eyebrow="Case Context"
        title={dbCase.title}
        description={`Active investigation metadata under ${dbCase.agency}.`}
      />

      <div className="space-y-6 p-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <StatCard label="Resolved Entities" value={stats.entities} icon={<Users className="size-4" />} />
          <StatCard label="Evidence Uploads" value={stats.evidence} icon={<FileStack className="size-4" />} />
          <StatCard label="Analytical Findings" value={stats.findings} tone="warning" icon={<Radar className="size-4" />} />
          <StatCard label="Cross-Case Recurrences" value={stats.crossCaseLinks} tone="danger" icon={<Layers className="size-4" />} />
        </div>

        {/* Metadata Details */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <section className="rounded-lg border border-border bg-card p-6 lg:col-span-2">
            <h2 className="text-sm font-semibold mb-4">Investigation Details</h2>
            <p className="text-sm leading-relaxed text-muted-foreground whitespace-pre-wrap">
              {dbCase.description || 'No detailed case brief provided.'}
            </p>
          </section>

          <section className="rounded-lg border border-border bg-card p-6">
            <h2 className="text-sm font-semibold mb-4">Classification & Scope</h2>
            <dl className="space-y-4 text-sm">
              <div className="flex items-center justify-between border-b border-border pb-2">
                <dt className="flex items-center gap-2 text-muted-foreground">
                  <ShieldCheck className="size-4 text-warning" />
                  Clearance Level
                </dt>
                <dd className="font-semibold text-warning">{dbCase.classification}</dd>
              </div>

              <div className="flex items-center justify-between border-b border-border pb-2">
                <dt className="flex items-center gap-2 text-muted-foreground">
                  <User className="size-4 text-primary" />
                  Assigned To
                </dt>
                <dd className="font-semibold">{dbCase.assignedTo || 'Unassigned'}</dd>
              </div>

              <div className="flex items-center justify-between border-b border-border pb-2">
                <dt className="flex items-center gap-2 text-muted-foreground">
                  <Building className="size-4 text-muted-foreground" />
                  Agency Scope
                </dt>
                <dd className="text-muted-foreground">{dbCase.agency}</dd>
              </div>

              <div className="flex items-center justify-between border-b border-border pb-2">
                <dt className="flex items-center gap-2 text-muted-foreground">
                  <FolderGit className="size-4 text-muted-foreground" />
                  Priority
                </dt>
                <dd><SeverityBadge severity={dbCase.priority} /></dd>
              </div>

              <div className="flex items-center justify-between">
                <dt className="flex items-center gap-2 text-muted-foreground">
                  <Calendar className="size-4 text-muted-foreground" />
                  Status
                </dt>
                <dd><StatusBadge status={dbCase.status} /></dd>
              </div>
            </dl>
          </section>
        </div>
      </div>
    </div>
  )
}
