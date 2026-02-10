import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { getIncidents } from '../services/api';
import type { Incident, Severity } from '../types';
import { timeAgo, statusColors, severityOrder, statusLabel, severityLabel } from '../utils/helpers';
import './Dashboard.css';

type SortKey = 'severity' | 'status' | 'createdAt' | 'service';

export default function Dashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>('severity');
  const [sortAsc, setSortAsc] = useState(true);

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

  // Stats
  const bySeverity = (s: Severity) => active.filter((i) => i.severity === s).length;

  const avgMtta = (() => {
    const acked = incidents.filter((i) => i.acknowledgedAt);
    if (!acked.length) return null;
    const sum = acked.reduce((a, i) => a + (new Date(i.acknowledgedAt!).getTime() - new Date(i.createdAt).getTime()), 0);
    return Math.round(sum / acked.length / 60000);
  })();

  const avgMttr = (() => {
    const res = incidents.filter((i) => i.resolvedAt);
    if (!res.length) return null;
    const sum = res.reduce((a, i) => a + (new Date(i.resolvedAt!).getTime() - new Date(i.createdAt).getTime()), 0);
    return Math.round(sum / res.length / 60000);
  })();

  // Sorting
  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortAsc(!sortAsc);
    else { setSortKey(key); setSortAsc(true); }
  };

  const sortedActive = [...active].sort((a, b) => {
    let cmp = 0;
    switch (sortKey) {
      case 'severity': cmp = severityOrder[a.severity] - severityOrder[b.severity]; break;
      case 'status': cmp = a.status.localeCompare(b.status); break;
      case 'createdAt': cmp = new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime(); break;
      case 'service': cmp = a.service.localeCompare(b.service); break;
    }
    return sortAsc ? cmp : -cmp;
  });

  if (loading) return <div className="loading">Loading…</div>;

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      <p className="dashboard-subtitle">Real-time incident overview</p>

      {/* Stats */}
      <div className="stats-overview">
        {/* Hero + response times row */}
        <div className="stats-row-top">
          <div className="stat-hero">
            <span className="hero-value">{active.length}</span>
            <div className="hero-text">
              <span className="hero-label">Open Incidents</span>
              <span className="hero-sub">{incidents.length} total tracked</span>
            </div>
          </div>
          <div className="stat-pair">
            <div className="stat-card compact">
              <span className="stat-icon">⏱</span>
              <div className="stat-text">
                <span className="stat-value">{avgMtta !== null ? `${avgMtta}m` : '—'}</span>
                <span className="stat-label">Avg MTTA</span>
              </div>
            </div>
            <div className="stat-card compact">
              <span className="stat-icon">🔧</span>
              <div className="stat-text">
                <span className="stat-value">{avgMttr !== null ? `${avgMttr}m` : '—'}</span>
                <span className="stat-label">Avg MTTR</span>
              </div>
            </div>
          </div>
        </div>

        {/* Severity breakdown row */}
        <div className="severity-row">
          {(['critical', 'high', 'medium', 'low'] as const).map((sev) => {
            const count = bySeverity(sev);
            const total = active.length || 1;
            return (
              <div key={sev} className={`sev-card ${sev}`}>
                <div className="sev-header">
                  <span className="sev-dot" />
                  <span className="sev-name">{sev}</span>
                </div>
                <span className="sev-value">{count}</span>
                <div className="sev-bar-track">
                  <div
                    className="sev-bar-fill"
                    style={{ width: `${Math.round((count / total) * 100)}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Active incidents table */}
      <div className="section-header">
        <h2>Active Incidents</h2>
        <span className="section-count">{sortedActive.length} total</span>
      </div>
      {sortedActive.length === 0 ? (
        <p className="empty-state">No active incidents 🎉</p>
      ) : (
        <div className="table-wrapper">
          <table className="incident-table">
            <thead>
              <tr>
                <th>ID</th>
                <th className="sortable" onClick={() => handleSort('service')}>
                  Service <span className="sort-indicator">{sortKey === 'service' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
                <th className="sortable" onClick={() => handleSort('severity')}>
                  Severity <span className="sort-indicator">{sortKey === 'severity' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
                <th className="sortable" onClick={() => handleSort('status')}>
                  Status <span className="sort-indicator">{sortKey === 'status' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
                <th>Assigned</th>
                <th className="sortable" onClick={() => handleSort('createdAt')}>
                  Created <span className="sort-indicator">{sortKey === 'createdAt' ? (sortAsc ? '↑' : '↓') : ''}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {sortedActive.map((inc) => (
                <tr key={inc.id}>
                  <td>
                    <Link to={`/incidents/${inc.id}`} className="incident-link">{inc.id}</Link>
                  </td>
                  <td><span className="service-name">{inc.service}</span></td>
                  <td>
                    <span className={`badge severity-${inc.severity}`}>{severityLabel(inc.severity)}</span>
                  </td>
                  <td>
                    <span className="badge" style={{ background: statusColors[inc.status] }}>
                      {statusLabel(inc.status)}
                    </span>
                  </td>
                  <td><span className="assigned-name">{inc.assignedTo}</span></td>
                  <td className="time-cell" title={inc.createdAt}>{timeAgo(inc.createdAt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Recently resolved */}
      {resolved.length > 0 && (
        <div className="resolved-section">
          <div className="section-header">
            <h2>Recently Resolved</h2>
            <span className="section-count">{resolved.length}</span>
          </div>
          <div className="table-wrapper">
            <table className="incident-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Service</th>
                  <th>Severity</th>
                  <th>Assigned</th>
                  <th>Resolved</th>
                </tr>
              </thead>
              <tbody>
                {resolved.map((inc) => (
                  <tr key={inc.id}>
                    <td>
                      <Link to={`/incidents/${inc.id}`} className="incident-link">{inc.id}</Link>
                    </td>
                    <td><span className="service-name">{inc.service}</span></td>
                    <td>
                      <span className={`badge severity-${inc.severity}`}>{severityLabel(inc.severity)}</span>
                    </td>
                    <td><span className="assigned-name">{inc.assignedTo}</span></td>
                    <td className="time-cell" title={inc.resolvedAt}>{inc.resolvedAt ? timeAgo(inc.resolvedAt) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
