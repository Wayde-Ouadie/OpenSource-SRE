import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getIncidents } from '../services/api';
import type { Incident, Severity } from '../types';
import AddIncidentModal from '../components/AddIncidentModal';
import {
  timeAgo,
  statusBgClass,
  severityBadgeClass,
  severityDotClass,
  severityOrder,
  statusLabel,
  severityLabel,
} from '../utils/helpers';

type SortKey = 'severity' | 'status' | 'createdAt' | 'service';

export default function Dashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>('severity');
  const [sortAsc, setSortAsc] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const data = await getIncidents();
      setIncidents(data);
    } catch {
      /* handled gracefully */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const active = incidents.filter((i) => i.status !== 'resolved');
  const resolved = incidents.filter((i) => i.status === 'resolved');

  const bySeverity = (s: Severity) => active.filter((i) => i.severity === s).length;

  const avgMtta = (() => {
    const acked = incidents.filter((i) => i.acknowledgedAt);
    if (!acked.length) return null;
    const sum = acked.reduce(
      (a, i) => a + (new Date(i.acknowledgedAt!).getTime() - new Date(i.createdAt).getTime()),
      0,
    );
    return Math.round(sum / acked.length / 60000);
  })();

  const avgMttr = (() => {
    const res = incidents.filter((i) => i.resolvedAt);
    if (!res.length) return null;
    const sum = res.reduce(
      (a, i) => a + (new Date(i.resolvedAt!).getTime() - new Date(i.createdAt).getTime()),
      0,
    );
    return Math.round(sum / res.length / 60000);
  })();

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(true);
    }
  };

  const sortedActive = [...active].sort((a, b) => {
    let cmp = 0;
    switch (sortKey) {
      case 'severity':
        cmp = severityOrder[a.severity] - severityOrder[b.severity];
        break;
      case 'status':
        cmp = a.status.localeCompare(b.status);
        break;
      case 'createdAt':
        cmp = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        break;
      case 'service':
        cmp = a.service.localeCompare(b.service);
        break;
    }
    return sortAsc ? cmp : -cmp;
  });

  if (loading)
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-text-muted text-sm">
        <span className="w-4.5 h-4.5 border-2 border-border border-t-accent rounded-full animate-spin" />
        Loading…
      </div>
    );

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <h1>Dashboard</h1>
        <button
          onClick={() => setShowAddModal(true)}
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-accent hover:bg-accent-hover transition-colors shadow-sm cursor-pointer"
        >
          <span className="text-base leading-none">+</span> Add Incident
        </button>
      </div>
      <p className="text-text-muted text-sm mb-6">Real-time incident overview</p>

      {/* ── Stats ── */}
      <div className="flex flex-col gap-3 mb-8">
        {/* Top row: hero + MTTA/MTTR */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {/* Hero card */}
          <div className="bg-surface border border-border rounded-xl p-5 flex items-center gap-5 shadow-sm hover:shadow-md hover:border-border-light transition-all">
            <span className="text-5xl font-extrabold tracking-tighter leading-none text-text">
              {active.length}
            </span>
            <div className="flex flex-col gap-0.5">
              <span className="text-[0.95rem] font-semibold text-text">Open Incidents</span>
              <span className="text-xs text-text-muted">{incidents.length} total tracked</span>
            </div>
          </div>

          {/* MTTA / MTTR */}
          <div className="flex flex-col gap-3">
            <StatCompact icon="⏱" value={avgMtta !== null ? `${avgMtta}m` : '—'} label="Avg MTTA" />
            <StatCompact icon="🔧" value={avgMttr !== null ? `${avgMttr}m` : '—'} label="Avg MTTR" />
          </div>
        </div>

        {/* Severity breakdown row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {(['critical', 'high', 'medium', 'low'] as const).map((sev) => {
            const count = bySeverity(sev);
            const total = active.length || 1;
            return (
              <div
                key={sev}
                className="bg-surface border border-border rounded-xl p-4 flex flex-col gap-2 shadow-sm hover:shadow-md hover:border-border-light transition-all"
              >
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${severityDotClass[sev]}`} />
                  <span className="text-[0.7rem] uppercase tracking-wide font-semibold text-text-muted">
                    {sev}
                  </span>
                </div>
                <span className="text-2xl font-bold tracking-tight leading-none text-text">
                  {count}
                </span>
                <div className="h-1 bg-bg-subtle rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-400 ${severityDotClass[sev]}`}
                    style={{ width: `${Math.max(Math.round((count / total) * 100), 2)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Active incidents table ── */}
      <div className="flex items-center justify-between mb-3">
        <h2>Active Incidents</h2>
        <span className="text-[0.72rem] font-medium text-text-muted bg-bg-subtle px-2.5 py-0.5 rounded-full">
          {sortedActive.length} total
        </span>
      </div>

      {sortedActive.length === 0 ? (
        <div className="py-12 text-center text-text-muted bg-surface border border-border rounded-xl">
          No active incidents 🎉
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-xl overflow-hidden shadow-sm mb-8">
          <table className="w-full border-collapse">
            <thead className="bg-bg-subtle">
              <tr>
                <Th>ID</Th>
                <Th sortable onClick={() => handleSort('service')}>
                  Service{' '}
                  <SortArrow active={sortKey === 'service'} asc={sortAsc} />
                </Th>
                <Th sortable onClick={() => handleSort('severity')}>
                  Severity{' '}
                  <SortArrow active={sortKey === 'severity'} asc={sortAsc} />
                </Th>
                <Th sortable onClick={() => handleSort('status')}>
                  Status{' '}
                  <SortArrow active={sortKey === 'status'} asc={sortAsc} />
                </Th>
                <Th>Assigned</Th>
                <Th sortable onClick={() => handleSort('createdAt')}>
                  Created{' '}
                  <SortArrow active={sortKey === 'createdAt'} asc={sortAsc} />
                </Th>
              </tr>
            </thead>
            <tbody>
              {sortedActive.map((inc) => (
                <tr
                  key={inc.id}
                  className="border-b border-border last:border-b-0 hover:bg-surface-hover transition-colors"
                >
                  <Td>
                    <Link
                      to={`/incidents/${inc.id}`}
                      className="text-accent font-semibold text-sm no-underline hover:text-accent-hover hover:underline"
                    >
                      {inc.id}
                    </Link>
                  </Td>
                  <Td>
                    <span className="font-mono text-xs text-text-secondary">{inc.service}</span>
                  </Td>
                  <Td>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[0.72rem] font-semibold leading-none whitespace-nowrap ${severityBadgeClass[inc.severity]}`}
                    >
                      {severityLabel(inc.severity)}
                    </span>
                  </Td>
                  <Td>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[0.72rem] font-semibold leading-none whitespace-nowrap text-white ${statusBgClass[inc.status]}`}
                    >
                      {statusLabel(inc.status)}
                    </span>
                  </Td>
                  <Td>
                    <span className="text-[0.83rem]">{inc.assignedTo}</span>
                  </Td>
                  <Td>
                    <span className="text-xs text-text-muted" title={inc.createdAt}>
                      {timeAgo(inc.createdAt)}
                    </span>
                  </Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Recently resolved ── */}
      {resolved.length > 0 && (
        <div className="opacity-65 hover:opacity-90 transition-opacity">
          <div className="flex items-center justify-between mb-3">
            <h2>Recently Resolved</h2>
            <span className="text-[0.72rem] font-medium text-text-muted bg-bg-subtle px-2.5 py-0.5 rounded-full">
              {resolved.length}
            </span>
          </div>
          <div className="bg-surface border border-border rounded-xl overflow-hidden shadow-sm mb-8">
            <table className="w-full border-collapse">
              <thead className="bg-bg-subtle">
                <tr>
                  <Th>ID</Th>
                  <Th>Service</Th>
                  <Th>Severity</Th>
                  <Th>Assigned</Th>
                  <Th>Resolved</Th>
                </tr>
              </thead>
              <tbody>
                {resolved.map((inc) => (
                  <tr
                    key={inc.id}
                    className="border-b border-border last:border-b-0 hover:bg-surface-hover transition-colors"
                  >
                    <Td>
                      <Link
                        to={`/incidents/${inc.id}`}
                        className="text-accent font-semibold text-sm no-underline hover:text-accent-hover hover:underline"
                      >
                        {inc.id}
                      </Link>
                    </Td>
                    <Td>
                      <span className="font-mono text-xs text-text-secondary">{inc.service}</span>
                    </Td>
                    <Td>
                      <span
                        className={`inline-flex items-center px-2 py-0.5 rounded text-[0.72rem] font-semibold leading-none whitespace-nowrap ${severityBadgeClass[inc.severity]}`}
                      >
                        {severityLabel(inc.severity)}
                      </span>
                    </Td>
                    <Td>
                      <span className="text-[0.83rem]">{inc.assignedTo}</span>
                    </Td>
                    <Td>
                      <span className="text-xs text-text-muted" title={inc.resolvedAt}>
                        {inc.resolvedAt ? timeAgo(inc.resolvedAt) : '—'}
                      </span>
                    </Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      <AddIncidentModal
        open={showAddModal}
        onClose={() => setShowAddModal(false)}
        onCreated={fetchData}
      />
    </div>
  );
}

/* ── Small helper components ── */

function StatCompact({ icon, value, label }: { icon: string; value: string; label: string }) {
  return (
    <div className="bg-surface border border-border rounded-xl px-4 py-3 flex items-center gap-3 flex-1 shadow-sm hover:shadow-md hover:border-border-light transition-all">
      <span className="text-lg w-9 h-9 flex items-center justify-center bg-bg-subtle rounded-md shrink-0">
        {icon}
      </span>
      <div className="flex flex-col gap-px">
        <span className="text-xl font-bold text-text tracking-tight leading-tight">{value}</span>
        <span className="text-[0.68rem] text-text-muted uppercase tracking-wide font-medium">
          {label}
        </span>
      </div>
    </div>
  );
}

function Th({
  children,
  sortable,
  onClick,
}: {
  children: React.ReactNode;
  sortable?: boolean;
  onClick?: () => void;
}) {
  return (
    <th
      className={`text-left px-4 py-2.5 text-[0.7rem] uppercase text-text-muted tracking-wide font-semibold border-b border-border ${
        sortable ? 'cursor-pointer select-none hover:text-text' : ''
      }`}
      onClick={onClick}
    >
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="text-left px-4 py-2.5 text-sm text-text-secondary">{children}</td>;
}

function SortArrow({ active, asc }: { active: boolean; asc: boolean }) {
  if (!active) return null;
  return <span className="text-[0.65rem] ml-0.5 opacity-70">{asc ? '↑' : '↓'}</span>;
}
