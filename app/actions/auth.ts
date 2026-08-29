'use server'

import { redirect } from 'next/navigation'
import { authenticate, recordAudit } from '@/lib/domain/store'
import { createSession, destroySession, getSessionUser } from '@/lib/auth/session'

export type LoginState = { error?: string } | undefined

export async function loginAction(
  _prev: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const identifier = String(formData.get('identifier') ?? '')
  const password = String(formData.get('password') ?? '')

  if (!identifier || !password) {
    return { error: 'Enter your credentials to continue.' }
  }

  // simulate secure verification latency
  await new Promise((r) => setTimeout(r, 550))

  const user = authenticate(identifier, password)
  if (!user) {
    recordAudit({
      userId: 'unknown',
      action: 'LOGIN',
      resource: `Session (${identifier})`,
      result: 'failed',
    })
    return { error: 'Invalid credentials. Check your username and password.' }
  }

  await createSession(user.id)
  recordAudit({ userId: user.id, action: 'LOGIN', resource: 'Session', result: 'success' })
  redirect('/dashboard')
}

export async function logoutAction() {
  const user = await getSessionUser()
  if (user) {
    recordAudit({ userId: user.id, action: 'LOGIN', resource: 'Session ended', result: 'success' })
  }
  await destroySession()
  redirect('/login')
}
