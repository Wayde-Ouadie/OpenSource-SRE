import { useState } from 'react';
import type { Severity } from '../types';
import { createIncident } from '../services/api';
import type { CreateIncidentPayload } from '../services/api';

interface AddIncidentModalProps {
  open: boolean;
  onClose: () => void;
  onCreated: () => void;
}

const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low'];

export default function AddIncidentModal({ open, onClose, onCreated }: AddIncidentModalProps) {
  const [service, setService] = useState('');
  const [severity, setSeverity] = useState<Severity>('medium');
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [assignedTo, setAssignedTo] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  const isValid = service.trim() && title.trim() && description.trim() && assignedTo.trim();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid) return;

    setSubmitting(true);
    setError(null);

    try {
      const payload: CreateIncidentPayload = {
        service: service.trim(),
        severity,
        title: title.trim(),
        description: description.trim(),
        assigned_to: assignedTo.trim(),
      };
      await createIncident(payload);
      // Reset form
      setService('');
      setSeverity('medium');
      setTitle('');
      setDescription('');
      setAssignedTo('');
      onCreated();
      onClose();
    } catch {
      setError('Failed to create incident. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-surface border border-border rounded-xl shadow-lg w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="text-lg font-semibold text-text">Create Incident</h2>
          <button
            onClick={onClose}
            className="text-text-muted hover:text-text transition-colors text-xl leading-none cursor-pointer"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-5 flex flex-col gap-4">
          {error && (
            <div className="text-sm text-sev-critical bg-sev-critical-bg border border-sev-critical/20 rounded-lg px-3 py-2">
              {error}
            </div>
          )}

          {/* Title */}
          <Field label="Title" required>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Payment API returning 500 errors"
              className="w-full bg-bg-subtle border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
              required
            />
          </Field>

          {/* Service */}
          <Field label="Service" required>
            <input
              type="text"
              value={service}
              onChange={(e) => setService(e.target.value)}
              placeholder="e.g. payment-api"
              className="w-full bg-bg-subtle border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
              required
            />
          </Field>

          {/* Severity */}
          <Field label="Severity" required>
            <div className="flex gap-2">
              {SEVERITIES.map((sev) => (
                <button
                  key={sev}
                  type="button"
                  onClick={() => setSeverity(sev)}
                  className={`flex-1 px-3 py-2 rounded-lg text-xs font-semibold uppercase tracking-wide border transition-all cursor-pointer ${
                    severity === sev
                      ? sevActiveClass[sev]
                      : 'bg-bg-subtle border-border text-text-muted hover:border-border-light'
                  }`}
                >
                  {sev}
                </button>
              ))}
            </div>
          </Field>

          {/* Description */}
          <Field label="Description" required>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the incident in detail…"
              rows={3}
              className="w-full bg-bg-subtle border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors resize-y"
              required
            />
          </Field>

          {/* Assigned To */}
          <Field label="Assigned To" required>
            <input
              type="text"
              value={assignedTo}
              onChange={(e) => setAssignedTo(e.target.value)}
              placeholder="e.g. Alice Chen"
              className="w-full bg-bg-subtle border border-border rounded-lg px-3 py-2 text-sm text-text placeholder:text-text-muted focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/30 transition-colors"
              required
            />
          </Field>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium text-text-muted bg-bg-subtle border border-border hover:bg-surface-hover hover:text-text transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!isValid || submitting}
              className="px-4 py-2 rounded-lg text-sm font-semibold text-white bg-accent hover:bg-accent-hover disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer"
            >
              {submitting ? 'Creating…' : 'Create Incident'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Helper components ── */

function Field({
  label,
  required,
  children,
}: {
  label: string;
  required?: boolean;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-semibold text-text-muted uppercase tracking-wide">
        {label}
        {required && <span className="text-sev-critical ml-0.5">*</span>}
      </span>
      {children}
    </label>
  );
}

const sevActiveClass: Record<Severity, string> = {
  critical: 'bg-sev-critical-bg border-sev-critical/40 text-sev-critical',
  high: 'bg-sev-high-bg border-sev-high/40 text-sev-high',
  medium: 'bg-sev-medium-bg border-sev-medium/40 text-sev-medium',
  low: 'bg-sev-low-bg border-sev-low/40 text-sev-low',
};
