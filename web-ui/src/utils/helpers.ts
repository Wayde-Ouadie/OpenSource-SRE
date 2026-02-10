import { formatDistanceToNow } from 'date-fns';
import type { IncidentStatus, Severity } from '../types';

export function timeAgo(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

export const statusColors: Record<IncidentStatus, string> = {
  open: 'var(--color-open)',
  acknowledged: 'var(--color-acknowledged)',
  in_progress: 'var(--color-in-progress)',
  resolved: 'var(--color-resolved)',
};

export const severityOrder: Record<Severity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

export function statusLabel(s: IncidentStatus): string {
  return s.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export function severityLabel(s: Severity): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/** Returns the valid next statuses from a given status */
export function validTransitions(current: IncidentStatus): IncidentStatus[] {
  switch (current) {
    case 'open':
      return ['acknowledged'];
    case 'acknowledged':
      return ['in_progress', 'resolved'];
    case 'in_progress':
      return ['resolved'];
    case 'resolved':
      return [];
  }
}
