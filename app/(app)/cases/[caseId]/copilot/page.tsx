import { getCase } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { CopilotChat } from '@/components/copilot-chat'
import { redirect } from 'next/navigation'

export default async function CaseCopilotPage({ params }: { params: Promise<{ caseId: string }> }) {
  const user = await requireUser()
  const { caseId } = await params
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  return (
    <div>
      <PageHeader
        eyebrow="AI Assistant"
        title="Grounded Investigator Copilot"
        description="Ask questions about suspects, call logs, or financial chains. Answers are strictly bounded by case evidence."
      />
      <CopilotChat caseId={caseId} />
    </div>
  )
}
