import { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getIncident, updateIncidentStatus, addNote } from '../services/api';
import type { Incident, IncidentStatus } from '../types';
import {
  timeAgo,
  statusBgClass,
  severityBadgeClass,
  statusColorHex,
  statusLabel,
  severityLabel,
  validTransitions,
} from '../utils/helpers';

const actionBtnColors: Record<string, string> = {
  acknowledged: 'bg-status-ack hover:bg-status-ack/90',
  in_progress: 'bg-status-ip hover:bg-status-ip/90',
  resolved: 'bg-status-resolved hover:bg-status-resolved/90',
};

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [confirming, setConfirming] = useState<IncidentStatus | null>(null);
  const [updating, setUpdating] = useState(false);
  const [noteContent, setNoteContent] = useState('');
  const [noteAuthor, setNoteAuthor] = useState('');
  const [submittingNote, setSubmittingNote] = useState(false);

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

  if (loading)
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-text-muted text-sm">
        <span className="w-4.5 h-4.5 border-2 border-border border-t-accent rounded-full animate-spin" />
        Loading…
      </div>
    );

  if (!incident)
    return (
      <div className="py-12 px-8 text-center text-text-muted bg-surface border border-border rounded-xl">
        Incident not found
      </div>
    );

  const transitions = validTransitions(incident.status);

  return (
    <div className="max-w-[920px]">
      {/* Back link */}
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-text-muted text-[0.82rem] font-medium no-underline py-1 mb-4 hover:text-accent"
      >
        ← Back to Dashboard
      </Link>

      {/* Header */}
      <header className="flex justify-between items-start gap-5 flex-wrap mb-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight mb-2">
            {incident.id}: {incident.title}
          </h1>
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[0.72rem] font-semibold leading-none whitespace-nowrap ${severityBadgeClass[incident.severity]}`}
            >
              {severityLabel(incident.severity)}
            </span>
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-[0.72rem] font-semibold leading-none whitespace-nowrap text-white ${statusBgClass[incident.status]}`}
            >
              {statusLabel(incident.status)}
            </span>
            <span className="text-text-muted text-[0.82rem]">{incident.service}</span>
            <span className="text-text-muted text-[0.82rem]">
              Assigned to <strong className="text-text">{incident.assignedTo}</strong>
            </span>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-2 shrink-0">
          {transitions.map((t) => (
            <button
              key={t}
              className={`inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-[0.82rem] font-semibold text-white cursor-pointer shadow-sm border-none hover:-translate-y-px hover:shadow-md active:translate-y-0 disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none ${actionBtnColors[t] || 'bg-text-muted'}`}
              onClick={() => handleAction(t)}
              disabled={updating}
            >
              {t === 'acknowledged' && '✅ Acknowledge'}
              {t === 'in_progress' && '🔧 In Progress'}
              {t === 'resolved' && (confirming === 'resolved' ? 'Confirm Resolve?' : '🟢 Resolve')}
            </button>
          ))}
          {confirming === 'resolved' && (
            <button
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md text-[0.82rem] font-semibold text-white cursor-pointer shadow-sm border-none bg-text-muted hover:bg-text-muted/80"
              onClick={() => setConfirming(null)}
            >
              Cancel
            </button>
          )}
        </div>
      </header>

      {/* Description */}
      <p className="text-text-secondary text-sm leading-relaxed mb-6 p-4 bg-surface border border-border rounded-xl">
        {incident.description}
      </p>

      {/* Grid: timestamps + alerts */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        {/* Timestamps */}
        <section className="bg-surface border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-[0.72rem] uppercase tracking-wide text-text-muted font-semibold pb-2 mb-3 border-b border-border">
            Timestamps
          </h3>
          <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-2 m-0">
            <dt className="font-semibold text-[0.82rem] text-text-secondary">Created</dt>
            <dd className="m-0 text-[0.82rem] text-text-muted" title={incident.createdAt}>
              {timeAgo(incident.createdAt)}
            </dd>
            {incident.acknowledgedAt && (
              <>
                <dt className="font-semibold text-[0.82rem] text-text-secondary">Acknowledged</dt>
                <dd className="m-0 text-[0.82rem] text-text-muted" title={incident.acknowledgedAt}>
                  {timeAgo(incident.acknowledgedAt)}
                </dd>
              </>
            )}
            {incident.resolvedAt && (
              <>
                <dt className="font-semibold text-[0.82rem] text-text-secondary">Resolved</dt>
                <dd className="m-0 text-[0.82rem] text-text-muted" title={incident.resolvedAt}>
                  {timeAgo(incident.resolvedAt)}
                </dd>
              </>
            )}
          </dl>
        </section>

        {/* Linked alerts */}
        <section className="bg-surface border border-border rounded-xl p-4 shadow-sm">
          <h3 className="text-[0.72rem] uppercase tracking-wide text-text-muted font-semibold pb-2 mb-3 border-b border-border">
            Linked Alerts
          </h3>
          {incident.alerts.length === 0 ? (
            <p className="text-text-muted text-sm">No alerts linked</p>
          ) : (
            <ul className="list-none p-0 m-0 flex flex-col gap-2.5">
              {incident.alerts.map((a) => (
                <li
                  key={a.id}
                  className="text-[0.83rem] p-2.5 bg-bg-subtle rounded-md border-l-[3px] border-l-accent"
                >
                  <strong>{a.source}</strong>: {a.message}
                  <span className="block mt-0.5 text-text-muted">{timeAgo(a.timestamp)}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Timeline */}
      <section className="bg-surface border border-border rounded-xl p-4 shadow-sm mb-4">
        <h3 className="text-[0.72rem] uppercase tracking-wide text-text-muted font-semibold pb-2 mb-3 border-b border-border">
          Timeline
        </h3>
        <ol className="list-none p-0 m-0 relative">
          {incident.timeline.map((e, i) => (
            <li key={e.id} className="flex gap-3 pb-4 relative">
              {/* Connecting line */}
              {i < incident.timeline.length - 1 && (
                <div className="absolute left-[8px] top-[22px] bottom-0 w-0.5 bg-border" />
              )}
              {/* Dot */}
              <span
                className="w-[18px] h-[18px] rounded-full shrink-0 mt-px border-2 border-surface"
                style={{
                  background: statusColorHex[e.type as IncidentStatus] || '#252836',
                  boxShadow: '0 0 0 2px var(--color-border)',
                }}
              />
              <div className="flex flex-col gap-px pt-px">
                <span className="text-sm text-text-secondary">{e.message}</span>
                <span className="text-[0.72rem] text-text-muted">
                  {e.actor && `${e.actor} · `}
                  {timeAgo(e.timestamp)}
                </span>
              </div>
            </li>
          ))}
        </ol>
      </section>

      {/* Notes */}
      <section className="bg-surface border border-border rounded-xl p-4 shadow-sm mb-4">
        <h3 className="text-[0.72rem] uppercase tracking-wide text-text-muted font-semibold pb-2 mb-3 border-b border-border">
          Notes &amp; Comments
        </h3>

        {/* Existing notes */}
        {incident.notes && incident.notes.length > 0 ? (
          <ul className="list-none p-0 m-0 flex flex-col gap-3 mb-4">
            {incident.notes.map((note) => (
              <li
                key={note.id}
                className="p-3 bg-bg-subtle rounded-lg border-l-[3px] border-l-accent"
              >
                <p className="text-sm text-text-secondary leading-relaxed m-0 whitespace-pre-wrap">
                  {note.content}
                </p>
                <span className="block mt-1.5 text-[0.72rem] text-text-muted">
                  <strong className="text-text-secondary">{note.author}</strong> ·{' '}
                  {timeAgo(note.created_at)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-text-muted text-sm mb-4">No notes yet. Be the first to add one.</p>
        )}

        {/* Add note form */}
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            if (!noteContent.trim() || !noteAuthor.trim()) return;
            setSubmittingNote(true);
            try {
              await addNote(incident.id, noteContent.trim(), noteAuthor.trim());
              setNoteContent('');
              setNoteAuthor('');
              // Refresh incident to get updated notes
              await fetchIncident();
            } catch {
              /* handled gracefully */
            } finally {
              setSubmittingNote(false);
            }
          }}
          className="flex flex-col gap-3 pt-3 border-t border-border"
        >
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">
              Your Name <span className="text-sev-critical">*</span>
            </label>
            <input
              type="text"
              value={noteAuthor}
              onChange={(e) => setNoteAuthor(e.target.value)}
              placeholder="e.g. Alice Chen"
              className="w-full bg-bg-subtle border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
              required
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-semibold text-text-muted uppercase tracking-wide">
              Comment <span className="text-sev-critical">*</span>
            </label>
            <textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Describe observations, potential causes, or solutions…"
              rows={3}
              className="w-full bg-bg-subtle border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors resize-y"
              required
            />
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!noteContent.trim() || !noteAuthor.trim() || submittingNote}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold text-white bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              {submittingNote ? 'Posting…' : '💬 Add Note'}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
