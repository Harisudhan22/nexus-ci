// NEXUS-CI domain model
// Decision-support intelligence platform. Language is deliberately non-accusatory.

export type Role = 'investigator' | 'senior_investigator' | 'analyst' | 'supervisor' | 'admin'

export interface User {
  id: string
  name: string
  email: string
  username: string
  password: string // demo only, plaintext seed; never do this in production
  role: Role
  agency: string
  clearance: 'RESTRICTED' | 'CONFIDENTIAL' | 'SECRET'
  caseAccess: string[] | 'ALL'
}

export type EntityType =
  | 'person'
  | 'phone'
  | 'vehicle'
  | 'account'
  | 'location'
  | 'org'
  | 'case'
  | 'document'
  | 'event'

export type RelationshipType =
  | 'CALLS'
  | 'TRANSFERS'
  | 'OWNS'
  | 'MENTIONED_IN'
  | 'SEEN_AT'
  | 'CO_OCCURS'
  | 'ASSOCIATED_WITH'
  | 'VISITED'
  | 'LINKED_TO'

export type CaseStatus = 'active' | 'under_review' | 'cold' | 'closed'
export type Priority = 'low' | 'medium' | 'high' | 'critical'

export interface Case {
  id: string
  title: string
  description: string
  status: CaseStatus
  priority: Priority
  createdAt: string
  updatedAt: string
  assignedTo: string // user id
  agency: string
  classification: 'RESTRICTED' | 'CONFIDENTIAL' | 'SECRET'
}

export type SourceType = 'FIR' | 'POLICE_REPORT' | 'CDR' | 'TRANSACTIONS' | 'VEHICLE' | 'JSON' | 'IMAGE'

export interface Evidence {
  id: string
  caseId: string
  title: string
  sourceType: SourceType
  fileName: string
  sha256: string
  uploadedAt: string
  uploadedBy: string // user id
  sizeBytes: number
  status: 'processed' | 'processing' | 'failed'
  relevance: number // 0-100
  extractedText?: string
  rows?: Record<string, string>[] // for tabular sources like CDR / transactions
  entityMentions: string[] // canonical entity ids referenced in this evidence
}

// A raw mention captured before resolution
export interface RawMention {
  id: string
  caseId: string
  evidenceId: string
  surface: string // e.g. "R. Kumar"
  type: EntityType
  resolvedTo?: string // canonical entity id
}

export interface CanonicalEntity {
  id: string
  type: EntityType
  label: string
  subtitle?: string
  caseIds: string[]
  aliases: string[]
  relevance: number // 0-100 analytical relevance
  attributes: Record<string, string>
  // precomputed layout position for the network graph (deterministic, no spider web)
  x: number
  y: number
  cluster: string
}

export interface GraphEdge {
  id: string
  source: string // entity id
  target: string // entity id
  type: RelationshipType
  confidence: number // 0-100
  occurrences: number
  timeframe: { from: string; to: string }
  evidenceIds: string[]
  createdByPipeline: string
  suspicious?: boolean
  rationale: string // "WHY THIS EXISTS"
}

export type MatchSignal = { label: string; matched: boolean }

export interface ResolutionCandidate {
  id: string
  caseId: string
  canonicalId: string
  canonicalLabel: string
  type: EntityType
  mentions: string[] // surface forms
  confidence: number
  signals: MatchSignal[]
  status: 'pending' | 'accepted' | 'rejected'
}

export type FindingCategory =
  | 'unusual_connectivity'
  | 'cross_case_recurrence'
  | 'suspicious_transaction_chain'
  | 'activity_spike'
  | 'potential_bridge'
  | 'repeated_location'
  | 'anomalous_communication'

export interface Finding {
  id: string
  caseId: string
  title: string
  category: FindingCategory
  severity: 'low' | 'medium' | 'high'
  confidence: number
  why: string
  entityIds: string[]
  evidenceIds: string[]
  status: 'open' | 'acknowledged' | 'investigating' | 'dismissed'
  createdAt: string
}

export type TimelineEventType =
  | 'call'
  | 'transfer'
  | 'meeting'
  | 'sighting'
  | 'case_mention'
  | 'document'

export interface TimelineEvent {
  id: string
  caseId: string
  timestamp: string
  type: TimelineEventType
  title: string
  entityIds: string[]
  evidenceId: string
}

export type AuditAction =
  | 'LOGIN'
  | 'UPLOAD'
  | 'VIEW'
  | 'DOWNLOAD'
  | 'QUERY'
  | 'ENTITY_MERGE'
  | 'ENTITY_REJECT'
  | 'FINDING_ACKNOWLEDGE'
  | 'PERMISSION_CHANGE'

export interface AuditEntry {
  id: string
  timestamp: string
  userId: string
  action: AuditAction
  caseId?: string
  resource: string
  result: 'success' | 'denied' | 'failed'
}

export interface CrossCaseLink {
  id: string
  canonicalId: string
  label: string
  type: EntityType
  confidence: number
  caseIds: string[]
  reasons: string[]
}

export const ENTITY_META: Record<
  EntityType,
  { label: string; token: string; short: string }
> = {
  person: { label: 'Person', token: 'var(--entity-person)', short: 'PER' },
  phone: { label: 'Phone', token: 'var(--entity-phone)', short: 'TEL' },
  vehicle: { label: 'Vehicle', token: 'var(--entity-vehicle)', short: 'VEH' },
  account: { label: 'Account', token: 'var(--entity-account)', short: 'ACC' },
  location: { label: 'Location', token: 'var(--entity-location)', short: 'LOC' },
  org: { label: 'Organization', token: 'var(--entity-org)', short: 'ORG' },
  case: { label: 'Case', token: 'var(--entity-case)', short: 'CAS' },
  document: { label: 'Document', token: 'var(--entity-document)', short: 'DOC' },
  event: { label: 'Event', token: 'var(--entity-event)', short: 'EVT' },
}

export const RELATIONSHIP_LABELS: Record<RelationshipType, string> = {
  CALLS: 'Calls',
  TRANSFERS: 'Transfers',
  OWNS: 'Owns',
  MENTIONED_IN: 'Mentioned in',
  SEEN_AT: 'Seen at',
  CO_OCCURS: 'Co-occurs',
  ASSOCIATED_WITH: 'Associated with',
  VISITED: 'Visited',
  LINKED_TO: 'Linked to',
}
