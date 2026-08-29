'use client'

import { useActionState, useState } from 'react'
import { useFormStatus } from 'react-dom'
import { AlertTriangle, Eye, EyeOff, Loader2, ShieldCheck } from 'lucide-react'
import { loginAction, type LoginState } from '@/app/actions/auth'
import { cn } from '@/lib/utils'

const DEMO_ACCOUNTS = [
  { username: 'mira', role: 'Senior Investigator', scope: 'All cases' },
  { username: 'arjun', role: 'Investigator', scope: 'Case 101 only' },
  { username: 'lena', role: 'Analyst', scope: 'Cases 101 & 205' },
  { username: 'dev', role: 'Supervisor', scope: 'All cases' },
  { username: 'admin', role: 'Admin', scope: 'All cases' },
]

function SubmitButton() {
  const { pending } = useFormStatus()
  return (
    <button
      type="submit"
      disabled={pending}
      className="mt-2 flex h-11 w-full items-center justify-center gap-2 rounded-md bg-primary text-sm font-semibold text-primary-foreground transition hover:opacity-90 disabled:opacity-60"
    >
      {pending ? (
        <>
          <Loader2 className="size-4 animate-spin" />
          Verifying credentials…
        </>
      ) : (
        <>
          <ShieldCheck className="size-4" />
          Authenticate
        </>
      )}
    </button>
  )
}

export function LoginForm() {
  const [state, formAction] = useActionState<LoginState, FormData>(loginAction, undefined)
  const [showPw, setShowPw] = useState(false)
  const [identifier, setIdentifier] = useState('')

  return (
    <div className="w-full max-w-sm">
      <form action={formAction} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="identifier" className="text-xs font-medium text-muted-foreground">
            Username or email
          </label>
          <input
            id="identifier"
            name="identifier"
            autoComplete="username"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="e.g. mira"
            className="h-11 rounded-md border border-input bg-surface px-3 text-sm text-foreground outline-none ring-ring/40 transition focus:border-primary/60 focus:ring-2"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="password" className="text-xs font-medium text-muted-foreground">
            Password
          </label>
          <div className="relative">
            <input
              id="password"
              name="password"
              type={showPw ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="••••••••"
              className="h-11 w-full rounded-md border border-input bg-surface px-3 pr-10 text-sm text-foreground outline-none ring-ring/40 transition focus:border-primary/60 focus:ring-2"
            />
            <button
              type="button"
              onClick={() => setShowPw((s) => !s)}
              aria-label={showPw ? 'Hide password' : 'Show password'}
              className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1.5 text-muted-foreground transition hover:text-foreground"
            >
              {showPw ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
            </button>
          </div>
        </div>

        {state?.error ? (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-md border border-danger/40 bg-danger/10 px-3 py-2 text-xs text-foreground"
          >
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-danger" />
            <span>{state.error}</span>
          </div>
        ) : null}

        <SubmitButton />

        <p className="text-center text-[11px] leading-relaxed text-muted-foreground">
          Authorized personnel only. All access is logged for audit.
          MFA is enforced in production deployments.
        </p>
      </form>

      <div className="mt-7 rounded-lg border border-border bg-surface/60 p-3">
        <p className="mb-2 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
          Demo accounts · password{' '}
          <span className="font-mono text-foreground">demo1234</span>
        </p>
        <ul className="flex flex-col divide-y divide-border/70">
          {DEMO_ACCOUNTS.map((a) => (
            <li key={a.username}>
              <button
                type="button"
                onClick={() => setIdentifier(a.username)}
                className={cn(
                  'flex w-full items-center justify-between gap-2 py-1.5 text-left text-xs transition hover:text-primary',
                  identifier === a.username ? 'text-primary' : 'text-foreground',
                )}
              >
                <span className="font-mono">{a.username}</span>
                <span className="text-muted-foreground">{a.role}</span>
                <span className="hidden text-[10px] text-muted-foreground sm:inline">{a.scope}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
