import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getIncident, updateIncidentStatus } from '../services/api';
import type { Incident, IncidentStatus } from '../types';
import { timeAgo, statusColors, statusLabel, severityLabel, validTransitions } from '../utils/helpers';
import './IncidentDetail.css';

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState<IncidentStatus | null>(null);
  const [updating, setUpdating] = useState(false);

  const fetchIncident = useCallback(async () => {
    if (!id) return;
    try {
      const data = await getIncident(id);
      if (data) setIncident(data);
    } catch {
      /* handled */
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchIncident();
  }, [fetchIncident]);

  const handleAction = async (newStatus: IncidentStatus) => {
    // Require confirmation only for resolve
    if (newStatus === 'resolved' && confirming !== 'resolved') {
      setConfirming('resolved');
      return;
    }
    setConfirming(null);
    setUpdating(true);
    const updated = await updateIncidentStatus(id!, newStatus);
    if (updated) setIncident(updated);
    setUpdating(false);
  };

  if (loading) return <div className="loading">Loading…</div>;
  if (!incident) return <div className="error-state">Incident not found</div>;

  const transitions = validTransitions(incident.status);

  return (
    <div className="incident-detail">
      <Link to="/" className="back-link">← Back to Dashboard</Link>

      <header className="detail-header">
        <div>
          <h1>{incident.id}: {incident.title}</h1>
          <p className="detail-meta">
            <span className={`badge severity-${incident.severity}`}>{severityLabel(incident.severity)}</span>
            <span className="badge" style={{ background: statusColors[incident.status] }}>{statusLabel(incident.status)}</span>
            <span className="meta-text">{incident.service}</span>
            <span className="meta-text">Assigned to <strong>{incident.assignedTo}</strong></span>
          </p>
        </div>
        <div className="actions">
          {transitions.map((t) => (
            <button
              key={t}
              className={`action-btn action-${t}`}
              onClick={() => handleAction(t)}
              disabled={updating}
            >
              {t === 'acknowledged' && '✅ Acknowledge'}
              {t === 'in_progress' && '🔧 In Progress'}
              {t === 'resolved' && (confirming === 'resolved' ? 'Confirm Resolve?' : '🟢 Resolve')}
            </button>
          ))}
          {confirming === 'resolved' && (
            <button className="action-btn cancel-btn" onClick={() => setConfirming(null)}>Cancel</button>
          )}
        </div>
      </header>

      <p className="description">{incident.description}</p>

      <div className="detail-grid">
        {/* Timestamps */}
        <section className="detail-section">
          <h3>Timestamps</h3>
          <dl>
            <dt>Created</dt>
            <dd title={incident.createdAt}>{timeAgo(incident.createdAt)}</dd>
            {incident.acknowledgedAt && (
              <>
                <dt>Acknowledged</dt>
                <dd title={incident.acknowledgedAt}>{timeAgo(incident.acknowledgedAt)}</dd>
              </>
            )}
            {incident.resolvedAt && (
              <>
                <dt>Resolved</dt>
                <dd title={incident.resolvedAt}>{timeAgo(incident.resolvedAt)}</dd>
              </>
            )}
          </dl>
        </section>

        {/* Linked alerts */}
        <section className="detail-section">
          <h3>Linked Alerts</h3>
          {incident.alerts.length === 0 ? (
            <p className="muted">No alerts linked</p>
          ) : (
            <ul className="alert-list">
              {incident.alerts.map((a) => (
                <li key={a.id}>
                  <strong>{a.source}</strong>: {a.message}
                  <span className="muted block">{timeAgo(a.timestamp)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Timeline */}
      <section className="detail-section">
        <h3>Timeline</h3>
        <ol className="timeline">
          {incident.timeline.map((e) => (
            <li key={e.id} className={`timeline-event type-${e.type}`}>
              <span className="tl-dot" style={{ background: statusColors[e.type as IncidentStatus] || 'var(--border)' }} />
              <div className="tl-content">
                <span className="tl-message">{e.message}</span>
                <span className="tl-meta">{e.actor && `${e.actor} · `}{timeAgo(e.timestamp)}</span>
              </div>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
