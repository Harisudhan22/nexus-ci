import { getCase } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { NetworkViewer } from '@/components/network-viewer'
import { redirect } from 'next/navigation'

export default async function CaseNetworkPage({ params }: { params: { caseId: string } }) {
  const user = await requireUser()
  const caseId = params.caseId
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  return (
    <div className="h-full">
      <NetworkViewer caseId={caseId} />
    </div>
  )
}
