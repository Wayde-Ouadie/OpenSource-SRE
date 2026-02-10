import type { Incident, IncidentStatus, OnCallEngineer, EscalationPolicy, MetricsData } from '../types';
import { mockIncidents, mockOnCall, mockEscalationPolicies, mockMetrics } from '../data/mock';

// Simulate async API calls with a small delay
const delay = (ms = 200) => new Promise((r) => setTimeout(r, ms));

// In-memory store so mutations persist during the session
let incidents: Incident[] = structuredClone(mockIncidents);

export async function getIncidents(): Promise<Incident[]> {
  await delay();
  return structuredClone(incidents);
}

export async function getIncident(id: string): Promise<Incident | undefined> {
  await delay();
  return structuredClone(incidents.find((i) => i.id === id));
}

export async function updateIncidentStatus(
  id: string,
  newStatus: IncidentStatus,
  actor: string = 'You',
): Promise<Incident | undefined> {
  await delay(100);
  const incident = incidents.find((i) => i.id === id);
  if (!incident) return undefined;

  const now = new Date().toISOString();
  incident.status = newStatus;

  if (newStatus === 'acknowledged') incident.acknowledgedAt = now;
  if (newStatus === 'resolved') incident.resolvedAt = now;

  incident.timeline.push({
    id: `TL-${Date.now()}`,
    type: newStatus === 'in_progress' ? 'in_progress' : newStatus as 'acknowledged' | 'resolved',
    message: `Incident ${newStatus.replace('_', ' ')}`,
    timestamp: now,
    actor,
  });

  return structuredClone(incident);
}

export async function getOnCallEngineers(): Promise<OnCallEngineer[]> {
  await delay();
  return structuredClone(mockOnCall);
}

export async function getEscalationPolicies(): Promise<EscalationPolicy[]> {
  await delay();
  return structuredClone(mockEscalationPolicies);
}

export async function getMetrics(): Promise<MetricsData> {
  await delay();
  return structuredClone(mockMetrics);
}
