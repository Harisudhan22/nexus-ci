import { cookies } from 'next/headers'

const COOKIE = 'nexus_session'

export async function getServerAuthHeaders() {
  const jar = await cookies()
  const token = jar.get(COOKIE)?.value

  if (!token) {
    return {}
  }

  return {
    Authorization: `Bearer ${token}`,
    Cookie: `${COOKIE}=${token}`,
  }
}
