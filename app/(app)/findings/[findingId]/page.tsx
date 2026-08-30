import { listFindings } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { redirect } from 'next/navigation'

export default async function FindingDetailPage({ params }: { params: Promise<{ findingId: string }> }) {
  const user = await requireUser()
  const { findingId } = await params
  
  // Find case ID associated with this finding
  let caseId = 'case-101'
  try {
    const allFindings = await listFindings(caseId) // check case-101 first
    const match = allFindings.find(f => f.id === findingId)
    if (match) {
      caseId = match.caseId
    } else {
      // check case-205
      const allFindings205 = await listFindings('case-205')
      const match205 = allFindings205.find(f => f.id === findingId)
      if (match205) {
        caseId = match205.caseId
      }
    }
  } catch (err) {
    console.error(err)
  }

  // Redirect to the case findings page which contains full context and drawers
  redirect(`/cases/${caseId}/findings`)
}
