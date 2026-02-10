import { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { getMetrics } from '../services/api';
import type { MetricsData } from '../types';

export default function Metrics() {
  const [data, setData] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMetrics().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading || !data)
    return (
      <div className="flex items-center justify-center gap-2 py-16 text-text-muted text-sm">
        <span className="w-4.5 h-4.5 border-2 border-border border-t-accent rounded-full animate-spin" />
        Loading…
      </div>
    );

  const tooltipStyle = {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-border)',
    borderRadius: 8,
    fontSize: 13,
  };

  return (
    <div>
      <h1 className="mb-1">SRE Metrics</h1>
      <p className="text-text-muted text-sm mb-6">Response times, volume trends, and service breakdown</p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* MTTA trend */}
        <ChartCard title="MTTA Trend (minutes)">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.mttaTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--color-text-muted)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-text-muted)" />
              <Tooltip contentStyle={tooltipStyle} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--color-status-ack)"
                strokeWidth={2}
                dot={{ r: 3, fill: 'var(--color-status-ack)' }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* MTTR trend */}
        <ChartCard title="MTTR Trend (minutes)">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.mttrTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--color-text-muted)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-text-muted)" />
              <Tooltip contentStyle={tooltipStyle} />
              <Line
                type="monotone"
                dataKey="value"
                stroke="var(--color-status-resolved)"
                strokeWidth={2}
                dot={{ r: 3, fill: 'var(--color-status-resolved)' }}
                activeDot={{ r: 5 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Incidents per service */}
        <ChartCard title="Incidents per Service">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.incidentsPerService} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--color-text-muted)" />
              <YAxis
                dataKey="service"
                type="category"
                tick={{ fontSize: 11 }}
                width={120}
                stroke="var(--color-text-muted)"
              />
              <Tooltip
                contentStyle={tooltipStyle}
                cursor={{ fill: 'var(--color-accent-subtle)' }}
              />
              <Bar dataKey="count" fill="var(--color-accent)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Incident volume over time */}
        <ChartCard title="Incident Volume Over Time">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={data.incidentVolume}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--color-text-muted)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--color-text-muted)" />
              <Tooltip contentStyle={tooltipStyle} />
              <Area
                type="monotone"
                dataKey="count"
                stroke="var(--color-status-open)"
                fill="var(--color-status-open)"
                fillOpacity={0.1}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface border border-border rounded-xl p-5 shadow-sm hover:shadow-md hover:border-border-light transition-all">
      <h3 className="text-[0.72rem] uppercase tracking-wide text-text-muted font-semibold mb-4">
        {title}
      </h3>
      {children}
    </div>
  );
}
