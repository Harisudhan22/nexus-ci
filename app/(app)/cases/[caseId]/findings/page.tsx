import { listFindings, getCase } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { FindingsManager } from '@/components/findings-manager'
import { redirect } from 'next/navigation'

export default async function CaseFindingsPage({ params }: { params: Promise<{ caseId: string }> }) {
  const user = await requireUser()
  const { caseId } = await params
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  const findings = await listFindings(caseId)

  return (
    <div>
      <PageHeader
        eyebrow="Intelligence Alerts"
        title="Analytical Case Findings"
        description="Review automated graph patterns, communication spikes, and potential transaction bridge anomalies."
      />
      <FindingsManager caseId={caseId} initialFindings={findings} />
    </div>
  )
}
