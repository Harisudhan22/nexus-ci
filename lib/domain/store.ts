import {
  auditSeed,
  cases,
  crossCaseLinks,
  edges,
  entities,
  evidence,
  findings,
  resolutionCandidates,
  rawMentions,
  timelineEvents,
  users,
} from './seed'
import type {
  AuditAction,
  AuditEntry,
  CanonicalEntity,
  GraphEdge,
  User,
} from './types'

// In-memory mutable state (resets on server reload — ideal for a demo).
const auditLog: AuditEntry[] = [...auditSeed]
const resolutionState = new Map(resolutionCandidates.map((c) => [c.id, { ...c }]))
const findingState = new Map(findings.map((f) => [f.id, { ...f }]))

// -------------------------------------------------------------------------------------
// USERS / AUTH
// -------------------------------------------------------------------------------------
export function authenticate(identifier: string, password: string): User | null {
  const id = identifier.trim().toLowerCase()
  const user = users.find(
    (u) => u.username.toLowerCase() === id || u.email.toLowerCase() === id,
  )
  if (!user || user.password !== password) return null
  return user
}

export function getUser(id: string): User | undefined {
  return users.find((u) => u.id === id)
}

export function publicUser(u: User) {
  const { password: _pw, ...rest } = u
  return rest
}

export function canAccessCase(user: Pick<User, 'caseAccess'>, caseId: string): boolean {
  return user.caseAccess === 'ALL' || user.caseAccess.includes(caseId)
}

// -------------------------------------------------------------------------------------
// CASES
// -------------------------------------------------------------------------------------
export function listCases(user?: { caseAccess: string[] | 'ALL' }) {
  if (!user) return cases
  return cases.filter((c) => canAccessCase(user, c.id))
}

export function getCase(caseId: string) {
  return cases.find((c) => c.id === caseId)
}

export function caseStats(caseId: string) {
  const ents = entities.filter((e) => e.caseIds.includes(caseId))
  const evs = evidence.filter((e) => e.caseId === caseId)
  const fnd = [...findingState.values()].filter((f) => f.caseId === caseId)
  const crossLinks = crossCaseLinks.filter((l) => l.caseIds.includes(caseId))
  return {
    entities: ents.length,
    evidence: evs.length,
    findings: fnd.length,
    crossCaseLinks: crossLinks.length,
    lastActivity: getCase(caseId)?.updatedAt,
  }
}

// -------------------------------------------------------------------------------------
// EVIDENCE
// -------------------------------------------------------------------------------------
export function listEvidence(caseId?: string) {
  return caseId ? evidence.filter((e) => e.caseId === caseId) : evidence
}
export function getEvidence(id: string) {
  return evidence.find((e) => e.id === id)
}

// -------------------------------------------------------------------------------------
// ENTITIES
// -------------------------------------------------------------------------------------
export function listEntities(caseId?: string) {
  return caseId ? entities.filter((e) => e.caseIds.includes(caseId)) : entities
}
export function getEntity(id: string) {
  return entities.find((e) => e.id === id)
}
export function listRawMentions(caseId?: string) {
  return caseId ? rawMentions.filter((m) => m.caseId === caseId) : rawMentions
}

