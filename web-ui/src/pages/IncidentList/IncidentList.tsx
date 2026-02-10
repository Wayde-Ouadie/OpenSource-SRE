import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { fetchIncidents, type Incident, type IncidentStatus, type Severity } from '../../services/api';
import Card from '../../components/ui/Card/Card';
import Text from '../../components/ui/Text/Text';
import Badge from '../../components/ui/Badge/Badge';
import Icon from '../../components/ui/Icon/Icon';
import { formatTimestamp } from '../../utils/format';

export default function IncidentList() {
    const { status, data, error } = useApi(fetchIncidents);
    const [statusFilter, setStatusFilter] = useState<IncidentStatus | 'all'>('all');
    const [severityFilter, setSeverityFilter] = useState<Severity | 'all'>('all');

    const filteredIncidents = status === 'success'
        ? data.filter((inc: Incident) => {
            if (statusFilter !== 'all' && inc.status !== statusFilter) return false;
            if (severityFilter !== 'all' && inc.severity !== severityFilter) return false;
            return true;
        })
        : [];

    const statusOptions: (IncidentStatus | 'all')[] = ['all', 'triggered', 'acknowledged', 'resolved'];
    const severityOptions: (Severity | 'all')[] = ['all', 'critical', 'high', 'medium', 'low'];

    return (
        <div className="space-y-spacing-xl">
            <Text variant="h1">Incidents</Text>

            {/* Filters */}
            <div className="flex flex-wrap gap-spacing-md">
                <div className="flex items-center gap-spacing-sm">
                    <Text variant="label">Status:</Text>
                    <div className="flex gap-spacing-xs">
                        {statusOptions.map((opt) => (
                            <button
                                key={opt}
                                onClick={() => setStatusFilter(opt)}
                                className={`px-3 py-1.5 text-sm rounded-lg font-medium capitalize transition-colors cursor-pointer ${statusFilter === opt
                                        ? 'bg-primary text-white'
                                        : 'bg-surface-raised text-text-secondary hover:text-text-primary'
                                    }`}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                </div>

                <div className="flex items-center gap-spacing-sm">
                    <Text variant="label">Severity:</Text>
                    <div className="flex gap-spacing-xs">
                        {severityOptions.map((opt) => (
                            <button
                                key={opt}
                                onClick={() => setSeverityFilter(opt)}
                                className={`px-3 py-1.5 text-sm rounded-lg font-medium capitalize transition-colors cursor-pointer ${severityFilter === opt
                                        ? 'bg-primary text-white'
                                        : 'bg-surface-raised text-text-secondary hover:text-text-primary'
                                    }`}
                            >
                                {opt}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Incident List */}
            {status === 'loading' && (
                <div className="space-y-spacing-md">
                    {[1, 2, 3].map((i) => (
                        <Card key={i} className="animate-pulse"><div className="h-20" /></Card>
                    ))}
                </div>
            )}

            {status === 'error' && (
                <Card>
                    <div className="flex items-center gap-spacing-sm text-danger">
                        <Icon name="alert" />
                        <Text variant="body" className="text-danger">Failed to load incidents: {error}</Text>
                    </div>
                </Card>
            )}

            {status === 'success' && filteredIncidents.length === 0 && (
                <Card>
                    <div className="text-center py-spacing-xl">
                        <Icon name="check" size="lg" className="text-success mx-auto mb-spacing-sm" />
                        <Text variant="body">No incidents match the current filters</Text>
                    </div>
                </Card>
            )}

            {status === 'success' && filteredIncidents.length > 0 && (
                <div className="space-y-spacing-sm">
                    {/* Table Header */}
                    <div className="grid grid-cols-12 gap-spacing-md px-spacing-lg py-spacing-sm text-sm">
                        <Text variant="label" className="col-span-1">ID</Text>
                        <Text variant="label" className="col-span-4">Title</Text>
                        <Text variant="label" className="col-span-2">Severity</Text>
                        <Text variant="label" className="col-span-2">Status</Text>
                        <Text variant="label" className="col-span-2">Assignee</Text>
                        <Text variant="label" className="col-span-1">Time</Text>
                    </div>

                    {filteredIncidents.map((incident: Incident) => (
                        <Link key={incident.id} to={`/incidents/${incident.id}`} className="block">
                            <Card className="hover:border-border-light transition-colors duration-150 cursor-pointer">
                                <div className="grid grid-cols-12 gap-spacing-md items-center">
                                    <Text variant="caption" className="col-span-1 font-mono">{incident.id}</Text>
                                    <div className="col-span-4">
                                        <Text variant="body" className="text-text-primary font-medium">{incident.title}</Text>
                                        <Text variant="caption">{incident.service}</Text>
                                    </div>
                                    <div className="col-span-2">
                                        <Badge variant={incident.severity}>{incident.severity}</Badge>
                                    </div>
                                    <div className="col-span-2">
                                        <Badge variant={incident.status}>{incident.status}</Badge>
                                    </div>
                                    <Text variant="body" className="col-span-2">{incident.assignee}</Text>
                                    <Text variant="caption" className="col-span-1">{formatTimestamp(incident.createdAt)}</Text>
                                </div>
                            </Card>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    );
}
