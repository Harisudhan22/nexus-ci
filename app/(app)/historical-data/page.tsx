import { requireUser } from "@/lib/auth/session"
import { PageHeader } from "@/components/page-header"
import { SyncInterface } from "./sync-interface"

export default async function HistoricalDataPage() {
  // Ensure user is authenticated
  await requireUser()

  return (
    <div>
      <PageHeader
        eyebrow="Integrations"
        title="Historical Data Sync"
        description="Connect with mock external systems to import structural and unstructured case records."
      />
      <div className="p-6">
        <SyncInterface />
      </div>
    </div>
  )
}
