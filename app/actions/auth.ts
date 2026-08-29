'use server'

import { redirect } from 'next/navigation'
import { createSession, destroySession, getSessionUser } from '@/lib/auth/session'

const API_URL = process.env.API_URL || 'http://127.0.0.1:8000/api'

export type LoginState = { error?: string } | undefined

export async function loginAction(
  _prev: LoginState,
  formData: FormData,
): Promise<LoginState> {
  const username = String(formData.get('identifier') ?? '')
  const password = String(formData.get('password') ?? '')

  if (!username || !password) {
    return { error: 'Enter your credentials to continue.' }
  }

  try {
    const res = await fetch(`${API_URL}/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
      next: { revalidate: 0 }
    })

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}))
      return { error: errData.detail || 'Invalid credentials. Check your username and password.' }
    }

    const data = await res.json()
    await createSession(data.access_token)
  } catch (err) {
    console.error('Login action error:', err)
    return { error: 'Failed to communicate with authentication services. Ensure the backend is running.' }
  }

  redirect('/dashboard')
}

export async function logoutAction() {
  await destroySession()
  redirect('/login')
}
