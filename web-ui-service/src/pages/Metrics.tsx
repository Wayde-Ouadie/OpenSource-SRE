import { useState, useEffect } from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, AreaChart, Area,
} from 'recharts';
import { getMetrics } from '../services/api';
import type { MetricsData } from '../types';
import './Metrics.css';

export default function Metrics() {
  const [data, setData] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMetrics().then(setData).finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <div className="loading">Loading…</div>;

  return (
    <div className="metrics-page">
      <h1>SRE Metrics</h1>
      <p className="metrics-subtitle">Response times, volume trends, and service breakdown</p>

      <div className="chart-grid">
        {/* MTTA trend */}
        <div className="chart-card">
          <h3>MTTA Trend (minutes)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.mttaTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13 }} />
              <Line type="monotone" dataKey="value" stroke="var(--color-acknowledged)" strokeWidth={2} dot={{ r: 3, fill: 'var(--color-acknowledged)' }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* MTTR trend */}
        <div className="chart-card">
          <h3>MTTR Trend (minutes)</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.mttrTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13 }} />
              <Line type="monotone" dataKey="value" stroke="var(--color-resolved)" strokeWidth={2} dot={{ r: 3, fill: 'var(--color-resolved)' }} activeDot={{ r: 5 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Incidents per service */}
        <div className="chart-card">
          <h3>Incidents per Service</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.incidentsPerService} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis type="number" tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
              <YAxis dataKey="service" type="category" tick={{ fontSize: 11 }} width={120} stroke="var(--text-muted)" />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13 }} cursor={{ fill: 'var(--accent-subtle)' }} />
              <Bar dataKey="count" fill="var(--accent)" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Incident volume over time */}
        <div className="chart-card">
          <h3>Incident Volume Over Time</h3>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={data.incidentVolume}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
              <YAxis tick={{ fontSize: 11 }} stroke="var(--text-muted)" />
              <Tooltip contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, fontSize: 13 }} />
              <Area type="monotone" dataKey="count" stroke="var(--color-open)" fill="var(--color-open)" fillOpacity={0.1} strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
