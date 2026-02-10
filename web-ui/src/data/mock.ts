import type { Incident, OnCallEngineer, EscalationPolicy, MetricsData } from '../types';

const now = new Date();
const h = (hoursAgo: number) => new Date(now.getTime() - hoursAgo * 3600000).toISOString();
const d = (daysAgo: number) => new Date(now.getTime() - daysAgo * 86400000).toISOString();

export const mockIncidents: Incident[] = [
  {
    id: 'INC-001',
    service: 'payment-api',
    severity: 'critical',
    status: 'open',
    title: 'Payment API returning 500 errors',
    description: 'The payment processing endpoint is returning 500 errors for ~30% of requests. Customer checkout is impacted.',
    assignedTo: 'Alice Chen',
    createdAt: h(0.5),
    alerts: [
      { id: 'ALT-001', source: 'Datadog', message: 'Error rate > 5% on payment-api', timestamp: h(0.6) },
      { id: 'ALT-002', source: 'PagerDuty', message: 'High error rate alert triggered', timestamp: h(0.5) },
    ],
    timeline: [
      { id: 'TL-001', type: 'created', message: 'Incident created from alert ALT-001', timestamp: h(0.5), actor: 'System' },
    ],
  },
  {
    id: 'INC-002',
    service: 'auth-service',
    severity: 'high',
    status: 'acknowledged',
    title: 'Authentication latency spike',
    description: 'Login requests are taking 8-12 seconds. P95 latency has tripled in the last 30 minutes.',
    assignedTo: 'Bob Martinez',
    createdAt: h(2),
    acknowledgedAt: h(1.5),
    alerts: [
      { id: 'ALT-003', source: 'Prometheus', message: 'auth-service p95 latency > 5s', timestamp: h(2.1) },
    ],
    timeline: [
      { id: 'TL-002', type: 'created', message: 'Incident created from alert ALT-003', timestamp: h(2), actor: 'System' },
      { id: 'TL-003', type: 'acknowledged', message: 'Incident acknowledged', timestamp: h(1.5), actor: 'Bob Martinez' },
    ],
  },
  {
    id: 'INC-003',
    service: 'search-service',
    severity: 'medium',
    status: 'in_progress',
    title: 'Search results returning stale data',
    description: 'Elasticsearch index is behind by ~15 minutes. Users see outdated results.',
    assignedTo: 'Carol Park',
    createdAt: h(5),
    acknowledgedAt: h(4.5),
    alerts: [
      { id: 'ALT-004', source: 'Custom Monitor', message: 'ES replication lag > 10min', timestamp: h(5.1) },
    ],
    timeline: [
      { id: 'TL-004', type: 'created', message: 'Incident created from monitoring', timestamp: h(5), actor: 'System' },
      { id: 'TL-005', type: 'acknowledged', message: 'Incident acknowledged', timestamp: h(4.5), actor: 'Carol Park' },
      { id: 'TL-006', type: 'in_progress', message: 'Investigating ES cluster health', timestamp: h(4), actor: 'Carol Park' },
    ],
  },
  {
    id: 'INC-004',
    service: 'notification-service',
    severity: 'low',
    status: 'open',
    title: 'Email notifications delayed',
    description: 'Email delivery is delayed by 5-10 minutes. Queue backlog is growing.',
    assignedTo: 'Dave Wilson',
    createdAt: h(1),
    alerts: [
      { id: 'ALT-005', source: 'CloudWatch', message: 'SQS queue depth > 1000', timestamp: h(1.1) },
    ],
    timeline: [
      { id: 'TL-007', type: 'created', message: 'Incident created from CloudWatch alarm', timestamp: h(1), actor: 'System' },
    ],
  },
  {
    id: 'INC-005',
    service: 'payment-api',
    severity: 'critical',
    status: 'resolved',
    title: 'Database connection pool exhausted',
    description: 'PostgreSQL connection pool reached max capacity causing cascading failures.',
    assignedTo: 'Alice Chen',
    createdAt: d(1),
    acknowledgedAt: new Date(new Date(d(1)).getTime() + 300000).toISOString(),
    resolvedAt: new Date(new Date(d(1)).getTime() + 3600000).toISOString(),
    alerts: [
      { id: 'ALT-006', source: 'Datadog', message: 'DB connection pool at 100%', timestamp: d(1) },
    ],
    timeline: [
      { id: 'TL-008', type: 'created', message: 'Incident created', timestamp: d(1), actor: 'System' },
      { id: 'TL-009', type: 'acknowledged', message: 'Incident acknowledged', timestamp: new Date(new Date(d(1)).getTime() + 300000).toISOString(), actor: 'Alice Chen' },
      { id: 'TL-010', type: 'in_progress', message: 'Scaling connection pool', timestamp: new Date(new Date(d(1)).getTime() + 600000).toISOString(), actor: 'Alice Chen' },
      { id: 'TL-011', type: 'resolved', message: 'Connection pool scaled, traffic normalized', timestamp: new Date(new Date(d(1)).getTime() + 3600000).toISOString(), actor: 'Alice Chen' },
    ],
  },
  {
    id: 'INC-006',
    service: 'cdn',
    severity: 'high',
    status: 'resolved',
    title: 'CDN cache purge failure',
    description: 'Static assets serving stale versions after deployment.',
    assignedTo: 'Eve Johnson',
    createdAt: d(2),
    acknowledgedAt: new Date(new Date(d(2)).getTime() + 120000).toISOString(),
    resolvedAt: new Date(new Date(d(2)).getTime() + 1800000).toISOString(),
    alerts: [
      { id: 'ALT-007', source: 'Fastly', message: 'Cache invalidation failed', timestamp: d(2) },
    ],
    timeline: [
      { id: 'TL-012', type: 'created', message: 'Incident created', timestamp: d(2), actor: 'System' },
      { id: 'TL-013', type: 'acknowledged', message: 'Incident acknowledged', timestamp: new Date(new Date(d(2)).getTime() + 120000).toISOString(), actor: 'Eve Johnson' },
      { id: 'TL-014', type: 'resolved', message: 'Manual cache purge completed', timestamp: new Date(new Date(d(2)).getTime() + 1800000).toISOString(), actor: 'Eve Johnson' },
    ],
  },
];

