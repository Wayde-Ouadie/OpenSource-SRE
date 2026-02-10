import { useApi } from '../../hooks/useApi';
import { fetchMetrics, fetchIncidents, type Incident } from '../../services/api';
import Card from '../../components/ui/Card/Card';
import Text from '../../components/ui/Text/Text';
import Icon from '../../components/ui/Icon/Icon';
import Progress from '../../components/ui/Progress/Progress';

export default function Metrics() {
    const metrics = useApi(fetchMetrics);
    const incidents = useApi(fetchIncidents);

    const severityCounts = incidents.status === 'success'
        ? {
            critical: incidents.data.filter((i: Incident) => i.severity === 'critical').length,
            high: incidents.data.filter((i: Incident) => i.severity === 'high').length,
            medium: incidents.data.filter((i: Incident) => i.severity === 'medium').length,
            low: incidents.data.filter((i: Incident) => i.severity === 'low').length,
        }
        : { critical: 0, high: 0, medium: 0, low: 0 };

    const statusCounts = incidents.status === 'success'
        ? {
            triggered: incidents.data.filter((i: Incident) => i.status === 'triggered').length,
            acknowledged: incidents.data.filter((i: Incident) => i.status === 'acknowledged').length,
            resolved: incidents.data.filter((i: Incident) => i.status === 'resolved').length,
        }
        : { triggered: 0, acknowledged: 0, resolved: 0 };

    const total = incidents.status === 'success' ? incidents.data.length : 0;

    return (
        <div className="space-y-spacing-xl">
            <Text variant="h1">Metrics</Text>
            <Text variant="body">All values are computed by backend services. The frontend displays them as provided.</Text>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-spacing-md">
                {metrics.status === 'loading' && (
                    <>
                        {[1, 2, 3, 4].map((i) => (
                            <Card key={i} className="animate-pulse"><div className="h-20" /></Card>
                        ))}
                    </>
                )}
                {metrics.status === 'error' && (
                    <Card className="col-span-4">
                        <div className="flex items-center gap-spacing-sm text-danger">
                            <Icon name="alert" />
                            <Text variant="body" className="text-danger">Failed to load metrics: {metrics.error}</Text>
                        </div>
                    </Card>
                )}
                {metrics.status === 'success' && metrics.data.map((metric) => (
                    <Card key={metric.label}>
                        <Text variant="label">{metric.label}</Text>
                        <div className="flex items-end gap-spacing-sm mt-spacing-sm">
                            <span className="text-3xl font-bold text-text-primary">
                                {metric.value}
                            </span>
                            <span className="text-sm text-text-muted">{metric.unit}</span>
                        </div>
                        <div className={`text-sm font-medium mt-spacing-sm ${metric.change < 0 ? 'text-success' : metric.change > 0 ? 'text-danger' : 'text-text-muted'}`}>
                            {metric.change > 0 ? '↑' : metric.change < 0 ? '↓' : '—'} {Math.abs(metric.change)}% vs last period
                        </div>
                    </Card>
                ))}
            </div>

            {/* Incident Breakdown */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-spacing-xl">
                {/* By Severity */}
                <Card>
                    <Text variant="h2" className="mb-spacing-lg">Incidents by Severity</Text>
                    {incidents.status === 'loading' && <div className="animate-pulse h-32" />}
                    {incidents.status === 'error' && (
                        <div className="flex items-center gap-spacing-sm text-danger">
                            <Icon name="alert" />
                            <Text variant="body" className="text-danger">Failed to load</Text>
                        </div>
                    )}
                    {incidents.status === 'success' && (
                        <div className="space-y-spacing-md">
                            {Object.entries(severityCounts).map(([severity, count]) => {
                                const percentage = total > 0 ? (count / total) * 100 : 0;
                                return (
                                    <div key={severity}>
                                        <div className="flex items-center justify-between mb-spacing-xs">
                                            <Text variant="body" className="capitalize text-text-primary">{severity}</Text>
                                            <Text variant="caption">{count} ({percentage.toFixed(0)}%)</Text>
                                        </div>
                                        <Progress value={percentage} variant={severity as 'critical' | 'high' | 'medium' | 'low'} />
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </Card>

                {/* By Status */}
                <Card>
                    <Text variant="h2" className="mb-spacing-lg">Incidents by Status</Text>
                    {incidents.status === 'loading' && <div className="animate-pulse h-32" />}
                    {incidents.status === 'error' && (
                        <div className="flex items-center gap-spacing-sm text-danger">
                            <Icon name="alert" />
                            <Text variant="body" className="text-danger">Failed to load</Text>
                        </div>
                    )}
                    {incidents.status === 'success' && (
                        <div className="space-y-spacing-md">
                            {Object.entries(statusCounts).map(([statusKey, count]) => {
                                const percentage = total > 0 ? (count / total) * 100 : 0;
                                return (
                                    <div key={statusKey}>
                                        <div className="flex items-center justify-between mb-spacing-xs">
                                            <Text variant="body" className="capitalize text-text-primary">{statusKey}</Text>
                                            <Text variant="caption">{count} ({percentage.toFixed(0)}%)</Text>
                                        </div>
                                        <Progress value={percentage} variant={statusKey as 'triggered' | 'acknowledged' | 'resolved'} />
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </Card>
            </div>
        </div>
    );
}
