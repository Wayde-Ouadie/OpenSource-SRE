import type { Incident, IncidentStatus, OnCallEngineer, EscalationPolicy, MetricsData, Severity } from '../types';
import { mockIncidents, mockOnCall, mockEscalationPolicies, mockMetrics } from '../data/mock';

// Base URL — empty string in production (nginx proxies /api/), configurable for dev
const API_BASE = '';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map backend incident JSON to frontend Incident type */
function mapIncident(raw: any): Incident {
  return {
    id: raw.id,
    service: raw.service,
    severity: raw.severity,
    status: raw.status,
    title: raw.title,
    description: raw.description || '',
    assignedTo: raw.assigned_to || 'Unassigned',
    createdAt: raw.created_at,
    acknowledgedAt: raw.acknowledged_at || undefined,
    resolvedAt: raw.resolved_at || undefined,
    alerts: (raw.alerts || []).map((a: any) => ({
      id: a.id,
      source: a.source || a.service || '',
      message: a.message || '',
      timestamp: a.timestamp || a.created_at || '',
    })),
    timeline: (raw.timeline || []).map((t: any) => ({
      id: t.id,
      type: t.type,
      message: t.detail || t.message || '',
      timestamp: t.timestamp,
      actor: t.actor || undefined,
    })),
    notes: raw.notes || [],
  };
}

// ---------------------------------------------------------------------------
// Incidents (live API with mock fallback)
// ---------------------------------------------------------------------------

export async function getIncidents(): Promise<Incident[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/incidents?limit=100`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return (data.items || []).map(mapIncident);
  } catch {
    // Fallback to mock data when backend is unavailable
    return structuredClone(mockIncidents);
  }
}

export async function getIncident(id: string): Promise<Incident | undefined> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/incidents/${id}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.json();
    return mapIncident(raw);
  } catch {
    return structuredClone(mockIncidents.find((i) => i.id === id));
  }
}

export interface CreateIncidentPayload {
  service: string;
  severity: Severity;
  title: string;
  description: string;
  assigned_to: string;
}

export async function createIncident(payload: CreateIncidentPayload): Promise<Incident> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/incidents`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw = await res.json();
    return mapIncident(raw);
  } catch {
    // Fallback: create a mock incident locally
    const now = new Date().toISOString();
    const newIncident: Incident = {
      id: `INC-${String(mockIncidents.length + 1).padStart(3, '0')}`,
      service: payload.service,
      severity: payload.severity,
      status: 'open',
      title: payload.title,
      description: payload.description,
      assignedTo: payload.assigned_to,
      createdAt: now,
      alerts: [],
      timeline: [
        {
          id: `TL-${Date.now()}`,
          type: 'created',
          message: `Incident manually created with severity '${payload.severity}'`,
          timestamp: now,
          actor: payload.assigned_to,
        },
      ],
    };
    mockIncidents.unshift(newIncident);
    return structuredClone(newIncident);
  }
}

export async function updateIncidentStatus(
  id: string,
  newStatus: IncidentStatus,
  _actor: string = 'You',
): Promise<Incident | undefined> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/incidents/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    // Re-fetch full incident after update
    return getIncident(id);
  } catch {
    // Fallback: mutate mock data
    const incident = mockIncidents.find((i) => i.id === id);
    if (!incident) return undefined;
    const now = new Date().toISOString();
    incident.status = newStatus;
    if (newStatus === 'acknowledged') incident.acknowledgedAt = now;
    if (newStatus === 'resolved') incident.resolvedAt = now;
    return structuredClone(incident);
  }
}

// ---------------------------------------------------------------------------
// On-Call (live API with mock fallback)
// ---------------------------------------------------------------------------

export async function getOnCallEngineers(): Promise<OnCallEngineer[]> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/schedules`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    // Transform schedules into OnCallEngineer entries
    const engineers: OnCallEngineer[] = [];
    for (const sched of data.items || []) {
      const team = sched.team;
      for (const name of sched.primary || []) {
        engineers.push({
          name,
          email: `${name.toLowerCase().replace(/ /g, '.')}@example.com`,
          team,
          role: 'primary',
          startTime: sched.starts_at,
          endTime: sched.starts_at, // placeholder
        });
      }
      for (const name of sched.secondary || []) {
        engineers.push({
          name,
          email: `${name.toLowerCase().replace(/ /g, '.')}@example.com`,
          team,
          role: 'secondary',
          startTime: sched.starts_at,
          endTime: sched.starts_at,
        });
      }
    }
    return engineers.length > 0 ? engineers : structuredClone(mockOnCall);
  } catch {
    return structuredClone(mockOnCall);
  }
}

export async function getEscalationPolicies(): Promise<EscalationPolicy[]> {
  // Escalation policies are not persisted in the backend — use mock data
  return structuredClone(mockEscalationPolicies);
}

// ---------------------------------------------------------------------------
// Metrics (computed from live incidents with mock fallback)
// ---------------------------------------------------------------------------

export async function getMetrics(): Promise<MetricsData> {
  try {
    const incidents = await getIncidents();
    if (incidents.length === 0) return structuredClone(mockMetrics);

    // Build MTTA trend (last 14 days)
    const now = new Date();
    const days = 14;
    const mttaTrend: { date: string; value: number }[] = [];
    const mttrTrend: { date: string; value: number }[] = [];
    const incidentVolume: { date: string; count: number }[] = [];

    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now.getTime() - i * 86400000);
      const dateStr = d.toISOString().slice(0, 10);

      const dayIncidents = incidents.filter((inc) => inc.createdAt.slice(0, 10) === dateStr);
      incidentVolume.push({ date: dateStr, count: dayIncidents.length });

      const acked = dayIncidents.filter((inc) => inc.acknowledgedAt);
      if (acked.length) {
        const avg = acked.reduce(
          (sum, inc) =>
            sum + (new Date(inc.acknowledgedAt!).getTime() - new Date(inc.createdAt).getTime()) / 60000,
          0,
        ) / acked.length;
        mttaTrend.push({ date: dateStr, value: Math.round(avg * 10) / 10 });
      } else {
        mttaTrend.push({ date: dateStr, value: 0 });
      }

      const resolved = dayIncidents.filter((inc) => inc.resolvedAt);
      if (resolved.length) {
        const avg = resolved.reduce(
          (sum, inc) =>
            sum + (new Date(inc.resolvedAt!).getTime() - new Date(inc.createdAt).getTime()) / 60000,
          0,
        ) / resolved.length;
        mttrTrend.push({ date: dateStr, value: Math.round(avg * 10) / 10 });
      } else {
        mttrTrend.push({ date: dateStr, value: 0 });
      }
    }

    // Incidents per service
    const serviceMap: Record<string, number> = {};
    for (const inc of incidents) {
      serviceMap[inc.service] = (serviceMap[inc.service] || 0) + 1;
    }
    const incidentsPerService = Object.entries(serviceMap)
      .map(([service, count]) => ({ service, count }))
      .sort((a, b) => b.count - a.count);

    return { mttaTrend, mttrTrend, incidentsPerService, incidentVolume };
  } catch {
    return structuredClone(mockMetrics);
  }
}
