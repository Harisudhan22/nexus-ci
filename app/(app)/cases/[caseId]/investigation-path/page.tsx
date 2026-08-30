import { getCase, listEntities } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { PathFinderWidget } from '@/components/path-finder-widget'
import { redirect } from 'next/navigation'

export default async function CasePathFinderPage({ params }: { params: Promise<{ caseId: string }> }) {
  const user = await requireUser()
  const { caseId } = await params
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  const entities = await listEntities(caseId)

  return (
    <div>
      <PageHeader
        eyebrow="Link Analysis"
        title="Evidence Path Finder"
        description="Trace evidence-supported connection routes and evaluate relationship strengths between any two entities."
      />
      <div className="p-6 max-w-4xl">
        <PathFinderWidget caseId={caseId} entities={entities} />
      </div>
    </div>
  )
}
