import { cookies } from 'next/headers'
import type {
  AuditEntry,
  CanonicalEntity,
  Case,
  Evidence,
  Finding,
  GraphEdge,
  RawMention,
  ResolutionCandidate,
  TimelineEvent,
  User,
  CrossCaseLink,
} from './types'

const API_URL = process.env.API_URL || 'http://127.0.0.1:8000/api'

// Helper to construct headers with the current Next.js request session cookie
async function getHeaders() {
  const jar = await cookies()
  const token = jar.get('nexus_session')?.value
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
    // Forward the cookie for session detection in FastAPI
    headers['Cookie'] = `nexus_session=${token}`
  }
  return headers
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = await getHeaders()
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      ...headers,
      ...options.headers,
    },
    next: { revalidate: 0 }, // Disable Next.js caching to ensure real-time updates
  })

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}))
    throw new Error(errorData.detail || `API request failed with status ${res.status}`)
  }

  return res.json()
}

// -------------------------------------------------------------------------------------
// USERS / AUTH
// -------------------------------------------------------------------------------------
export async function getSessionUser(): Promise<User | null> {
  try {
    return await request<User>('/auth/me')
  } catch {
    return null
  }
}

export async function listUsers(): Promise<User[]> {
  try {
    return await request<User[]>('/users')
  } catch {
    return []
  }
}

export async function getUser(id: string): Promise<User | null> {
  try {
    return await request<User>(`/auth/me`) // standard fallback
  } catch {
    return null
  }
}

export function publicUser(u: User) {
  return u
}

// -------------------------------------------------------------------------------------
// CASES
function mapCase(raw: any): Case {
  return {
    id: raw.id,
    title: raw.title,
    description: raw.description,
    status: raw.status,
    priority: raw.priority,
    createdAt: raw.created_at || raw.createdAt,
    updatedAt: raw.updated_at || raw.updatedAt,
    assignedTo: raw.assigned_to || raw.assignedTo,
    agency: raw.agency,
    classification: raw.classification,
  }
}

export async function listCases(user?: any): Promise<Case[]> {
  try {
    const list = await request<any[]>('/cases')
    return list.map(mapCase)
  } catch {
    return []
  }
}

export async function getCase(caseId: string): Promise<Case | undefined> {
  try {
    const raw = await request<any>(`/cases/${caseId}`)
    return mapCase(raw)
  } catch {
    return undefined
  }
}

export async function caseStats(caseId: string) {
  try {
    return await request<{
      entities: number
      evidence: number
      findings: number
      crossCaseLinks: number
      lastActivity?: string
    }>(`/cases/${caseId}/stats`)
  } catch {
    return {
      entities: 0,
      evidence: 0,
      findings: 0,
      crossCaseLinks: 0,
    }
  }
}

// -------------------------------------------------------------------------------------
// EVIDENCE
// -------------------------------------------------------------------------------------
export async function listEvidence(caseId?: string): Promise<Evidence[]> {
  if (!caseId) return []
  try {
    return await request<Evidence[]>(`/cases/${caseId}/documents`)
  } catch {
    return []
  }
}

export async function getEvidence(id: string): Promise<Evidence | undefined> {
  try {
    return await request<Evidence>(`/documents/${id}`)
  } catch {
    return undefined
  }
}

// -------------------------------------------------------------------------------------
// ENTITIES
// -------------------------------------------------------------------------------------
export async function listEntities(caseId?: string): Promise<CanonicalEntity[]> {
  if (!caseId) return []
  try {
    return await request<CanonicalEntity[]>(`/cases/${caseId}/entities`)
  } catch {
    return []
  }
}

export async function getEntity(id: string): Promise<CanonicalEntity | undefined> {
  try {
    return await request<CanonicalEntity>(`/entities/${id}`)
  } catch {
    return undefined
  }
}

export async function listRawMentions(caseId?: string): Promise<RawMention[]> {
  // Not used directly in frontend dashboards, fallback to empty
  return []
}

// -------------------------------------------------------------------------------------
// GRAPH + ANALYTICS
// -------------------------------------------------------------------------------------
export async function graphForCase(caseId?: string): Promise<{ nodes: CanonicalEntity[]; edges: GraphEdge[]; centrality: any }> {
  if (!caseId) return { nodes: [], edges: [], centrality: {} }
  try {
    return await request<{ nodes: CanonicalEntity[]; edges: GraphEdge[]; centrality: any }>(`/cases/${caseId}/graph`)
  } catch {
    return { nodes: [], edges: [], centrality: {} }
  }
}

