import { cookies } from 'next/headers'
import { getUser, publicUser } from '@/lib/domain/store'

const COOKIE = 'nexus_session'

// Demo session: signed-ish token = base64(userId).ts. Not production-grade; the brief
// explicitly scopes this as a synthetic prototype. Cookie is httpOnly + sameSite.
export async function createSession(userId: string) {
  const token = Buffer.from(`${userId}:${Date.now()}`).toString('base64url')
  const jar = await cookies()
  jar.set(COOKIE, token, {
    httpOnly: true,
    sameSite: 'lax',
    secure: true,
    path: '/',
    maxAge: 60 * 60 * 8,
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
    const decoded = Buffer.from(token, 'base64url').toString('utf8')
    const userId = decoded.split(':')[0]
    const user = getUser(userId)
    return user ? publicUser(user) : null
  } catch {
    return null
  }
}

export type SessionUser = NonNullable<Awaited<ReturnType<typeof getSessionUser>>>
