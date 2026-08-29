import { listTimeline, getCase } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { Phone, ArrowRightLeft, FileText, Calendar, Compass, AlertCircle } from 'lucide-react'
import { redirect } from 'next/navigation'

export default async function CaseTimelinePage({ params }: { params: { caseId: string } }) {
  const user = await requireUser()
  const caseId = params.caseId
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  const events = await listTimeline(caseId)

  const getIcon = (type: string) => {
    switch (type) {
      case 'call':
        return <Phone className="size-4 text-primary" />
      case 'transfer':
        return <ArrowRightLeft className="size-4 text-warning" />
      case 'document':
        return <FileText className="size-4 text-success" />
      default:
        return <Compass className="size-4 text-muted-foreground" />
    }
  }

  return (
    <div>
      <PageHeader
        eyebrow="Sequence of Events"
        title="Analytical Chronology Timeline"
        description="Factual events compiled chronologically from ingested logs, phone records, and financial transfers."
      />

      <div className="p-6 max-w-4xl">
        {events.length === 0 ? (
          <div className="rounded-lg border border-dashed border-border py-16 text-center bg-card">
            <Calendar className="size-8 text-muted-foreground mx-auto mb-2 opacity-50" />
            <p className="text-sm text-muted-foreground">No chronological events registered for this case yet.</p>
          </div>
        ) : (
          <div className="relative pl-6 border-l border-border space-y-6 ml-4">
            {events.map((evt) => (
              <div key={evt.id} className="relative">
                {/* Node Dot Icon */}
                <div className="absolute -left-[37px] top-1 flex size-7 items-center justify-center rounded-full border border-border bg-card shadow-sm">
                  {getIcon(evt.type)}
                </div>

                <div className="rounded-lg border border-border bg-card p-4 space-y-2 hover:border-primary/45 transition">
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span className="font-mono text-[10px] bg-secondary px-1.5 py-0.5 rounded border border-border">
                      {evt.type.toUpperCase()}
                    </span>
                    <time className="font-mono">{new Date(evt.timestamp).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</time>
                  </div>

                  <h3 className="text-sm font-semibold">{evt.title}</h3>

                  <div className="flex items-center justify-between text-[11px] pt-2 border-t border-border/60">
                    <span className="text-muted-foreground">
                      Evidence Ref:{' '}
                      <span className="font-mono text-primary font-bold">{evt.evidenceId}</span>
                    </span>
                    {evt.entityIds.length > 0 && (
                      <span className="text-[10px] text-muted-foreground italic">
                        Links: {evt.entityIds.join(', ')}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
