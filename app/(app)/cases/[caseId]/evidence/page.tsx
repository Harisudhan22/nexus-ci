import { listEvidence, getCase } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { EvidenceManager } from '@/components/evidence-manager'
import { redirect } from 'next/navigation'

export default async function CaseEvidencePage({ params }: { params: { caseId: string } }) {
  const user = await requireUser()
  const caseId = params.caseId
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  const evidence = await listEvidence(caseId)

  return (
    <div>
      <PageHeader
        eyebrow="Evidence Locker"
        title="Case Files & Documents"
        description="Ingest and review transcripts, transaction ledgers, CDR records, and PDFs."
      />
      <EvidenceManager caseId={caseId} initialEvidence={evidence} />
    </div>
  )
}