export const mockOnCall: OnCallEngineer[] = [
  { name: 'Alice Chen', email: 'alice@example.com', team: 'Platform', role: 'primary', startTime: h(8), endTime: h(-16) },
  { name: 'Frank Lee', email: 'frank@example.com', team: 'Platform', role: 'secondary', startTime: h(8), endTime: h(-16) },
  { name: 'Bob Martinez', email: 'bob@example.com', team: 'Backend', role: 'primary', startTime: h(4), endTime: h(-20) },
  { name: 'Grace Kim', email: 'grace@example.com', team: 'Backend', role: 'secondary', startTime: h(4), endTime: h(-20) },
  { name: 'Carol Park', email: 'carol@example.com', team: 'Data', role: 'primary', startTime: h(6), endTime: h(-18) },
  { name: 'Henry Zhao', email: 'henry@example.com', team: 'Data', role: 'secondary', startTime: h(6), endTime: h(-18) },
];

export const mockEscalationPolicies: EscalationPolicy[] = [
  {
    team: 'Platform',
    levels: [
      { level: 1, target: 'Primary on-call', timeout: '5 min' },
      { level: 2, target: 'Secondary on-call', timeout: '10 min' },
      { level: 3, target: 'Engineering Manager', timeout: '15 min' },
    ],
  },
  {
    team: 'Backend',
    levels: [
      { level: 1, target: 'Primary on-call', timeout: '5 min' },
      { level: 2, target: 'Secondary on-call', timeout: '10 min' },
      { level: 3, target: 'VP Engineering', timeout: '20 min' },
    ],
  },
  {
    team: 'Data',
    levels: [
      { level: 1, target: 'Primary on-call', timeout: '10 min' },
      { level: 2, target: 'Secondary on-call', timeout: '15 min' },
      { level: 3, target: 'Data Lead', timeout: '20 min' },
    ],
  },
];

export const mockMetrics: MetricsData = {
  mttaTrend: Array.from({ length: 14 }, (_, i) => ({
    date: d(13 - i).slice(0, 10),
    value: Math.round((3 + Math.random() * 7) * 10) / 10,
  })),
  mttrTrend: Array.from({ length: 14 }, (_, i) => ({
    date: d(13 - i).slice(0, 10),
    value: Math.round((20 + Math.random() * 40) * 10) / 10,
  })),
  incidentsPerService: [
    { service: 'payment-api', count: 12 },
    { service: 'auth-service', count: 8 },
    { service: 'search-service', count: 5 },
    { service: 'notification-service', count: 4 },
    { service: 'cdn', count: 3 },
    { service: 'user-service', count: 2 },
  ],
  incidentVolume: Array.from({ length: 14 }, (_, i) => ({
    date: d(13 - i).slice(0, 10),
    count: Math.floor(1 + Math.random() * 6),
  })),
};
