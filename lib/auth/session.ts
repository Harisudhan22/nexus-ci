import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'

const COOKIE = 'nexus_session'
const API_URL = process.env.API_URL || 'http://127.0.0.1:8000/api'

export async function createSession(token: string) {
  const jar = await cookies()
  jar.set(COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: 60 * 60 * 8, // 8 hours
  })
}

export async function destroySession() {
  const jar = await cookies()
  jar.delete(COOKIE)
}

export async function getSessionUser() {
  const jar = await cookies()
  const token = jar.get(COOKIE)?.value
  if (!token) return null

  try {
    const res = await fetch(`${API_URL}/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      next: { revalidate: 0 } // Disable caching to ensure fresh verification
    })
    
    if (!res.ok) {
      return null
    }
    
    const user = await res.json()
    return user
  } catch (error) {
    print(`Session user fetch failed: ${error}`)
    return null
  }
}

export async function requireUser() {
  const user = await getSessionUser()
  if (!user) {
    redirect('/login')
  }
  return user
}

export type SessionUser = NonNullable<Awaited<ReturnType<typeof getSessionUser>>>

function print(msg: string) {
  console.log(`[Session] ${msg}`)
}
