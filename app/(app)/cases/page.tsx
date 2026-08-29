import { requireUser } from "@/lib/auth/session"
import { listCases } from "@/lib/domain/store"
import { PageHeader } from "@/components/page-header"
import { CasesBrowser } from "@/components/cases-browser"

export default async function CasesPage() {
  const user = await requireUser()
  const cases = listCases(user)

  return (
    <div>
      <PageHeader
        eyebrow="Workspace"
        title="Case Registry"
        description={`${cases.length} case${cases.length === 1 ? "" : "s"} within your clearance and access scope.`}
      />
      <CasesBrowser cases={cases} />
    </div>
  )
}
