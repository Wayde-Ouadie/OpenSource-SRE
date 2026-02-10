import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useApi } from '../../hooks/useApi';
import { fetchIncidentById, acknowledgeIncident, resolveIncident } from '../../services/api';
import Card from '../../components/ui/Card/Card';
import Text from '../../components/ui/Text/Text';
import Badge from '../../components/ui/Badge/Badge';
import Button from '../../components/ui/Button/Button';
import Icon from '../../components/ui/Icon/Icon';
import { formatDateTime } from '../../utils/format';

const timelineIcons: Record<string, string> = {
    created: 'alert',
    acknowledged: 'check',
    resolved: 'shield',
    note: 'list',
    escalated: 'user',
};

export default function IncidentDetail() {
    const { id } = useParams<{ id: string }>();
    const { status, data: incident, error, refetch } = useApi(
        () => fetchIncidentById(id!),
        [id]
    );
    const [actionLoading, setActionLoading] = useState<'ack' | 'resolve' | null>(null);
    const [actionError, setActionError] = useState<string | null>(null);

    const handleAcknowledge = async () => {
        if (!id) return;
        setActionLoading('ack');
        setActionError(null);
        try {
            await acknowledgeIncident(id);
            refetch();
        } catch (err) {
            setActionError(err instanceof Error ? err.message : 'Failed to acknowledge');
        } finally {
            setActionLoading(null);
        }
    };

    const handleResolve = async () => {
        if (!id) return;
        setActionLoading('resolve');
        setActionError(null);
        try {
            await resolveIncident(id);
            refetch();
        } catch (err) {
            setActionError(err instanceof Error ? err.message : 'Failed to resolve');
        } finally {
            setActionLoading(null);
        }
    };

    if (status === 'loading') {
        return (
            <div className="space-y-spacing-xl">
                <Card className="animate-pulse"><div className="h-48" /></Card>
                <Card className="animate-pulse"><div className="h-64" /></Card>
            </div>
        );
    }

    if (status === 'error') {
        return (
            <Card>
                <div className="flex items-center gap-spacing-sm text-danger">
                    <Icon name="alert" />
                    <Text variant="body" className="text-danger">Failed to load incident: {error}</Text>
                </div>
            </Card>
        );
    }

    if (status === 'empty' || !incident) {
        return (
            <Card>
                <div className="text-center py-spacing-xl">
                    <Text variant="h3">Incident not found</Text>
                    <Link to="/incidents" className="text-primary hover:underline text-sm mt-spacing-sm inline-block">
                        ← Back to incidents
                    </Link>
                </div>
            </Card>
        );
    }

    return (
        <div className="space-y-spacing-xl">
            {/* Breadcrumb */}
            <div className="flex items-center gap-spacing-sm text-sm">
                <Link to="/incidents" className="text-text-muted hover:text-text-primary transition-colors">
                    Incidents
                </Link>
                <span className="text-text-muted">/</span>
                <span className="text-text-primary font-medium">{incident.id}</span>
            </div>

            {/* Incident Header */}
            <Card>
                <div className="space-y-spacing-lg">
                    <div className="flex items-start justify-between gap-spacing-md">
                        <div className="space-y-spacing-sm">
                            <div className="flex items-center gap-spacing-sm">
                                <Badge variant={incident.severity}>{incident.severity}</Badge>
                                <Badge variant={incident.status}>{incident.status}</Badge>
                                <Text variant="caption" className="font-mono">{incident.id}</Text>
                            </div>
                            <Text variant="h1">{incident.title}</Text>
                            <Text variant="body">{incident.description}</Text>
                        </div>
                    </div>

                    {/* Incident Metadata */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-spacing-md pt-spacing-md border-t border-border">
                        <div>
                            <Text variant="label">Service</Text>
                            <Text variant="body" className="text-text-primary mt-spacing-xs">{incident.service}</Text>
                        </div>
                        <div>
                            <Text variant="label">Assignee</Text>
                            <Text variant="body" className="text-text-primary mt-spacing-xs">{incident.assignee}</Text>
                        </div>
                        <div>
                            <Text variant="label">Created</Text>
                            <Text variant="body" className="text-text-primary mt-spacing-xs">{formatDateTime(incident.createdAt)}</Text>
                        </div>
                        <div>
                            <Text variant="label">Last Updated</Text>
                            <Text variant="body" className="text-text-primary mt-spacing-xs">{formatDateTime(incident.updatedAt)}</Text>
                        </div>
                    </div>

                    {/* Actions */}
                    {incident.status !== 'resolved' && (
                        <div className="flex items-center gap-spacing-md pt-spacing-md border-t border-border">
                            {incident.status === 'triggered' && (
                                <Button
                                    variant="primary"
                                    onClick={handleAcknowledge}
                                    loading={actionLoading === 'ack'}
                                    disabled={actionLoading !== null}
                                >
                                    Acknowledge
                                </Button>
                            )}
                            <Button
                                variant="danger"
                                onClick={handleResolve}
                                loading={actionLoading === 'resolve'}
                                disabled={actionLoading !== null}
                            >
                                Resolve
                            </Button>

                            {actionError && (
                                <div className="flex items-center gap-spacing-xs text-danger">
                                    <Icon name="alert" size="sm" />
                                    <Text variant="body" className="text-danger">{actionError}</Text>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </Card>

            {/* Timeline */}
            <div className="space-y-spacing-md">
                <Text variant="h2">Timeline</Text>
                <div className="relative">
                    <div className="absolute left-4 top-0 bottom-0 w-px bg-border" />
                    {incident.timeline.map((event, idx) => (
                        <div key={event.id} className="relative flex gap-spacing-lg pl-12 pb-spacing-lg">
                            <div className={`absolute left-2.5 w-3 h-3 rounded-full border-2 border-background ${idx === 0 ? 'bg-primary' : 'bg-surface-raised'
                                }`} />
                            <Card className="flex-1">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-spacing-sm">
                                        <Icon name={timelineIcons[event.type] || 'list'} size="sm" className="text-text-muted" />
                                        <Text variant="body" className="text-text-primary capitalize font-medium">{event.type}</Text>
                                    </div>
                                    <Text variant="caption">{formatDateTime(event.timestamp)}</Text>
                                </div>
                                <Text variant="body" className="mt-spacing-xs">{event.message}</Text>
                                <Text variant="caption" className="mt-spacing-xs">by {event.actor}</Text>
                            </Card>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}
