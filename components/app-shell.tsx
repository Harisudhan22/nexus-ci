'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import {
  Bot,
  ClipboardList,
  FilePlus,
  FileSearch,
  FileText,
  Folder,
  GitBranch,
  LayoutDashboard,
  ListTree,
  LogOut,
  Menu,
  PlusCircle,
  Radar,
  Route,
  ScrollText,
  ShieldCheck,
  Users,
  X,
  Database,
  Cpu,
  Layers,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Sparkles,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { NexusMark } from '@/components/nexus-mark'
import { logoutAction } from '@/app/actions/auth'
import type { SessionUser } from '@/lib/auth/session'
import type { Case } from '@/lib/domain/types'

const NAV_GROUPS = [
  {
    title: 'OVERVIEW',
    items: [
      { href: '/dashboard', label: 'Operations Dashboard', icon: LayoutDashboard },
    ],
  },
  {
    title: 'INVESTIGATE',
    items: [
      { href: '/cases', label: 'Cases Directory', icon: Folder },
      { href: '/entities', label: 'Global Entities', icon: Users },
      { href: '/findings', label: 'Pattern Findings', icon: Radar },
    ],
  },
  {
    title: 'INTELLIGENCE',
    items: [
      { href: '/reports', label: 'Executive Reports', icon: FileText },
      { href: '/historical-data', label: 'Data Integrations', icon: ShieldCheck },
    ],
  },
  {
    title: 'GOVERNANCE',
    items: [
      { href: '/audit', label: 'Audit Trail', icon: ScrollText },
    ],
  },
]

const CASE_NAV = [
  { seg: 'overview', label: 'Case Workspace', icon: ClipboardList },
  { seg: 'network', label: 'Network Graph', icon: GitBranch },
  { seg: 'evidence', label: 'Evidence Locker', icon: FileSearch },
  { seg: 'entities', label: 'Entity Resolution', icon: Users },
  { seg: 'findings', label: 'Pattern Alerts', icon: Radar },
  { seg: 'timeline', label: 'Timeline', icon: ListTree },
  { seg: 'investigation-path', label: 'Path Finder', icon: Route },
  { seg: 'copilot', label: 'AI Copilot', icon: Bot },
]

const ROLE_LABEL: Record<string, string> = {
  investigator: 'Field Investigator',
  senior_investigator: 'Lead Officer',
  analyst: 'Intelligence Analyst',
  supervisor: 'Case Supervisor',
  admin: 'System Administrator',
}

const PIPELINE_STEPS = [
  { label: 'EVIDENCE', status: 'ready' },
  { label: 'VALIDATE', status: 'ready' },
  { label: 'PARSE', status: 'ready' },
  { label: 'EXTRACT', status: 'ready' },
  { label: 'RESOLVE', status: 'ready' },
  { label: 'LINK', status: 'ready' },
  { label: 'GRAPH', status: 'ready' },
  { label: 'ANALYZE', status: 'ready' },
  { label: 'DETECT', status: 'ready' },
  { label: 'RETRIEVE', status: 'ready' },
  { label: 'COPILOT', status: 'ready' },
  { label: 'REPORT', status: 'ready' },
]

