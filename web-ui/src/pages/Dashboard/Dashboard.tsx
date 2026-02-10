import { useApi } from '../../hooks/useApi';
import { fetchIncidents, fetchMetrics, fetchOnCallSchedules, type Incident } from '../../services/api';
import Card from '../../components/ui/Card/Card';
import Text from '../../components/ui/Text/Text';
import Badge from '../../components/ui/Badge/Badge';
import Icon from '../../components/ui/Icon/Icon';
import { Link } from 'react-router-dom';
import { formatTimestamp } from '../../utils/format';

export default function Dashboard() {
    const incidents = useApi(fetchIncidents);
    const metrics = useApi(fetchMetrics);
    const onCall = useApi(fetchOnCallSchedules);

    const activeIncidents = incidents.status === 'success'
        ? incidents.data.filter((i: Incident) => i.status !== 'resolved')
        : [];

    const criticalCount = activeIncidents.filter((i: Incident) => i.severity === 'critical').length;

    return (
        <div className="space-y-spacing-xl">
            <div className="flex items-center justify-between">
                <Text variant="h1">Dashboard</Text>
                <Text variant="caption">
                    Last updated: {new Date().toLocaleTimeString()}
                </Text>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-spacing-md">
                {metrics.status === 'loading' && (
                    <>
                        {[1, 2, 3, 4].map((i) => (
                            <Card key={i} className="animate-pulse">
                                <div className="h-16" />
                            </Card>
                        ))}
                    </>
                )}
                {metrics.status === 'error' && (
                    <Card className="col-span-4">
                        <div className="flex items-center gap-spacing-sm text-danger">
                            <Icon name="alert" size="md" />
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
                            <span className={`ml-auto text-sm font-medium ${metric.change < 0 ? 'text-success' : metric.change > 0 ? 'text-danger' : 'text-text-muted'}`}>
                                {metric.change > 0 ? '+' : ''}{metric.change}%
                            </span>
                        </div>
                    </Card>
                ))}
            </div>

            {/* Critical Alert Banner */}
            {criticalCount > 0 && (
                <div className="bg-danger/10 border border-danger/30 rounded-xl px-spacing-lg py-spacing-md flex items-center gap-spacing-md">
                    <div className="bg-danger/20 rounded-lg p-2">
                        <Icon name="alert" size="lg" className="text-danger" />
                    </div>
                    <div>
                        <Text variant="h3" className="text-danger">{criticalCount} Critical Incident{criticalCount > 1 ? 's' : ''}</Text>
                        <Text variant="body" className="text-text-secondary">Requires immediate attention</Text>
                    </div>
                    <Link
                        to="/incidents"
                        className="ml-auto text-sm font-medium text-danger hover:underline"
                    >
                        View All →
                    </Link>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-spacing-xl">
                {/* Active Incidents */}
                <div className="lg:col-span-2 space-y-spacing-md">
                    <div className="flex items-center justify-between">
                        <Text variant="h2">Active Incidents</Text>
                        <Link to="/incidents" className="text-sm text-primary hover:underline">
                            View all →
                        </Link>
                    </div>

                    {incidents.status === 'loading' && (
                        <Card className="animate-pulse"><div className="h-32" /></Card>
                    )}
                    {incidents.status === 'error' && (
                        <Card>
                            <div className="flex items-center gap-spacing-sm text-danger">
                                <Icon name="alert" />
                                <Text variant="body" className="text-danger">Failed to load incidents: {incidents.error}</Text>
                            </div>
                        </Card>
                    )}
                    {incidents.status === 'empty' && (
                        <Card>
                            <div className="text-center py-spacing-xl">
                                <Icon name="check" size="lg" className="text-success mx-auto mb-spacing-sm" />
                                <Text variant="body">No active incidents</Text>
                            </div>
                        </Card>
                    )}
                    {incidents.status === 'success' && activeIncidents.map((incident: Incident) => (
                        <Link key={incident.id} to={`/incidents/${incident.id}`} className="block">
                            <Card className="hover:border-border-light transition-colors duration-150 cursor-pointer">
                                <div className="flex items-start justify-between gap-spacing-md">
                                    <div className="space-y-spacing-xs">
                                        <div className="flex items-center gap-spacing-sm">
                                            <Badge variant={incident.severity}>{incident.severity}</Badge>
                                            <Badge variant={incident.status}>{incident.status}</Badge>
                                        </div>
                                        <Text variant="h3">{incident.title}</Text>
                                        <Text variant="body">{incident.service} · {incident.assignee}</Text>
                                    </div>
                                    <Text variant="caption">{formatTimestamp(incident.createdAt)}</Text>
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>

                {/* On-Call Sidebar */}
                <div className="space-y-spacing-md">
                    <div className="flex items-center justify-between">
                        <Text variant="h2">On-Call Now</Text>
                        <Link to="/on-call" className="text-sm text-primary hover:underline">
                            Schedule →
                        </Link>
                    </div>

                    {onCall.status === 'loading' && (
                        <Card className="animate-pulse"><div className="h-24" /></Card>
                    )}
                    {onCall.status === 'error' && (
                        <Card>
                            <div className="flex items-center gap-spacing-sm text-danger">
                                <Icon name="alert" />
                                <Text variant="body" className="text-danger">Failed to load on-call: {onCall.error}</Text>
                            </div>
                        </Card>
                    )}
                    {onCall.status === 'success' && onCall.data.map((schedule) => (
                        <Card key={schedule.id}>
                            <Text variant="label">{schedule.team}</Text>
                            <div className="flex items-center gap-spacing-sm mt-spacing-sm">
                                <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
                                    <Icon name="user" size="sm" className="text-primary" />
                                </div>
                                <div>
                                    <Text variant="body" className="text-text-primary font-medium">{schedule.currentOnCall}</Text>
                                    <Text variant="caption">{schedule.email}</Text>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            </div>
        </div>
    );
}
