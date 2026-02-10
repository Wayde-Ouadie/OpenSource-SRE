import { formatDistanceToNow } from 'date-fns';
import type { IncidentStatus, Severity } from '../types';

export function timeAgo(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

/** Tailwind bg classes for status badges */
export const statusBgClass: Record<IncidentStatus, string> = {
  open: 'bg-status-open',
  acknowledged: 'bg-status-ack',
  in_progress: 'bg-status-ip',
  resolved: 'bg-status-resolved',
};

/** Tailwind bg + text classes for severity badges */
export const severityBadgeClass: Record<Severity, string> = {
  critical: 'bg-sev-critical-bg text-sev-critical',
  high: 'bg-sev-high-bg text-sev-high',
  medium: 'bg-sev-medium-bg text-sev-medium',
  low: 'bg-sev-low-bg text-sev-low',
};

/** Tailwind bg color for severity dots/bars */
export const severityDotClass: Record<Severity, string> = {
  critical: 'bg-sev-critical',
  high: 'bg-sev-high',
  medium: 'bg-sev-medium',
  low: 'bg-sev-low',
};

/** Raw hex for recharts / inline usage */
export const statusColorHex: Record<IncidentStatus, string> = {
  open: '#ef4444',
  acknowledged: '#f59e0b',
  in_progress: '#3b82f6',
  resolved: '#22c55e',
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
