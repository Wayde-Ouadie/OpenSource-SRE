import { useApi } from '../../hooks/useApi';
import { fetchOnCallSchedules } from '../../services/api';
import Card from '../../components/ui/Card/Card';
import Text from '../../components/ui/Text/Text';
import Icon from '../../components/ui/Icon/Icon';
import { formatDateTime } from '../../utils/format';

export default function OnCall() {
    const { status, data, error } = useApi(fetchOnCallSchedules);

    return (
        <div className="space-y-spacing-xl">
            <Text variant="h1">On-Call Schedule</Text>

            {status === 'loading' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-spacing-md">
                    {[1, 2, 3, 4].map((i) => (
                        <Card key={i} className="animate-pulse"><div className="h-32" /></Card>
                    ))}
                </div>
            )}

            {status === 'error' && (
                <Card>
                    <div className="flex items-center gap-spacing-sm text-danger">
                        <Icon name="alert" />
                        <Text variant="body" className="text-danger">Failed to load on-call schedules: {error}</Text>
                    </div>
                </Card>
            )}

            {status === 'empty' && (
                <Card>
                    <div className="text-center py-spacing-xl">
                        <Text variant="body">No on-call schedules configured</Text>
                    </div>
                </Card>
            )}

            {status === 'success' && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-spacing-md">
                    {data.map((schedule) => (
                        <Card key={schedule.id}>
                            <div className="space-y-spacing-md">
                                <div className="flex items-center justify-between">
                                    <Text variant="h3">{schedule.team}</Text>
                                    <div className="flex items-center gap-spacing-xs">
                                        <span className="w-2 h-2 rounded-full bg-success animate-pulse" />
                                        <Text variant="caption" className="text-success">Active</Text>
                                    </div>
                                </div>

                                <div className="flex items-center gap-spacing-md p-spacing-md bg-background rounded-lg">
                                    <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                                        <Icon name="user" className="text-primary" />
                                    </div>
                                    <div>
                                        <Text variant="body" className="text-text-primary font-semibold">{schedule.currentOnCall}</Text>
                                        <Text variant="caption">{schedule.email}</Text>
                                    </div>
                                </div>

                                <div className="grid grid-cols-2 gap-spacing-md text-sm">
                                    <div>
                                        <Text variant="label">Shift Start</Text>
                                        <Text variant="caption" className="mt-spacing-xs block">{formatDateTime(schedule.startTime)}</Text>
                                    </div>
                                    <div>
                                        <Text variant="label">Shift End</Text>
                                        <Text variant="caption" className="mt-spacing-xs block">{formatDateTime(schedule.endTime)}</Text>
                                    </div>
                                </div>

                                <div className="pt-spacing-sm border-t border-border">
                                    <Text variant="caption">
                                        Next on-call: <span className="text-text-primary font-medium">{schedule.nextOnCall}</span>
                                    </Text>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            )}
        </div>
    );
}
