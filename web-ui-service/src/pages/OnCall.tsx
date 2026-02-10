import { useState, useEffect } from 'react';
import { getOnCallEngineers, getEscalationPolicies } from '../services/api';
import type { OnCallEngineer, EscalationPolicy } from '../types';
import { timeAgo } from '../utils/helpers';

export default function OnCall() {
  const [engineers, setEngineers] = useState<OnCallEngineer[]>([]);
  const [policies, setPolicies] = useState<EscalationPolicy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getOnCallEngineers(), getEscalationPolicies()])
      .then(([eng, pol]) => {
        setEngineers(eng);
        setPolicies(pol);
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-text-muted text-sm">
        <span className="w-4.5 h-4.5 border-2 border-border border-t-accent rounded-full animate-spin" />
        Loading…
      </div>
    );

  const teams = Array.from(new Set(engineers.map((e) => e.team)));

  return (
    <div>
      <h1 className="mb-1">On-Call Schedule</h1>
      <p className="text-text-muted text-sm mb-6">Current rotation and escalation policies</p>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {teams.map((team) => {
          const members = engineers.filter((e) => e.team === team);
          const policy = policies.find((p) => p.team === team);

          return (
            <div
              key={team}
              className="bg-surface border border-border rounded-xl p-5 shadow-sm hover:shadow-md hover:border-border-light transition-all"
            >
              {/* Team header */}
              <h2 className="text-base font-bold mb-4 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-accent" />
                {team}
              </h2>

              {/* Members */}
              <div className="flex flex-col gap-2 mb-4">
                {members.map((m) => (
                  <div
                    key={m.email}
                    className={`flex items-center gap-3 px-3 py-2.5 rounded-md bg-bg-subtle border border-transparent hover:border-border-light transition-colors ${
                      m.role === 'primary' ? 'border-l-[3px] border-l-accent!' : 'border-l-[3px] border-l-text-muted!'
                    }`}
                  >
                    {/* Avatar */}
                    <div className="w-[34px] h-[34px] rounded-full bg-accent-subtle text-accent flex items-center justify-center text-xs font-bold shrink-0">
                      {m.name
                        .split(' ')
                        .map((n) => n[0])
                        .join('')}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <span className="block font-semibold text-sm text-text">{m.name}</span>
                      <span className="block text-xs text-text-muted">{m.email}</span>
                      <span className="block text-[0.72rem] text-text-muted mt-0.5">
                        Until {timeAgo(m.endTime)}
                      </span>
                    </div>

                    {/* Role tag */}
                    <span
                      className={`text-[0.6rem] uppercase font-bold tracking-wide px-2 py-0.5 rounded shrink-0 ${
                        m.role === 'primary'
                          ? 'bg-accent-subtle text-accent'
                          : 'bg-bg text-text-muted border border-border'
                      }`}
                    >
                      {m.role}
                    </span>
                  </div>
                ))}
              </div>

              {/* Escalation policy */}
              {policy && (
                <div className="pt-4 border-t border-border">
                  <h4 className="text-[0.68rem] uppercase tracking-wide text-text-muted font-semibold mb-2">
                    Escalation Policy
                  </h4>
                  <ul className="list-none p-0 m-0 flex flex-col gap-1">
                    {policy.levels.map((l) => (
                      <li
                        key={l.level}
                        className="text-sm text-text-secondary flex items-center gap-2"
                      >
                        <span className="text-[0.65rem] font-bold text-text-muted bg-bg border border-border px-1.5 py-px rounded min-w-[24px] text-center">
                          L{l.level}
                        </span>
                        <span className="flex-1">{l.target}</span>
                        <span className="text-xs text-text-muted">{l.timeout}</span>
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
