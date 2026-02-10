export type Severity = 'critical' | 'high' | 'medium' | 'low';
export type IncidentStatus = 'open' | 'acknowledged' | 'in_progress' | 'resolved';

export interface Incident {
  id: string;
  service: string;
  severity: Severity;
  status: IncidentStatus;
  title: string;
  description: string;
  assignedTo: string;
  createdAt: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  alerts: Alert[];
  timeline: TimelineEvent[];
}

export interface Alert {
  id: string;
  source: string;
  message: string;
  timestamp: string;
}

export interface TimelineEvent {
  id: string;
  type: 'created' | 'acknowledged' | 'in_progress' | 'resolved' | 'note';
  message: string;
  timestamp: string;
  actor?: string;
}

export interface OnCallEngineer {
  name: string;
  email: string;
  team: string;
  role: 'primary' | 'secondary';
  startTime: string;
  endTime: string;
}

export interface EscalationPolicy {
  team: string;
  levels: { level: number; target: string; timeout: string }[];
}

export interface MetricsData {
  mttaTrend: { date: string; value: number }[];
  mttrTrend: { date: string; value: number }[];
  incidentsPerService: { service: string; count: number }[];
  incidentVolume: { date: string; count: number }[];
}
