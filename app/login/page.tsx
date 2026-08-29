import { redirect } from 'next/navigation'
import { Activity, Database, GitBranch, Lock } from 'lucide-react'
import { getSessionUser } from '@/lib/auth/session'
import { LoginForm } from '@/components/login-form'
import { NexusMark } from '@/components/nexus-mark'

export default async function LoginPage() {
  const user = await getSessionUser()
  if (user) redirect('/dashboard')

  return (
    <main className="flex min-h-screen w-full">
      {/* Left: brand / mission panel */}
      <section className="relative hidden flex-1 flex-col justify-between overflow-hidden border-r border-border bg-surface p-10 lg:flex">
        <div className="absolute inset-0 grid-lines opacity-40" aria-hidden />
        <div
          className="absolute inset-0"
          aria-hidden
          style={{
            background:
              'radial-gradient(60% 50% at 30% 20%, color-mix(in oklch, var(--primary) 12%, transparent), transparent)',
          }}
        />
        <div className="relative flex items-center gap-3">
          <NexusMark className="size-9" />
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-tight">NEXUS-CI</p>
            <p className="text-xs text-muted-foreground">Criminal Intelligence Platform</p>
          </div>
        </div>

        <div className="relative max-w-md">
          <h1 className="text-balance text-3xl font-semibold leading-tight tracking-tight">
            From fragmented evidence to explainable criminal intelligence.
          </h1>
          <p className="mt-4 text-pretty text-sm leading-relaxed text-muted-foreground">
            NEXUS-CI resolves noisy references, links entities across cases, and surfaces
            evidence-backed investigative leads — a decision-support tool that keeps the
            investigator in control.
          </p>

          <ul className="mt-8 flex flex-col gap-3">
            {[
              { icon: GitBranch, text: 'Evidence-centric knowledge graph' },
              { icon: Database, text: 'Cross-source entity resolution' },
              { icon: Activity, text: 'Explainable, grounded findings' },
            ].map(({ icon: Icon, text }) => (
              <li key={text} className="flex items-center gap-3 text-sm">
                <span className="flex size-8 items-center justify-center rounded-md border border-border bg-elevated text-primary">
                  <Icon className="size-4" />
                </span>
                {text}
              </li>
            ))}
          </ul>
        </div>

        <div className="relative flex items-center gap-2 text-[11px] text-muted-foreground">
          <Lock className="size-3.5" />
          Synthetic demonstration data · No real law-enforcement records
        </div>
      </section>

      {/* Right: auth */}
      <section className="flex flex-1 flex-col items-center justify-center px-6 py-12">
        <div className="mb-8 flex flex-col items-center gap-3 lg:hidden">
          <NexusMark className="size-10" />
          <div className="text-center">
            <p className="text-lg font-semibold tracking-tight">NEXUS-CI</p>
            <p className="text-xs text-muted-foreground">Evidence-Centric Criminal Intelligence</p>
          </div>
        </div>
        <div className="mb-6 hidden w-full max-w-sm lg:block">
          <h2 className="text-xl font-semibold tracking-tight">Sign in</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Access is role-aware and fully audited.
          </p>
        </div>
        <LoginForm />
      </section>
    </main>
  )
}