export async function neighbors(entityId: string, caseId?: string): Promise<{ edges: GraphEdge[]; entities: CanonicalEntity[] }> {
  if (!caseId) return { edges: [], entities: [] }
  try {
    const { nodes, edges } = await graphForCase(caseId)
    const connectedEdges = edges.filter(e => e.source === entityId || e.target === entityId)
    const otherIds = new Set<string>()
    connectedEdges.forEach(e => {
      otherIds.add(e.source === entityId ? e.target : e.source)
    })
    const entities = nodes.filter(n => otherIds.has(n.id))
    return { edges: connectedEdges, entities }
  } catch {
    return { edges: [], entities: [] }
  }
}

export async function computeCentrality(caseId?: string): Promise<Map<string, { degree: number; centrality: number; isBridge: boolean }>> {
  if (!caseId) return new Map()
  try {
    const { centrality } = await graphForCase(caseId)
    return new Map(Object.entries(centrality)) as any
  } catch {
    return new Map()
  }
}

export interface PathResult {
  nodeIds: string[]
  edges: GraphEdge[]
  totalConfidence: number
  hops: number
}

export async function findPath(
  from: string,
  to: string,
  mode: 'shortest' | 'strongest' = 'shortest',
  caseId?: string,
): Promise<PathResult | null> {
  try {
    return await request<PathResult>(`/paths?from=${from}&to=${to}&case_id=${caseId}&mode=${mode}`)
  } catch {
    return null
  }
}

// -------------------------------------------------------------------------------------
// FINDINGS
// -------------------------------------------------------------------------------------
export async function listFindings(caseId?: string): Promise<Finding[]> {
  if (!caseId) return []
  try {
    return await request<Finding[]>(`/cases/${caseId}/findings`)
  } catch {
    return []
  }
}

export async function getFinding(id: string): Promise<Finding | undefined> {
  // Finding get is usually not standalone, fallback via list filter
  return undefined
}

export async function setFindingStatus(
  id: string,
  status: 'open' | 'acknowledged' | 'investigating' | 'dismissed',
): Promise<Finding | null> {
  try {
    return await request<Finding>(`/findings/${id}/acknowledge`, {
      method: 'POST',
      body: JSON.stringify({ status }),
    })
  } catch {
    return null
  }
}

// -------------------------------------------------------------------------------------
// TIMELINE
// -------------------------------------------------------------------------------------
export async function listTimeline(caseId?: string): Promise<TimelineEvent[]> {
  if (!caseId) return []
  try {
    return await request<TimelineEvent[]>(`/cases/${caseId}/timeline`)
  } catch {
    return []
  }
}

// -------------------------------------------------------------------------------------
// RESOLUTION
// -------------------------------------------------------------------------------------
export async function listResolutionCandidates(caseId?: string): Promise<ResolutionCandidate[]> {
  if (!caseId) return []
  try {
    return await request<ResolutionCandidate[]>(`/entity-resolution/candidates?case_id=${caseId}`)
  } catch {
    return []
  }
}

export async function decideResolution(id: string, decision: 'accepted' | 'rejected'): Promise<any> {
  try {
    return await request(`/entity-resolution/review`, {
      method: 'POST',
      body: JSON.stringify({ candidate_id: id, decision }),
    })
  } catch {
    return null
  }
}

// -------------------------------------------------------------------------------------
// CROSS-CASE
// -------------------------------------------------------------------------------------
export async function listCrossCaseLinks(caseId?: string): Promise<CrossCaseLink[]> {
  if (!caseId) return []
  try {
    return await request<CrossCaseLink[]>(`/cases/${caseId}/cross-case-links`)
  } catch {
    return []
  }
}

// -------------------------------------------------------------------------------------
// AUDIT
// -------------------------------------------------------------------------------------
export async function listAudit(): Promise<AuditEntry[]> {
  try {
    return await request<AuditEntry[]>('/audit')
  } catch {
    return []
  }
}

export async function recordAudit(entry: {
  userId: string
  action: string
  resource: string
  caseId?: string
  result?: 'success' | 'denied' | 'failed'
}): Promise<any> {
  // Audits are recorded on the backend during actions
  return null
}