// -------------------------------------------------------------------------------------
// GRAPH + ANALYTICS
// -------------------------------------------------------------------------------------
export function graphForCase(caseId?: string) {
  const nodes = listEntities(caseId)
  const nodeIds = new Set(nodes.map((n) => n.id))
  const graphEdges = edges.filter(
    (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
  )
  return { nodes, edges: graphEdges }
}

export function neighbors(entityId: string, caseId?: string) {
  const { edges: es } = graphForCase(caseId)
  const connected = es.filter((e) => e.source === entityId || e.target === entityId)
  const ids = new Set<string>()
  connected.forEach((e) => {
    ids.add(e.source === entityId ? e.target : e.source)
  })
  return {
    edges: connected,
    entities: [...ids].map((id) => getEntity(id)).filter(Boolean) as CanonicalEntity[],
  }
}

/** Degree-based centrality (normalized 0-1) plus bridge detection across clusters. */
export function computeCentrality(caseId?: string) {
  const { nodes, edges: es } = graphForCase(caseId)
  const degree = new Map<string, number>()
  const clustersByNode = new Map<string, Set<string>>()
  nodes.forEach((n) => {
    degree.set(n.id, 0)
    clustersByNode.set(n.id, new Set())
  })
  es.forEach((e) => {
    degree.set(e.source, (degree.get(e.source) ?? 0) + 1)
    degree.set(e.target, (degree.get(e.target) ?? 0) + 1)
    const sc = getEntity(e.source)?.cluster
    const tc = getEntity(e.target)?.cluster
    if (tc) clustersByNode.get(e.source)?.add(tc)
    if (sc) clustersByNode.get(e.target)?.add(sc)
  })
  const maxDeg = Math.max(1, ...[...degree.values()])
  const result = new Map<
    string,
    { degree: number; centrality: number; isBridge: boolean }
  >()
  nodes.forEach((n) => {
    const d = degree.get(n.id) ?? 0
    result.set(n.id, {
      degree: d,
      centrality: Math.round((d / maxDeg) * 100) / 100,
      isBridge: (clustersByNode.get(n.id)?.size ?? 0) > 1,
    })
  })
  return result
}

export interface PathResult {
  nodeIds: string[]
  edges: GraphEdge[]
  totalConfidence: number
  hops: number
}

/** BFS shortest path or strongest-evidence path over the evidence graph. Never invents a path. */
export function findPath(
  from: string,
  to: string,
  mode: 'shortest' | 'strongest' = 'shortest',
  caseId?: string,
): PathResult | null {
  const { edges: es } = graphForCase(caseId)
  const adj = new Map<string, GraphEdge[]>()
  es.forEach((e) => {
    if (!adj.has(e.source)) adj.set(e.source, [])
    if (!adj.has(e.target)) adj.set(e.target, [])
    adj.get(e.source)!.push(e)
    adj.get(e.target)!.push(e)
  })
  if (!adj.has(from) || !adj.has(to)) return null

  if (mode === 'shortest') {
    const prev = new Map<string, { node: string; edge: GraphEdge } | null>()
    prev.set(from, null)
    const queue = [from]
    while (queue.length) {
      const cur = queue.shift()!
      if (cur === to) break
      for (const e of adj.get(cur) ?? []) {
        const nxt = e.source === cur ? e.target : e.source
        if (!prev.has(nxt)) {
          prev.set(nxt, { node: cur, edge: e })
          queue.push(nxt)
        }
      }
    }
    if (!prev.has(to)) return null
    return reconstruct(prev, from, to)
  }

  // strongest: Dijkstra maximizing summed confidence (min of negative confidence as cost)
  const best = new Map<string, number>()
  const prev = new Map<string, { node: string; edge: GraphEdge } | null>()
  best.set(from, 0)
  prev.set(from, null)
  const visited = new Set<string>()
  while (visited.size < adj.size) {
    let cur: string | null = null
    let curScore = -Infinity
    for (const [node, score] of best) {
      if (!visited.has(node) && score > curScore) {
        curScore = score
        cur = node
      }
    }
    if (cur === null) break
    visited.add(cur)
    for (const e of adj.get(cur) ?? []) {
      const nxt = e.source === cur ? e.target : e.source
      const score = curScore + e.confidence
      if (score > (best.get(nxt) ?? -Infinity)) {
        best.set(nxt, score)
        prev.set(nxt, { node: cur, edge: e })
      }
    }
  }
  if (!prev.has(to)) return null
  return reconstruct(prev, from, to)
}

function reconstruct(
  prev: Map<string, { node: string; edge: GraphEdge } | null>,
  from: string,
  to: string,
): PathResult {
  const nodeIds: string[] = [to]
  const pathEdges: GraphEdge[] = []
  let cur = to
  while (cur !== from) {
    const step = prev.get(cur)
    if (!step) break
    pathEdges.unshift(step.edge)
    nodeIds.unshift(step.node)
    cur = step.node
  }
  const totalConfidence = pathEdges.length
    ? Math.round(pathEdges.reduce((s, e) => s + e.confidence, 0) / pathEdges.length)
    : 0
  return { nodeIds, edges: pathEdges, totalConfidence, hops: pathEdges.length }
}

// -------------------------------------------------------------------------------------
// FINDINGS
// -------------------------------------------------------------------------------------
export function listFindings(caseId?: string) {
  const all = [...findingState.values()]
  return caseId ? all.filter((f) => f.caseId === caseId) : all
}
export function getFinding(id: string) {
  return findingState.get(id)
}
export function setFindingStatus(
  id: string,
  status: 'open' | 'acknowledged' | 'investigating' | 'dismissed',
) {
  const f = findingState.get(id)
  if (!f) return null
  f.status = status
  findingState.set(id, f)
  return f
}

// -------------------------------------------------------------------------------------
// TIMELINE
// -------------------------------------------------------------------------------------
export function listTimeline(caseId?: string) {
  const all = caseId ? timelineEvents.filter((t) => t.caseId === caseId) : timelineEvents
  return [...all].sort((a, b) => a.timestamp.localeCompare(b.timestamp))
}

// -------------------------------------------------------------------------------------
// RESOLUTION
// -------------------------------------------------------------------------------------
export function listResolutionCandidates(caseId?: string) {
  const all = [...resolutionState.values()]
  return caseId ? all.filter((c) => c.caseId === caseId) : all
}
export function decideResolution(id: string, decision: 'accepted' | 'rejected') {
  const c = resolutionState.get(id)
  if (!c) return null
  c.status = decision
  resolutionState.set(id, c)
  return c
}

// -------------------------------------------------------------------------------------
// CROSS-CASE
// -------------------------------------------------------------------------------------
export function listCrossCaseLinks(caseId?: string) {
  return caseId ? crossCaseLinks.filter((l) => l.caseIds.includes(caseId)) : crossCaseLinks
}

// -------------------------------------------------------------------------------------
// AUDIT
// -------------------------------------------------------------------------------------
export function listAudit() {
  return [...auditLog].sort((a, b) => b.timestamp.localeCompare(a.timestamp))
}
export function recordAudit(entry: {
  userId: string
  action: AuditAction
  resource: string
  caseId?: string
  result?: 'success' | 'denied' | 'failed'
}) {
  const e: AuditEntry = {
    id: `a-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
    timestamp: new Date().toISOString(),
    result: 'success',
    ...entry,
  }
  auditLog.unshift(e)
  return e
}
