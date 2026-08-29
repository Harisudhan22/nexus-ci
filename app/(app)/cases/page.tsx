import { requireUser } from "@/lib/auth/session"
import { listCases, caseStats, listUsers } from "@/lib/domain/store"
import { PageHeader } from "@/components/page-header"
import { CasesBrowser } from "@/components/cases-browser"

export default async function CasesPage() {
  const user = await requireUser()
  const cases = await listCases(user)
  const users = await listUsers()

  // Resolve case metadata and assignee name mapping in parallel
  const items = await Promise.all(
    cases.map(async (c) => {
      const stats = await caseStats(c.id)
      const assigneeUser = users.find((u) => u.id === c.assignedTo)
      return {
        c,
        stats,
        assignee: assigneeUser ? assigneeUser.name : undefined,
      }
    })
  )

  return (
    <div>
      <PageHeader
        eyebrow="Workspace"
        title="Case Registry"
        description={`${cases.length} case${cases.length === 1 ? "" : "s"} within your clearance and access scope.`}
      />
      <CasesBrowser items={items} />
    </div>
  )
}
