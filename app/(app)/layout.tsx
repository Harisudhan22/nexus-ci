import { redirect } from 'next/navigation'
import { getSessionUser } from '@/lib/auth/session'
import { listCases } from '@/lib/domain/store'
import { AppShell } from '@/components/app-shell'

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const user = await getSessionUser()
  if (!user) redirect('/login')

  const cases = listCases(user).map((c) => ({ id: c.id, title: c.title }))

  return (
    <AppShell user={user} cases={cases}>
      {children}
    </AppShell>
  )
}
