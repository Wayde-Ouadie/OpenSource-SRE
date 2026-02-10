// ─── Types ───────────────────────────────────────────────────────────────────

export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type IncidentStatus = 'triggered' | 'acknowledged' | 'resolved';

export interface Incident {
    id: string;
    title: string;
    description: string;
    severity: Severity;
    status: IncidentStatus;
    assignee: string;
    service: string;
    createdAt: string;
    updatedAt: string;
    timeline: TimelineEvent[];
}

export interface TimelineEvent {
    id: string;
    type: 'created' | 'acknowledged' | 'resolved' | 'note' | 'escalated';
    message: string;
    timestamp: string;
    actor: string;
}

export interface OnCallSchedule {
    id: string;
    team: string;
    currentOnCall: string;
    email: string;
    startTime: string;
    endTime: string;
    nextOnCall: string;
}

export interface MetricEntry {
    label: string;
    value: string;
    change: number;
    unit: string;
}

// ─── Mock Data ───────────────────────────────────────────────────────────────

const mockIncidents: Incident[] = [
    {
        id: 'INC-001',
        title: 'Database connection pool exhausted',
        description: 'Production database is not accepting new connections. Connection pool at 100% capacity causing service degradation across multiple endpoints.',
        severity: 'critical',
        status: 'triggered',
        assignee: 'Sarah Chen',
        service: 'postgres-primary',
        createdAt: '2026-02-09T22:15:00Z',
        updatedAt: '2026-02-09T22:15:00Z',
        timeline: [
            { id: 't1', type: 'created', message: 'Incident created from alert: DB connection pool > 95%', timestamp: '2026-02-09T22:15:00Z', actor: 'AlertManager' },
        ],
    },
    {
        id: 'INC-002',
        title: 'API latency spike on /api/v2/orders',
        description: 'P99 latency increased from 120ms to 2.4s on the orders endpoint. Likely caused by a slow downstream dependency.',
        severity: 'high',
        status: 'acknowledged',
        assignee: 'Mike Rodriguez',
        service: 'order-service',
        createdAt: '2026-02-09T21:30:00Z',
        updatedAt: '2026-02-09T21:45:00Z',
        timeline: [
            { id: 't1', type: 'created', message: 'Incident created from alert: P99 > 2s', timestamp: '2026-02-09T21:30:00Z', actor: 'AlertManager' },
            { id: 't2', type: 'acknowledged', message: 'Investigating downstream dependencies', timestamp: '2026-02-09T21:45:00Z', actor: 'Mike Rodriguez' },
        ],
    },
    {
        id: 'INC-003',
        title: 'Elevated error rate on payment gateway',
        description: 'Error rate on the payment gateway increased to 3.2%. Stripe webhook delivery intermittent.',
        severity: 'medium',
        status: 'acknowledged',
        assignee: 'Priya Patel',
        service: 'payment-service',
        createdAt: '2026-02-09T20:00:00Z',
        updatedAt: '2026-02-09T20:30:00Z',
        timeline: [
            { id: 't1', type: 'created', message: 'Incident created from alert: Error rate > 2%', timestamp: '2026-02-09T20:00:00Z', actor: 'AlertManager' },
            { id: 't2', type: 'acknowledged', message: 'Contacted Stripe support', timestamp: '2026-02-09T20:30:00Z', actor: 'Priya Patel' },
        ],
    },
    {
        id: 'INC-004',
        title: 'SSL certificate expiry warning',
        description: 'SSL certificate for api.example.com expires in 7 days. Renewal process should be initiated.',
        severity: 'low',
        status: 'resolved',
        assignee: 'James Wilson',
        service: 'infra-certs',
        createdAt: '2026-02-08T10:00:00Z',
        updatedAt: '2026-02-08T14:00:00Z',
        timeline: [
            { id: 't1', type: 'created', message: 'Certificate expiry warning triggered', timestamp: '2026-02-08T10:00:00Z', actor: 'CertMonitor' },
            { id: 't2', type: 'acknowledged', message: 'Starting renewal process', timestamp: '2026-02-08T11:00:00Z', actor: 'James Wilson' },
            { id: 't3', type: 'resolved', message: 'Certificate renewed and deployed', timestamp: '2026-02-08T14:00:00Z', actor: 'James Wilson' },
        ],
    },
    {
        id: 'INC-005',
        title: 'Memory leak in notification worker',
        description: 'Notification worker memory usage growing at ~50MB/hr. RSS at 3.2GB, approaching OOM threshold.',
        severity: 'high',
        status: 'triggered',
        assignee: 'Sarah Chen',
        service: 'notification-worker',
        createdAt: '2026-02-09T23:00:00Z',
        updatedAt: '2026-02-09T23:00:00Z',
        timeline: [
            { id: 't1', type: 'created', message: 'Alert: Memory usage > 3GB on notification-worker-04', timestamp: '2026-02-09T23:00:00Z', actor: 'AlertManager' },
        ],
    },
];

