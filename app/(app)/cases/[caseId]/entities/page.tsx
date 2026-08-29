import { listEntities, listResolutionCandidates, getCase } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { EntitiesResolver } from '@/components/entities-resolver'
import { redirect } from 'next/navigation'

export default async function CaseEntitiesPage({ params }: { params: { caseId: string } }) {
  const user = await requireUser()
  const caseId = params.caseId
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  const entities = await listEntities(caseId)
  const candidates = await listResolutionCandidates(caseId)

  return (
    <div>
      <PageHeader
        eyebrow="Intelligence Database"
        title="Entity Registry & Resolution"
        description="Verify resolved identities and reconcile surface-level name variations under human supervision."
      />
      <EntitiesResolver 
        caseId={caseId} 
        initialEntities={entities} 
        initialCandidates={candidates} 
      />
    </div>
  )
}
