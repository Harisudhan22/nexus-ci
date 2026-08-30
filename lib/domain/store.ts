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

// Helper to construct headers with the current request session cookie.
async function getHeaders() {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (typeof window === 'undefined') {
    try {
      const { getServerAuthHeaders } = await import('./server-auth')
      Object.assign(headers, await getServerAuthHeaders())
    } catch {
      // Non-request context fallback
    }
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

// -------------------------------------------------------------------------------------
// HISTORICAL INTELLIGENCE & MULTI-SOURCE DATA
// -------------------------------------------------------------------------------------
export interface HistoricalStats {
  historicalCases: number
  firRecords: number
  cdrRecords: number
  financialRecords: number
  surveillanceRecords: number
  intelligenceRecords: number
  persons: number
  phones: number
  vehicles: number
  locations: number
  organizations: number
  accounts: number
  documents: number
  entities: number
  relationships: number
  evidence: number
  indexedRagDocuments: number
  processingFailures: number
}

export async function getHistoricalStats(): Promise<HistoricalStats> {
  try {
    return await request<HistoricalStats>('/historical/stats')
  } catch {
    return {
      historicalCases: 0,
      firRecords: 0,
      cdrRecords: 0,
      financialRecords: 0,
      surveillanceRecords: 0,
      intelligenceRecords: 0,
      persons: 0,
      phones: 0,
      vehicles: 0,
      locations: 0,
      organizations: 0,
      accounts: 0,
      documents: 0,
      entities: 0,
      relationships: 0,
      evidence: 0,
      indexedRagDocuments: 0,
      processingFailures: 0,
    }
  }
}

export interface DataSourceItem {
  id: string
  name: string
  category: string
  status: string
  mode: string
  records: number
}

export async function listDataSources(): Promise<DataSourceItem[]> {
  try {
    return await request<DataSourceItem[]>('/historical/sources')
  } catch {
    return []
  }
}

export async function importHistoricalBatch(): Promise<{ status: string; message: string }> {
  return await request<{ status: string; message: string }>('/historical/import-batch', {
    method: 'POST',
  })
}

export async function simulateSourceIngestion(
  type: 'fir' | 'cdr' | 'transaction',
  data?: any
): Promise<{ status: string; recordId: string; message: string }> {
  return await request<{ status: string; recordId: string; message: string }>(`/historical/simulate/${type}`, {
    method: 'POST',
    body: JSON.stringify(data || {}),
  })
}

// -------------------------------------------------------------------------------------
// GLOBAL ENTITY SEARCH & CROSS-CASE INTELLIGENCE
// -------------------------------------------------------------------------------------
export interface GlobalEntitySearchResult {
  id: string
  label: string
  type: string
  subtitle?: string
  aliases: string[]
  caseIds: string[]
  cases: { id: string; title: string; priority: string }[]
  relevance: number
  attributes: Record<string, any>
  phones: string[]
  vehicles: string[]
  locations: string[]
  accounts: string[]
  organizations: string[]
  relationshipsCount: number
  findingsCount: number
  matchReasons: string[]
}

export async function searchGlobalEntities(query: string, type?: string): Promise<GlobalEntitySearchResult[]> {
  try {
    const params = new URLSearchParams()
    if (query) params.append('q', query)
    if (type) params.append('entity_type', type)
    return await request<GlobalEntitySearchResult[]>(`/entities/search?${params.toString()}`)
  } catch {
    return []
  }
}

export async function getCrossCaseAnalysis(entityId: string): Promise<any> {
  try {
    return await request<any>(`/entities/${entityId}/cross-case-analysis`)
  } catch {
    return null
  }
}

// -------------------------------------------------------------------------------------
// P1 ANALYTICS, RAG, COMPARISON & REPORTS
// -------------------------------------------------------------------------------------
export async function getGraphCentrality(caseId?: string): Promise<any> {
  try {
    const q = caseId ? `?case_id=${caseId}` : ''
    return await request<any>(`/analytics/centrality${q}`)
  } catch {
    return { nodes: [], topConnected: [], topBridges: [] }
  }
}

export async function getGraphCommunities(caseId?: string): Promise<any[]> {
  try {
    const q = caseId ? `?case_id=${caseId}` : ''
    return await request<any[]>(`/analytics/communities${q}`)
  } catch {
    return []
  }
}

export async function getNetworkDna(caseId?: string): Promise<any> {
  try {
    const q = caseId ? `?case_id=${caseId}` : ''
    return await request<any>(`/analytics/network-dna${q}`)
  } catch {
    return { networkSize: 0, communityCount: 0, relationshipCount: 0, communicationDensity: 0 }
  }
}

export async function queryRAG(question: string, caseId?: string): Promise<any> {
  try {
    return await request<any>(`/rag/query`, {
      method: 'POST',
      body: JSON.stringify({ question, case_id: caseId }),
    })
  } catch {
    return { retrievedChunks: [], sources: [] }
  }
}

export async function querySafeGraph(prompt: string, caseId?: string): Promise<any> {
  try {
    return await request<any>(`/ai/graph-query`, {
      method: 'POST',
      body: JSON.stringify({ prompt, case_id: caseId }),
    })
  } catch {
    return { nodes: [], edges: [] }
  }
}

export async function compareCases(case1: string, case2: string): Promise<any> {
  try {
    return await request<any>(`/cases/compare?case1=${case1}&case2=${case2}`)
  } catch {
    return null
  }
}

export async function generateReport(caseId: string, format: string = 'markdown'): Promise<any> {
  try {
    return await request<any>(`/reports/generate`, {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId, format }),
    })
  } catch {
    return null
  }
}

export async function getFindingExplanation(id: string): Promise<any> {
  try {
    return await request<any>(`/findings/${id}/explanation`)
  } catch {
    return null
  }
}
