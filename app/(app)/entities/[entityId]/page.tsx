import { getEntity, listCases } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { PageHeader } from '@/components/page-header'
import { EntityBadge } from '@/components/primitives'
import { User, Tag, Calendar, Database, Compass, Route } from 'lucide-react'
import Link from 'next/link'
import { redirect } from 'next/navigation'

export default async function EntityDetailPage({ params }: { params: Promise<{ entityId: string }> }) {
  const user = await requireUser()
  const { entityId } = await params
  const entity = await getEntity(entityId)

  if (!entity) {
    redirect('/cases')
  }

  // Find overlapping case names
  const cases = await listCases(user)
  const linkedCases = cases.filter(c => entity.caseIds.includes(c.id))

  return (
    <div>
      <PageHeader
        eyebrow="Resolved Target Profiling"
        title={entity.label}
        description={`Analytical records and alias resolving metrics for canonical node ${entity.id}.`}
      />

      <div className="p-6 max-w-4xl space-y-6">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {/* Metadata Cards */}
          <section className="rounded-lg border border-border bg-card p-5 space-y-4 md:col-span-2">
            <div className="flex items-center justify-between border-b border-border pb-2">
              <h2 className="text-sm font-semibold">Profile Overview</h2>
              <EntityBadge type={entity.type} />
            </div>

            {entity.aliases.length > 0 && (
              <div className="space-y-1.5">
                <span className="text-[10px] uppercase text-muted-foreground font-semibold block">Recognized Surface Mentions</span>
                <div className="flex flex-wrap gap-1.5">
                  {entity.aliases.map(a => (
                    <span key={a} className="px-2 py-0.5 text-xs rounded border border-border bg-secondary font-mono text-muted-foreground">{a}</span>
                  ))}
                </div>
              </div>
            )}

            <div className="space-y-1.5 pt-2">
              <span className="text-[10px] uppercase text-muted-foreground font-semibold block">Extracted Attributes</span>
              <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                {Object.entries(entity.attributes).map(([k, v]) => (
                  <div key={k} className="flex flex-col border-b border-border/40 pb-1.5">
                    <dt className="text-muted-foreground font-medium">{k}</dt>
                    <dd className="font-semibold text-foreground mt-0.5 font-mono">{String(v)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </section>

          {/* Quick Case links & Actions */}
          <section className="rounded-lg border border-border bg-card p-5 space-y-4">
            <h2 className="text-sm font-semibold border-b border-border pb-2">Connected Cases</h2>
            <ul className="space-y-2 text-xs">
              {linkedCases.map(c => (
                <li key={c.id}>
                  <Link 
                    href={`/cases/${c.id}/overview`}
                    className="flex flex-col p-2.5 rounded border border-border bg-secondary/20 hover:border-primary/50 hover:bg-secondary/40 transition"
                  >
                    <span className="font-mono text-[9px] text-primary uppercase font-bold">{c.id}</span>
                    <span className="font-semibold truncate mt-0.5">{c.title}</span>
                  </Link>
                </li>
              ))}
            </ul>

            <div className="pt-2">
              <Link
                href={`/cases/${entity.caseIds[0]}/network`}
                className="flex items-center justify-center gap-1.5 w-full h-8 rounded bg-primary text-xs font-semibold text-primary-foreground hover:opacity-90 transition"
              >
                <Compass className="size-3.5" />
                View Graph Context
              </Link>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
