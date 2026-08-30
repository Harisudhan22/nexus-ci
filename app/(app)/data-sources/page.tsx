import { requireUser } from "@/lib/auth/session"
import { PageHeader } from "@/components/page-header"
import { listDataSources } from "@/lib/domain/store"
import {
  Database,
  Radio,
  FileText,
  Phone,
  CreditCard,
  ShieldCheck,
  CheckCircle2,
  ExternalLink,
  RefreshCw,
  Layers
} from "lucide-react"

export default async function DataSourcesPage() {
  await requireUser()
  const sources = await listDataSources()

  return (
    <div>
      <PageHeader
        eyebrow="Integration Infrastructure"
        title="Multi-Source Data Adapters"
        description="Active ingestion adapters connecting police records, telecom CDRs, financial ledgers, surveillance, and open-source intelligence."
      />

      <div className="p-6 space-y-6">
        <div className="rounded-lg border border-border bg-card shadow-sm overflow-hidden">
          <div className="p-4 border-b border-border bg-muted/20 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Registered Source Adapters</h3>
              <p className="text-xs text-muted-foreground">Standardized multi-source ingestion pipeline converting raw feeds into Common Internal Records</p>
            </div>
            <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-500 border border-emerald-500/20 flex items-center gap-1.5">
              <CheckCircle2 className="size-3.5" /> All 9 Adapters Active
            </span>
          </div>

          <div className="divide-y divide-border">
            {sources.map((src) => (
              <div key={src.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-muted/10 transition">
                <div className="flex items-start gap-3.5">
                  <div className="p-2.5 rounded-lg bg-primary/10 text-primary shrink-0">
                    <Database className="size-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-semibold text-foreground">{src.name}</h4>
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-muted text-muted-foreground border border-border">
                        {src.category}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Ingestion Mode: <span className="font-mono text-foreground">{src.mode}</span> • Records Processed: <span className="font-semibold text-foreground">{src.records}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3 self-end sm:self-center">
                  <span className="flex items-center gap-1.5 text-xs text-emerald-500 font-medium">
                    <span className="size-2 rounded-full bg-emerald-500 animate-pulse" />
                    {src.status}
                  </span>
                  <a
                    href="/historical-data"
                    className="px-3 py-1.5 rounded-md border border-border bg-background hover:bg-muted text-xs font-medium transition flex items-center gap-1"
                  >
                    Sync / Test <ExternalLink className="size-3 ml-1" />
                  </a>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