const mockOnCallSchedules: OnCallSchedule[] = [
    { id: 'oc-1', team: 'Platform Engineering', currentOnCall: 'Sarah Chen', email: 'sarah.chen@company.com', startTime: '2026-02-09T08:00:00Z', endTime: '2026-02-10T08:00:00Z', nextOnCall: 'James Wilson' },
    { id: 'oc-2', team: 'Backend Services', currentOnCall: 'Mike Rodriguez', email: 'mike.r@company.com', startTime: '2026-02-09T08:00:00Z', endTime: '2026-02-10T08:00:00Z', nextOnCall: 'Priya Patel' },
    { id: 'oc-3', team: 'Infrastructure', currentOnCall: 'James Wilson', email: 'james.w@company.com', startTime: '2026-02-09T08:00:00Z', endTime: '2026-02-10T08:00:00Z', nextOnCall: 'Sarah Chen' },
    { id: 'oc-4', team: 'Data Services', currentOnCall: 'Priya Patel', email: 'priya.p@company.com', startTime: '2026-02-09T08:00:00Z', endTime: '2026-02-10T08:00:00Z', nextOnCall: 'Mike Rodriguez' },
];

const mockMetrics: MetricEntry[] = [
    { label: 'MTTA', value: '4.2', change: -12, unit: 'min' },
    { label: 'MTTR', value: '38', change: -8, unit: 'min' },
    { label: 'Incidents (24h)', value: '5', change: 25, unit: '' },
    { label: 'Uptime (30d)', value: '99.94', change: 0.02, unit: '%' },
];

// ─── API Functions ───────────────────────────────────────────────────────────

const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export async function fetchIncidents(): Promise<Incident[]> {
    await delay(600);
    return [...mockIncidents];
}

export async function fetchIncidentById(id: string): Promise<Incident | null> {
    await delay(400);
    return mockIncidents.find((inc) => inc.id === id) ?? null;
}

export async function acknowledgeIncident(id: string): Promise<Incident> {
    await delay(800);
    const incident = mockIncidents.find((inc) => inc.id === id);
    if (!incident) throw new Error(`Incident ${id} not found`);
    if (incident.status === 'resolved') throw new Error('Cannot acknowledge a resolved incident');

    incident.status = 'acknowledged';
    incident.updatedAt = new Date().toISOString();
    incident.timeline.push({
        id: `t${incident.timeline.length + 1}`,
        type: 'acknowledged',
        message: 'Incident acknowledged',
        timestamp: new Date().toISOString(),
        actor: incident.assignee,
    });

    return { ...incident };
}

export async function resolveIncident(id: string): Promise<Incident> {
    await delay(800);
    const incident = mockIncidents.find((inc) => inc.id === id);
    if (!incident) throw new Error(`Incident ${id} not found`);

    incident.status = 'resolved';
    incident.updatedAt = new Date().toISOString();
    incident.timeline.push({
        id: `t${incident.timeline.length + 1}`,
        type: 'resolved',
        message: 'Incident resolved',
        timestamp: new Date().toISOString(),
        actor: incident.assignee,
    });

    return { ...incident };
}

export async function fetchOnCallSchedules(): Promise<OnCallSchedule[]> {
    await delay(500);
    return [...mockOnCallSchedules];
}

export async function fetchMetrics(): Promise<MetricEntry[]> {
    await delay(700);
    return [...mockMetrics];
}

export async function fetchServiceHealth(): Promise<'healthy' | 'degraded' | 'down'> {
    await delay(300);
    return 'healthy';
}
