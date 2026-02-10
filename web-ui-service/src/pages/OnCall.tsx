import { useState, useEffect } from 'react';
import { getOnCallEngineers, getEscalationPolicies } from '../services/api';
import type { OnCallEngineer, EscalationPolicy } from '../types';
import { timeAgo } from '../utils/helpers';
import './OnCall.css';

export default function OnCall() {
  const [engineers, setEngineers] = useState<OnCallEngineer[]>([]);
  const [policies, setPolicies] = useState<EscalationPolicy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getOnCallEngineers(), getEscalationPolicies()])
      .then(([eng, pol]) => { setEngineers(eng); setPolicies(pol); })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading">Loading…</div>;

  // Group engineers by team
  const teams = Array.from(new Set(engineers.map((e) => e.team)));

  return (
    <div className="oncall-page">
      <h1>On-Call Schedule</h1>
      <p className="oncall-subtitle">Current rotation and escalation policies</p>

      <div className="oncall-grid">
        {teams.map((team) => {
          const members = engineers.filter((e) => e.team === team);
          const policy = policies.find((p) => p.team === team);

          return (
            <div key={team} className="oncall-card">
              <h2><span className="team-dot" />{team}</h2>

              <div className="oncall-members">
                {members.map((m) => (
                  <div key={m.email} className={`member ${m.role}`}>
                    <div className="member-avatar">
                      {m.name.split(' ').map(n => n[0]).join('')}
                    </div>
                    <div className="member-info">
                      <span className="member-name">{m.name}</span>
                      <span className="member-email">{m.email}</span>
                      <span className="member-schedule">Until {timeAgo(m.endTime)}</span>
                    </div>
                    <span className={`role-tag ${m.role}`}>{m.role}</span>
                  </div>
                ))}
              </div>

              {policy && (
                <div className="escalation">
                  <h4>Escalation Policy</h4>
                  <ul className="escalation-list">
                    {policy.levels.map((l) => (
                      <li key={l.level}>
                        <span className="esc-level">L{l.level}</span>
                        <span>{l.target}</span>
                        <span className="esc-timeout">{l.timeout}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