export function AppShell({
  user,
  cases,
  children,
}: {
  user: SessionUser
  cases: Pick<Case, 'id' | 'title'>[]
  children: React.ReactNode
}) {
  const pathname = usePathname()
  const [mobileOpen, setMobileOpen] = useState(false)

  const caseMatch = pathname.match(/\/cases\/([^/]+)/)
  const activeCaseId = caseMatch?.[1]
  const activeCase = cases.find((c) => c.id === activeCaseId)

  const sidebar = (
    <div className="flex h-full flex-col bg-slate-950/95 text-slate-200">
      {/* Header / Brand */}
      <div className="flex h-16 items-center gap-3 border-b border-slate-800/80 px-4 bg-slate-950">
        <NexusMark className="size-8 text-cyan-400" />
        <div className="leading-tight">
          <div className="flex items-center gap-1.5">
            <span className="font-bold tracking-tight text-white text-base">NEXUS-CI</span>
            <span className="rounded bg-cyan-500/10 border border-cyan-500/30 px-1.5 py-0.2 text-[9px] font-bold font-mono text-cyan-400">
              v2.5
            </span>
          </div>
          <p className="text-[10px] font-mono text-slate-400">CRIMINAL INTELLIGENCE PLATFORM</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-5">
        {/* Primary Action Button */}
        <div>
          <Link
            href="/cases/new"
            onClick={() => setMobileOpen(false)}
            className="flex w-full items-center justify-center gap-2 rounded-lg bg-cyan-600 px-3.5 py-2.5 text-xs font-bold text-white shadow-lg shadow-cyan-600/20 transition hover:bg-cyan-500 active:scale-[0.98]"
          >
            <PlusCircle className="size-4 shrink-0" />
            + NEW CASE & EVIDENCE
          </Link>
        </div>

        {/* Active Case Context */}
        {activeCase ? (
          <div className="rounded-xl border border-cyan-500/30 bg-slate-900/90 p-3 shadow-inner">
            <div className="mb-2 flex items-center justify-between">
              <span className="font-mono text-[9px] font-bold uppercase tracking-wider text-cyan-400 flex items-center gap-1">
                <span className="size-1.5 rounded-full bg-cyan-400 animate-pulse"></span>
                ACTIVE CASE CONTEXT
              </span>
              <Link href="/cases" className="text-[10px] text-slate-400 hover:text-white underline">
                Switch
              </Link>
            </div>
            <p className="font-mono text-xs font-extrabold text-white">{activeCase.id}</p>
            <p className="mt-0.5 line-clamp-1 text-xs text-slate-300 font-medium">{activeCase.title}</p>

            <ul className="mt-3 flex flex-col gap-0.5 border-t border-slate-800 pt-2">
              {CASE_NAV.map(({ seg, label, icon: Icon }) => {
                const href = `/cases/${activeCase.id}/${seg}`
                const active = pathname === href
                return (
                  <li key={seg}>
                    <Link
                      href={href}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        'flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-xs transition',
                        active
                          ? 'bg-cyan-500/15 font-semibold text-cyan-300 border border-cyan-500/30'
                          : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200',
                      )}
                    >
                      <Icon className="size-3.5 shrink-0" />
                      {label}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ) : null}

        {/* Navigation Groups */}
        {NAV_GROUPS.map((group) => (
          <div key={group.title}>
            <p className="mb-1.5 px-2 font-mono text-[10px] font-semibold uppercase tracking-wider text-slate-400">
              {group.title}
            </p>
            <ul className="flex flex-col gap-0.5">
              {group.items.map(({ href, label, icon: Icon }) => {
                const active = pathname === href || (href !== '/dashboard' && pathname.startsWith(href))
                return (
                  <li key={href}>
                    <Link
                      href={href}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        'flex items-center gap-3 rounded-md px-3 py-2 text-xs transition',
                        active
                          ? 'bg-slate-800 font-semibold text-white border-l-2 border-cyan-400'
                          : 'text-slate-400 hover:bg-slate-900 hover:text-slate-200',
                      )}
                    >
                      <Icon className="size-4 shrink-0 text-slate-400" />
                      {label}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ))}
      </nav>

      {/* User Footer */}
      <div className="border-t border-slate-800 p-3 bg-slate-950">
        <div className="flex items-center gap-2.5 rounded-lg bg-slate-900/80 px-2.5 py-2 border border-slate-800">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-cyan-500/20 font-mono text-xs font-bold text-cyan-400 border border-cyan-500/40">
            {user.name.split(' ').map((n) => n[0]).slice(-2).join('')}
          </span>
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-xs font-bold text-white">{user.name}</p>
            <p className="truncate text-[10px] font-mono text-slate-400">{ROLE_LABEL[user.role] || user.role}</p>
          </div>
          <form action={logoutAction}>
            <button
              type="submit"
              aria-label="Sign out"
              title="Sign out"
              className="rounded p-1.5 text-slate-400 transition hover:bg-slate-800 hover:text-white"
            >
              <LogOut className="size-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100 antialiased font-sans">
      {/* Top Header Console Bar */}
      <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b border-slate-800 bg-slate-950/90 px-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded p-1.5 text-slate-400 hover:bg-slate-800 hover:text-white lg:hidden"
          >
            <Menu className="size-5" />
          </button>
          <div className="hidden items-center gap-2 md:flex">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 font-mono text-[10px] font-bold text-emerald-400">
              <span className="size-1.5 rounded-full bg-emerald-400 animate-ping"></span>
              REAL RUNTIME ACTIVE
            </span>
            <span className="font-mono text-xs text-slate-400">|</span>
            <span className="font-mono text-xs text-slate-300">CLEARANCE: <strong className="text-amber-400">SECRET</strong></span>
          </div>
        </div>

        {/* Global Search Bar */}
        <div className="flex flex-1 max-w-md items-center mx-4">
          <form action="/entities/search" method="GET" className="relative w-full">
            <Search className="absolute left-3 top-1/2 size-3.5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              name="q"
              placeholder="Search suspects, phones, vehicles, accounts... (Ctrl+K)"
              className="h-8 w-full rounded-lg border border-slate-800 bg-slate-900/80 pl-9 pr-3 text-xs text-slate-200 placeholder:text-slate-400 outline-none ring-cyan-500/30 transition focus:border-cyan-500 focus:ring-2"
            />
          </form>
        </div>

        <div className="flex items-center gap-3">
          {activeCase ? (
            <div className="hidden sm:flex items-center gap-2 rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-xs">
              <Folder className="size-3.5 text-cyan-400" />
              <span className="font-mono text-cyan-300 font-bold">{activeCase.id}</span>
            </div>
          ) : null}
          <div className="flex items-center gap-1 text-[11px] font-mono text-slate-400">
            <span>SIH 2026 EDITION</span>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex flex-1 overflow-hidden">
        {/* Desktop sidebar */}
        <aside className="hidden w-64 shrink-0 border-r border-slate-800 bg-slate-950 lg:block">
          <div className="sticky top-14 h-[calc(100vh-3.5rem-2rem)]">{sidebar}</div>
        </aside>

        {/* Mobile sidebar */}
        {mobileOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <div
              className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm"
              onClick={() => setMobileOpen(false)}
            />
            <aside className="absolute left-0 top-0 h-full w-64 border-r border-slate-800 bg-slate-950">
              {sidebar}
            </aside>
          </div>
        ) : null}

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto pb-10">{children}</main>
      </div>

      {/* Bottom Intelligence Pipeline Status Stepper Bar */}
      <footer className="fixed bottom-0 left-0 right-0 z-30 flex h-8 items-center border-t border-slate-800 bg-slate-950 px-4 text-[10px] font-mono text-slate-400">
        <span className="mr-3 font-bold text-cyan-400 flex items-center gap-1">
          <Sparkles className="size-3" /> PIPELINE:
        </span>
        <div className="flex flex-1 items-center gap-1 overflow-x-auto no-scrollbar py-1">
          {PIPELINE_STEPS.map((step, idx) => (
            <div key={step.label} className="flex items-center gap-1 shrink-0">
              <span className="rounded bg-slate-900 border border-slate-800 px-1.5 py-0.5 text-[9px] font-bold text-slate-300 hover:text-cyan-400 transition cursor-default">
                {step.label}
              </span>
              {idx < PIPELINE_STEPS.length - 1 && (
                <span className="text-slate-600">➔</span>
              )}
            </div>
          ))}
        </div>
        <div className="hidden md:flex items-center gap-2 pl-3 border-l border-slate-800">
          <span className="text-emerald-400 font-bold">PGVECTOR + NEO4J ONLINE</span>
        </div>
      </footer>
    </div>
  )
}
