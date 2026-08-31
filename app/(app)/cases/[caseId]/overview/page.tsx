import { getCase, caseStats, listEntities, listEvidence, listFindings } from '@/lib/domain/store'
import { requireUser } from '@/lib/auth/session'
import { StatCard, SeverityBadge, StatusBadge } from '@/components/primitives'
import { ShieldCheck, Calendar, User, Building, FolderGit, Users, FileStack, Radar, Layers, GitBranch, Route, Bot, Sparkles, ArrowRight } from 'lucide-react'
import { redirect } from 'next/navigation'
import Link from 'next/link'

export default async function CaseOverviewPage({ params }: { params: Promise<{ caseId: string }> }) {
  const user = await requireUser()
  const { caseId } = await params
  const dbCase = await getCase(caseId)

  if (!dbCase) {
    redirect('/cases')
  }

  const stats = await caseStats(caseId)
  const entities = await listEntities(caseId)
  const evidence = await listEvidence(caseId)
  const findings = await listFindings(caseId)

  return (
    <div className="space-y-6 p-6">
      {/* Workspace Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-800 pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-cyan-400">
              ACTIVE CASE WORKSPACE
            </span>
            <span className="font-mono text-xs font-bold text-white">{dbCase.id}</span>
          </div>
          <h1 className="text-2xl font-extrabold text-white">{dbCase.title}</h1>
          <p className="text-xs text-slate-400">{dbCase.agency} | Police Station: {dbCase.police_station || 'Central Station PS'}</p>
        </div>

        <div className="flex items-center gap-2">
          <Link
            href={`/cases/${caseId}/network`}
            className="flex items-center gap-1.5 rounded-lg bg-cyan-600 px-3.5 py-2 text-xs font-bold text-white shadow hover:bg-cyan-500 active:scale-95 transition"
          >
            <GitBranch className="size-4" /> Open Graph
          </Link>
          <Link
            href={`/cases/${caseId}/copilot`}
            className="flex items-center gap-1.5 rounded-lg border border-pink-500/40 bg-pink-500/10 px-3.5 py-2 text-xs font-bold text-pink-400 hover:bg-pink-500/20 active:scale-95 transition"
          >
            <Bot className="size-4" /> Ask Copilot
          </Link>
        </div>
      </div>

      {/* KPI Stats Bar */}
      <div className="grid grid-cols-2 gap-3.5 md:grid-cols-4">
        <StatCard label="Resolved Entities" value={stats.entities} icon={<Users className="size-4 text-emerald-400" />} />
        <StatCard label="Evidence Uploads" value={stats.evidence} icon={<FileStack className="size-4 text-cyan-400" />} />
        <StatCard label="Analytical Findings" value={stats.findings} tone="warning" icon={<Radar className="size-4 text-amber-400" />} />
        <StatCard label="Cross-Case Links" value={stats.crossCaseLinks} tone="danger" icon={<Layers className="size-4 text-rose-400" />} />
      </div>

      {/* 3-Pane Main Investigation Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        
        {/* LEFT PANE: Case Metadata & Scope (4 Cols) */}
        <div className="lg:col-span-4 rounded-xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 shadow-xl">
          <h2 className="text-sm font-bold text-white border-b border-slate-800 pb-2">Classification & Scope</h2>
          
          <dl className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
              <dt className="text-slate-400 flex items-center gap-1.5">
                <ShieldCheck className="size-3.5 text-amber-400" /> Clearance
              </dt>
              <dd className="font-bold text-amber-400">{dbCase.classification}</dd>
            </div>

            <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
              <dt className="text-slate-400 flex items-center gap-1.5">
                <User className="size-3.5 text-cyan-400" /> Assigned Lead
              </dt>
              <dd className="font-bold text-white">{dbCase.assignedTo || 'Lead Officer'}</dd>
            </div>

            <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
              <dt className="text-slate-400 flex items-center gap-1.5">
                <Building className="size-3.5 text-slate-400" /> Jurisdiction
              </dt>
              <dd className="text-slate-200">{dbCase.agency}</dd>
            </div>

            <div className="flex items-center justify-between border-b border-slate-800/60 pb-2">
              <dt className="text-slate-400 flex items-center gap-1.5">
                <FolderGit className="size-3.5 text-slate-400" /> Priority Level
              </dt>
              <dd><SeverityBadge severity={dbCase.priority} /></dd>
            </div>

            <div className="flex items-center justify-between">
              <dt className="text-slate-400 flex items-center gap-1.5">
                <Calendar className="size-3.5 text-slate-400" /> Status
              </dt>
              <dd><StatusBadge status={dbCase.status} /></dd>
            </div>
          </dl>

          <div className="pt-2 border-t border-slate-800">
            <span className="text-[10px] font-mono text-slate-400 uppercase block mb-1">CASE SUMMARY BRIEF</span>
            <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap font-sans">
              {dbCase.description || 'No detailed case brief provided.'}
            </p>
          </div>
        </div>

        {/* CENTER PANE: Quick Module Launcher & Evidence List (5 Cols) */}
        <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 shadow-xl">
          <h2 className="text-sm font-bold text-white border-b border-slate-800 pb-2">Investigation Modules</h2>

          <div className="grid grid-cols-2 gap-2.5 text-xs font-bold">
            <Link
              href={`/cases/${caseId}/network`}
              className="p-3 rounded-lg border border-slate-800 bg-slate-950 hover:border-cyan-500/40 hover:bg-slate-900 transition flex items-center justify-between"
            >
              <span className="text-cyan-300 flex items-center gap-2"><GitBranch className="size-4 text-cyan-400" /> Graph Canvas</span>
              <ArrowRight className="size-3.5 text-slate-500" />
            </Link>

            <Link
              href={`/cases/${caseId}/evidence`}
              className="p-3 rounded-lg border border-slate-800 bg-slate-950 hover:border-cyan-500/40 hover:bg-slate-900 transition flex items-center justify-between"
            >
              <span className="text-cyan-300 flex items-center gap-2"><FileStack className="size-4 text-cyan-400" /> Evidence Locker</span>
              <ArrowRight className="size-3.5 text-slate-500" />
            </Link>

            <Link
              href={`/cases/${caseId}/investigation-path`}
              className="p-3 rounded-lg border border-slate-800 bg-slate-950 hover:border-cyan-500/40 hover:bg-slate-900 transition flex items-center justify-between"
            >
              <span className="text-cyan-300 flex items-center gap-2"><Route className="size-4 text-cyan-400" /> Path Finder</span>
              <ArrowRight className="size-3.5 text-slate-500" />
            </Link>

            <Link
              href={`/cases/${caseId}/copilot`}
              className="p-3 rounded-lg border border-slate-800 bg-slate-950 hover:border-pink-500/40 hover:bg-slate-900 transition flex items-center justify-between"
            >
              <span className="text-pink-300 flex items-center gap-2"><Bot className="size-4 text-pink-400" /> AI Copilot</span>
              <ArrowRight className="size-3.5 text-slate-500" />
            </Link>
          </div>

          <div className="pt-2 border-t border-slate-800">
            <span className="font-mono text-xs font-bold text-white flex items-center justify-between mb-2">
              <span>RECENT EVIDENCE LOCKER FILES ({evidence.length})</span>
              <Link href={`/cases/${caseId}/evidence`} className="text-[10px] text-cyan-400 hover:underline font-normal">View All</Link>
            </span>

            <div className="space-y-2">
              {evidence.slice(0, 3).map((e) => (
                <div key={e.id} className="p-2.5 rounded-lg border border-slate-800 bg-slate-950 font-mono text-xs flex items-center justify-between">
                  <div>
                    <span className="text-[10px] font-bold text-cyan-400 block">{e.sourceType}</span>
                    <span className="text-slate-200 line-clamp-1 font-bold">{e.title}</span>
                  </div>
                  <span className="text-[9px] text-emerald-400 border border-emerald-500/30 px-1.5 py-0.5 rounded">SHA-256 SEALED</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT PANE: Resolved Entities & Findings (3 Cols) */}
        <div className="lg:col-span-3 rounded-xl border border-slate-800 bg-slate-900/90 p-5 space-y-4 shadow-xl">
          <h2 className="text-sm font-bold text-white border-b border-slate-800 pb-2">Resolved Entities</h2>

          <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
            {entities.map((ent) => (
              <div key={ent.id} className="p-2.5 rounded-lg border border-slate-800 bg-slate-950 space-y-1 font-mono text-xs">
                <span className="text-[9px] font-bold text-emerald-400 uppercase">{ent.type}</span>
                <p className="font-bold text-white">{ent.label}</p>
                {ent.subtitle ? <p className="text-[10px] text-slate-400">{ent.subtitle}</p> : null}
              </div>
            ))}
          </div>
        </div>

      </div>
    </div>
  )
}
