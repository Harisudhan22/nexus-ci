'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useState } from 'react'
import {
  Bot,
  ClipboardList,
  FileSearch,
  Folder,
  GitBranch,
  LayoutDashboard,
  ListTree,
  LogOut,
  Menu,
  Radar,
  Route,
  ScrollText,
  ShieldCheck,
  Users,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { NexusMark } from '@/components/nexus-mark'
import { logoutAction } from '@/app/actions/auth'
import type { SessionUser } from '@/lib/auth/session'
import type { Case } from '@/lib/domain/types'

const GLOBAL_NAV = [
  { href: '/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/cases', label: 'Cases', icon: Folder },
  { href: '/audit', label: 'Audit', icon: ScrollText },
  { href: '/historical-data', label: 'Integrations', icon: ShieldCheck },
]

const CASE_NAV = [
  { seg: 'overview', label: 'Overview', icon: ClipboardList },
  { seg: 'network', label: 'Network Graph', icon: GitBranch },
  { seg: 'evidence', label: 'Evidence', icon: FileSearch },
  { seg: 'entities', label: 'Entities', icon: Users },
  { seg: 'findings', label: 'Findings', icon: Radar },
  { seg: 'timeline', label: 'Timeline', icon: ListTree },
  { seg: 'investigation-path', label: 'Path Finder', icon: Route },
  { seg: 'copilot', label: 'Copilot', icon: Bot },
]

const ROLE_LABEL: Record<string, string> = {
  investigator: 'Investigator',
  senior_investigator: 'Senior Investigator',
  analyst: 'Analyst',
  supervisor: 'Supervisor',
  admin: 'Administrator',
}

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
    <div className="flex h-full flex-col">
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <NexusMark className="size-7" />
        <div className="leading-none">
          <p className="text-sm font-semibold tracking-tight">NEXUS-CI</p>
          <p className="mt-0.5 text-[10px] text-muted-foreground">Criminal Intelligence</p>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="flex flex-col gap-0.5">
          {GLOBAL_NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || pathname.startsWith(href + '/')
            return (
              <li key={href}>
                <Link
                  href={href}
                  onClick={() => setMobileOpen(false)}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition',
                    active
                      ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
                      : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                  )}
                >
                  <Icon className="size-4 shrink-0" />
                  {label}
                </Link>
              </li>
            )
          })}
        </ul>

        {activeCase ? (
          <div className="mt-6">
            <div className="mb-2 flex items-center gap-2 px-3">
              <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Case Context
              </span>
            </div>
            <div className="mb-2 rounded-md border border-sidebar-border bg-sidebar-accent/40 px-3 py-2">
              <p className="font-mono text-[10px] uppercase text-primary">{activeCase.id}</p>
              <p className="mt-0.5 line-clamp-2 text-xs text-foreground">{activeCase.title}</p>
            </div>
            <ul className="flex flex-col gap-0.5">
              {CASE_NAV.map(({ seg, label, icon: Icon }) => {
                const href = `/cases/${activeCase.id}/${seg}`
                const active = pathname === href
                return (
                  <li key={seg}>
                    <Link
                      href={href}
                      onClick={() => setMobileOpen(false)}
                      className={cn(
                        'flex items-center gap-3 rounded-md px-3 py-2 text-sm transition',
                        active
                          ? 'bg-sidebar-accent font-medium text-sidebar-accent-foreground'
                          : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground',
                      )}
                    >
                      <Icon className="size-4 shrink-0" />
                      {label}
                    </Link>
                  </li>
                )
              })}
            </ul>
          </div>
        ) : null}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <div className="flex items-center gap-2.5 rounded-md px-2 py-1.5">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-semibold text-primary">
            {user.name.split(' ').map((n) => n[0]).slice(-2).join('')}
          </span>
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-xs font-medium">{user.name}</p>
            <p className="truncate text-[10px] text-muted-foreground">{ROLE_LABEL[user.role]}</p>
          </div>
          <form action={logoutAction}>
            <button
              type="submit"
              aria-label="Sign out"
              className="rounded p-1.5 text-muted-foreground transition hover:bg-sidebar-accent hover:text-foreground"
            >
              <LogOut className="size-4" />
            </button>
          </form>
        </div>
      </div>
    </div>
  )

  return (
    <div className="flex min-h-screen bg-background">
      {/* Desktop sidebar */}
      <aside className="hidden w-60 shrink-0 border-r border-sidebar-border bg-sidebar lg:block">
        <div className="sticky top-0 h-screen">{sidebar}</div>
      </aside>

      {/* Mobile sidebar */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-background/70 backdrop-blur-sm"
            onClick={() => setMobileOpen(false)}
          />
          <aside className="absolute left-0 top-0 h-full w-64 border-r border-sidebar-border bg-sidebar">
            {sidebar}
          </aside>
        </div>
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b border-border bg-background/85 px-4 backdrop-blur">
          <button
            className="rounded-md p-2 text-muted-foreground hover:bg-secondary lg:hidden"
            onClick={() => setMobileOpen((o) => !o)}
            aria-label="Toggle navigation"
          >
            {mobileOpen ? <X className="size-4" /> : <Menu className="size-4" />}
          </button>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <FileSearch className="size-3.5" />
            <span className="hidden sm:inline">Search entities, cases, evidence</span>
            <kbd className="hidden rounded border border-border bg-secondary px-1.5 py-0.5 font-mono text-[10px] sm:inline">
              ⌘K
            </kbd>
          </div>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden items-center gap-1.5 rounded-md border border-warning/40 bg-warning/10 px-2 py-1 text-[11px] font-medium text-warning sm:flex">
              <ShieldCheck className="size-3.5" />
              {user.clearance}
            </span>
            <span className="hidden items-center gap-1.5 rounded-md border border-border bg-secondary px-2 py-1 text-[11px] text-muted-foreground md:flex">
              {user.agency}
            </span>
            <span className="flex items-center gap-1.5 text-[11px] text-success">
              <span className="size-1.5 rounded-full bg-success" />
              Session active
            </span>
          </div>
        </header>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  )
}
