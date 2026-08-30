import Link from 'next/link'
import { Radar, ArrowUpRight } from 'lucide-react'
import { requireUser } from '@/lib/auth/session'
import { listCases, listFindings } from '@/lib/domain/store'
import { PageHeader } from '@/components/page-header'
import { ConfidenceMeter, SeverityBadge, StatusBadge } from '@/components/primitives'

export default async function FindingsPage() {
  const user = await requireUser()
  const cases = await listCases(user)
  const findingsByCase = await Promise.all(
    cases.map(async (caseItem) => ({
      caseItem,
      findings: await listFindings(caseItem.id),
    })),
  )
  const findings = findingsByCase
    .flatMap(({ caseItem, findings }) => findings.map((finding) => ({ finding, caseItem })))
    .sort((a, b) => b.finding.confidence - a.finding.confidence)

  return (
    <div>
      <PageHeader
        eyebrow="Analytical Review"
        title="Findings"
        description={`${findings.length} finding${findings.length === 1 ? '' : 's'} across accessible cases.`}
      />

      <div className="p-6">
        <section className="rounded-lg border border-border bg-card">
          <div className="flex items-center gap-2 border-b border-border px-5 py-4">
            <Radar className="size-4 text-warning" />
            <h2 className="text-sm font-semibold">Prioritized Signals</h2>
          </div>
          <ul className="divide-y divide-border">
            {findings.map(({ finding, caseItem }) => (
              <li key={finding.id}>
                <Link
                  href={`/cases/${finding.caseId}/findings`}
                  className="flex items-center gap-4 px-5 py-3.5 transition hover:bg-secondary/50"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityBadge severity={finding.severity} />
                      <span className="font-mono text-[10px] uppercase text-muted-foreground">{caseItem.id}</span>
                      <StatusBadge status={finding.status} />
                    </div>
                    <p className="mt-1 truncate text-sm font-medium">{finding.title}</p>
                    <p className="truncate text-xs text-muted-foreground">{finding.why}</p>
                  </div>
                  <div className="hidden w-28 shrink-0 sm:block">
                    <ConfidenceMeter value={finding.confidence} />
                  </div>
                  <ArrowUpRight className="size-4 shrink-0 text-muted-foreground" />
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </div>
  )
}
